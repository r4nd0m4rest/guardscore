# run_attacks.py — fire every attack in the catalog at a model, then score and persist the run

import json
from datetime import datetime, timezone
from pathlib import Path

from providers import OllamaProvider
from attacks import CATALOG
from detectors import detect
from results import Result
import taxonomy

MODEL = "llama3.2"
RUNS_DIR = Path(__file__).parent / "runs"


def coverage(pairs):
    """Roll the (attack, result) pairs up by taxonomy id.

    Returns {"owasp": {...}, "atlas": {...}}; each id maps to its title, how
    many attacks exercised it, and how many of those leaked.

    Pseudocode:
        start two empty buckets: owasp, atlas
        for each (attack, result):
            did it break? -> 1 or 0
            for each scheme (owasp, atlas):
                for each reference id the attack is tagged with:
                    make the bucket for that id if new
                    bucket.attacks += 1
                    bucket.broke   += (1 if broke else 0)
        return the buckets
    """
    out = {"owasp": {}, "atlas": {}}
    # loop: walk every attack/result pair and tally it under each of its ids
    for attack, result in pairs:
        broke = 1 if result.verdict == "LEAKED" else 0
        for scheme, ref_ids in (("owasp", attack.owasp), ("atlas", attack.atlas)):
            for ref_id in ref_ids:
                entry = out[scheme].setdefault(
                    ref_id, {"title": taxonomy.title(ref_id), "attacks": 0, "broke": 0}
                )
                entry["attacks"] += 1
                entry["broke"] += broke
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
            "verdict": result.verdict,
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


def main():
    """Run the catalog, print per-attack + aggregate + coverage, write the run file.

    Pseudocode:
        make a provider for MODEL
        for each attack in the catalog:
            send system + attack prompt
            detect whether the planted secret leaked
            keep the (attack, result) pair
            print the verdict and the reply
        count totals and leak rate -> summary
        build the coverage breakdown
        print coverage
        write the run to disk, print where
    """
    provider = OllamaProvider(model=MODEL)
    pairs = []  # list of (attack, result) so taxonomy data can be joined back in when scoring

    # loop: one round-trip per attack — send it, judge the reply, record + print
    for attack in CATALOG:
        messages = [
            {"role": "system", "content": attack.system_prompt},
            {"role": "user", "content": attack.attack_prompt},
        ]
        reply = provider.chat(messages)
        verdict = detect(reply, attack.planted_secret)
        pairs.append((attack, Result(name=attack.name, verdict=verdict, reply=reply)))

        print(f"=== {attack.name}: {verdict} ===")
        print(reply)
        print()

    # after the loop — summarize the whole run
    total = len(pairs)
    leaked = sum(1 for _, r in pairs if r.verdict == "LEAKED")
    safe = total - leaked
    leak_rate = (leaked / total * 100) if total > 0 else 0
    summary = {"total": total, "leaked": leaked, "safe": safe, "leak_rate": round(leak_rate, 1)}
    print(f"Ran {total} attacks: {leaked} LEAKED, {safe} SAFE ({leak_rate:.1f}% leak rate)")

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
