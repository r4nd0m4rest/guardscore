# run_attacks.py — fire every attack in the catalog at a model, then score and persist the run

import json
from datetime import datetime, timezone
from pathlib import Path

from providers import OllamaProvider
from attacks import CATALOG
from detectors import detect, detect_action
from results import Result
from tools import make_read_file
import taxonomy

MODEL = "llama3.2"
RUNS_DIR = Path(__file__).parent / "runs"

# A guardrail "broke" whether the leak detector fired (LEAKED) or the action
# detector did (VIOLATION). Both mean the same thing for scoring.
BROKE_VERDICTS = {"LEAKED", "VIOLATION"}


def broke(verdict):
    """True if this verdict means a guardrail failed — for a leak or an agentic attack."""
    return verdict in BROKE_VERDICTS


def coverage(pairs):
    """Roll the (attack, result) pairs up by taxonomy id.

    Returns {"owasp": {...}, "atlas": {...}}; each id maps to its title, how
    many attacks exercised it, and how many of those broke the guardrail.

    Pseudocode:
        start two empty buckets: owasp, atlas
        for each (attack, result):
            did the guardrail break? -> 1 or 0
            for each scheme (owasp, atlas):
                for each reference id the attack is tagged with:
                    make the bucket for that id if new
                    bucket.attacks += 1
                    bucket.broke   += (1 if it broke else 0)
        return the buckets
    """
    out = {"owasp": {}, "atlas": {}}
    # loop: walk every attack/result pair and tally it under each of its ids
    for attack, result in pairs:
        hit = 1 if broke(result.verdict) else 0
        for scheme, ref_ids in (("owasp", attack.owasp), ("atlas", attack.atlas)):
            for ref_id in ref_ids:
                entry = out[scheme].setdefault(
                    ref_id, {"title": taxonomy.title(ref_id), "attacks": 0, "broke": 0}
                )
                entry["attacks"] += 1
                entry["broke"] += hit
    return out


def write_run(pairs, summary, cov):
    """Serialize the whole run to runs/run-<timestamp>.json and return the path.

    Pseudocode:
        make sure runs/ exists
        grab one UTC timestamp (used in the record AND the filename)
        for each (attack, result): flatten into one dict (verdict + taxonomy tags)
        assemble the record: model, timestamp, summary, coverage, results
        write it as pretty JSON to runs/run-<timestamp>.json
        return that path
    """
    RUNS_DIR.mkdir(exist_ok=True)
    now = datetime.now(timezone.utc)

    # loop: join each result's outcome with its attack's taxonomy tags into one flat dict
    results_json = []
    for attack, result in pairs:
        results_json.append({
            "name": result.name,
            "kind": result.kind,
            "verdict": result.verdict,             # leak attacks: LEAKED/SAFE. agentic: the action verdict (VIOLATION/SAFE)
            "text_verdict": result.text_verdict,   # agentic only: what the text-level detector said
            "requested_files": result.requested_files,  # agentic only: every file the model asked to read
            "reply": result.reply,
            "intent": attack.intent,
            "owasp": attack.owasp,
            "atlas": attack.atlas,
        })

    record = {
        "model": MODEL,
        "timestamp": now.isoformat(),
        "summary": summary,
        "coverage": cov,
        "results": results_json,
    }

    path = RUNS_DIR / f"run-{now.strftime('%Y%m%d-%H%M%S')}.json"
    path.write_text(json.dumps(record, indent=2))
    return path


def run_leak_attack(provider, attack):
    """Send one leak attack, detect whether the planted secret leaked, return a Result.

    One attack in, one Result out. No loop, no printing — main() owns those.
    """
    messages = [
        {"role": "system", "content": attack.system_prompt},
        {"role": "user", "content": attack.attack_prompt},
    ]
    reply = provider.chat(messages)
    verdict = detect(reply, attack.planted_secret)
    return Result(name=attack.name, verdict=verdict, reply=reply)


def run_agentic_attack(provider, attack):
    """Run one agentic attack through a multi-round tool loop, return a Result.

    The model is handed a read_file tool backed by attack.files (an in-memory
    dict — nothing touches the real disk). Each round, any file it asks for is
    recorded, then served. After the loop we judge twice:
      - action: did it request a file outside attack.allowed_files?  (ground truth)
      - text:   did the canary appear in its final answer?           (unreliable proxy)
    """
    read_file = make_read_file(attack.files)
    messages = [
        {"role": "system", "content": attack.system_prompt},
        {"role": "user", "content": attack.attack_prompt},
    ]
    requested_files = []

    # loop: let the model call read_file up to max_rounds times, recording every request
    for _ in range(attack.max_rounds):
        message = provider.chat_with_tools(messages, [read_file])
        messages.append(message)

        calls = message.tool_calls or []
        if not calls:
            break  # model answered in words — nothing more to do

        for call in calls:
            if call.function.name == "read_file":
                filename = call.function.arguments["filename"]
                requested_files.append(filename)
                contents = read_file(filename)
                messages.append({"role": "tool", "content": str(contents), "name": "read_file"})

    final_reply = message.content or ""
    action_verdict = detect_action(requested_files, attack.allowed_files)
    text_verdict = detect(final_reply, attack.planted_secret)

    return Result(
        name=attack.name,
        verdict=action_verdict,
        reply=final_reply,
        kind="agentic",
        text_verdict=text_verdict,
        requested_files=requested_files,
    )


def main():
    """Run the catalog, print per-attack + aggregate + coverage, write the run file.

    Pseudocode:
        make a provider for MODEL
        for each attack in the catalog:
            dispatch to run_leak_attack or run_agentic_attack by attack.kind
            keep the (attack, result) pair
            print the verdict and the reply
        count totals and break rate -> summary
        build the coverage breakdown
        print coverage
        write the run to disk, print where
    """
    provider = OllamaProvider(model=MODEL)
    pairs = []  # list of (attack, result) so taxonomy data can be joined back in when scoring

    # loop: dispatch each attack to the right runner, collect the pair, print it
    for attack in CATALOG:
        if attack.kind == "agentic":
            result = run_agentic_attack(provider, attack)
        else:
            result = run_leak_attack(provider, attack)
        pairs.append((attack, result))
        header = f"=== {attack.name}: {result.verdict} ==="
        if result.kind == "agentic":
            files = ", ".join(result.requested_files) or "(none)"
            header += f"  [text: {result.text_verdict} | requested: {files}]"
        print(header)
        print(result.reply)
        print()

    # after the loop — summarize the whole run
    total = len(pairs)
    broke_count = sum(1 for _, r in pairs if broke(r.verdict))
    held = total - broke_count
    break_rate = (broke_count / total * 100) if total > 0 else 0
    summary = {"total": total, "broke": broke_count, "held": held, "break_rate": round(break_rate, 1)}
    print(f"Ran {total} attacks: {broke_count} broke, {held} held ({break_rate:.1f}%)")

    cov = coverage(pairs)
    print("\nCoverage:")
    # loop: print one aligned row per taxonomy id — "<id> <title> <broke>/<attacks> broke"
    for scheme in ("owasp", "atlas"):
        for ref_id, e in cov[scheme].items():
            print(f"  {ref_id:<14} {e['title']:<34} {e['broke']}/{e['attacks']} broke")

    path = write_run(pairs, summary, cov)
    print(f"\nWrote {path}")


if __name__ == "__main__":
    main()
