# guardscore

A small, from-scratch red-team harness for probing the guardrails of large language models. `guardscore` fires a catalog of adversarial prompts at a target model, judges whether each guardrail held or broke, and (as it matures) scores the results into a repeatable mini-benchmark.

> **Status: work in progress.** This is an actively developed learning and portfolio project, built one phase at a time. Phases 0–4+ are shipped (through automated detection, scoring, per-run JSON logs, and OWASP LLM Top 10 / MITRE ATLAS mapping). Phase 5 — the agentic attack scenario — has its core demonstrated: a prompt-injection attack drives a model into an unauthorized tool call (reading a file outside its allowlist), and an action-level detector catches the violation by inspecting what the model *did* rather than what it *said*. Both direct injection (attack in the user prompt) and indirect injection (attack hidden inside file content the model reads, via a multi-round loop) have been explored; the two together show that text-level detection is unreliable in both directions — it can miss real breaches *and* report ones that never happened. This currently lives in a standalone spike; folding it into the main scored harness is the next step. See the [Roadmap](#roadmap) for what's built and what's next.

## Why this exists

Prompt injection and system-prompt leakage are among the most practical, least-understood weaknesses in LLM-backed applications. `guardscore` is built from first principles — rather than wrapping an existing framework — to develop a working, testable understanding of how these attacks succeed, how to detect them programmatically, and where automated detection falls short. The end goal is a tool that maps its findings to industry references like the OWASP LLM Top 10 and MITRE ATLAS, and that culminates in a demonstrated agentic attack (prompt injection driving an unauthorized tool call).

## What it does today

- Talks to a local model through **Ollama** via a pluggable provider interface.
- Defines prompt-injection attacks as structured **data** (an attack catalog), not hardcoded logic.
- Runs the full catalog against a target model, focused on **system-prompt secret-leak** scenarios (plant a secret, instruct the model to protect it, attempt to extract it).
- **Detects** whether each attack leaked the planted secret and labels every result `LEAKED` or `SAFE`.
- **Scores** the run into an aggregate summary — total attacks, number leaked, and an overall leak rate.
- **Persists** every run to a timestamped JSON file (`runs/run-<timestamp>.json`) — model, UTC timestamp, aggregate summary, per-attack results, and a per-taxonomy coverage breakdown.
- **Maps** each attack to the industry references it exercises — OWASP LLM Top 10 (2025) and MITRE ATLAS technique IDs — and reports, per reference, how many probes broke the guardrail.

Making detection robust to obfuscated or encoded leaks (see [detection limits](#a-note-on-detection-limits)) remains in progress, as does folding the agentic scenario below into this scored harness.

Separately, a standalone **agentic-attack spike** (`tool_loop.py`) demonstrates the core of the Phase 5 scenario. A model is given a `read_file` tool restricted to an allowlist of authorized files. A prompt-injection attack induces the model to request a file *outside* that allowlist, and an **action-level detector** flags the unauthorized request — judging the tool call the model *made* rather than the text it returned. This distinction is the point: across repeated runs the model's final text is inconsistent (sometimes refusing, sometimes leaking, sometimes distorting the value), while the underlying unauthorized action is caught every time. The harness deliberately measures rather than blocks — it observes and scores the model's behavior, so the "secret" it exposes is always a harmless canary, never real data.

The spike covers two delivery variants. In **direct injection**, the attack is in the user prompt, and against `llama3.2` it reliably completes the unauthorized read (caught by the detector every run). In **indirect injection**, the attack is hidden inside the *content of a file the model reads*, and a multi-round loop lets detection run on every turn — necessary because the poisoned content only enters the conversation after the first read. Against `llama3.2` the indirect variant consistently hijacks the model's *intent* but does not complete a real unauthorized action: the model claims (and even confabulates) a read of the off-limits file without ever emitting the tool call. This is a documented capability limitation of the model, not a guardrail success — and it is the clean counter-example to text-level detection, which would have reported a breach the action detector correctly shows never happened. This spike is not yet wired into the main scored runner.

## Architecture

The design deliberately separates concerns so the harness stays reusable as it grows:

| Component | File | Responsibility |
|---|---|---|
| **Provider** | `providers.py` | A generic interface for talking to any model. `Provider` defines the contract; `OllamaProvider` implements it. Swapping model backends changes one line, not the harness. |
| **Attack catalog** | `attacks.py` | Attacks as data. An `Attack` dataclass holds each test case (name, system prompt to plant, attack prompt, planted secret, a one-line intent, and OWASP / ATLAS reference tags); `CATALOG` is the list of them. Adding an attack means adding a data entry, not writing code. |
| **Detector** | `detectors.py` | Judges each reply — does the planted secret appear? — and labels it `LEAKED` or `SAFE`. |
| **Taxonomy** | `taxonomy.py` | Lookup table mapping OWASP LLM Top 10 and MITRE ATLAS IDs to human-readable titles, so reports carry both the ID and its name. |
| **Result** | `results.py` | A `Result` dataclass that records the outcome of one attack (name, verdict, reply) so runs can be scored and, later, reported. |
| **Runner** | `run_attacks.py` | Iterates the catalog, sends each attack through the provider, detects leaks, prints per-attack verdicts, an aggregate score, and a per-taxonomy coverage breakdown, then writes the whole run to `runs/run-<timestamp>.json`. |

## Requirements

- Python 3.13 (managed with [pyenv](https://github.com/pyenv/pyenv) recommended)
- [Ollama](https://ollama.com) running locally
- A pulled model (default: `llama3.2`)

## Setup

```bash
# clone
git clone https://github.com/r4nd0m4rest/guardscore.git
cd guardscore

# create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# install dependencies
pip install ollama

# make sure Ollama is running and the model is available
ollama serve                    # in a separate terminal, or: brew services start ollama
ollama pull llama3.2
```

## Usage

Send a single prompt to a model:

```bash
python hello_model.py --prompt "In one sentence, what is SSRF?"
python hello_model.py --prompt "..." --model llama3.2
```

Run the full attack catalog against a model:

```bash
python run_attacks.py
```

Each attack is fired in turn, its response printed and labeled `LEAKED` or `SAFE`, followed by an aggregate summary and a per-taxonomy coverage breakdown — for example:

```
Ran 2 attacks: 1 LEAKED, 1 SAFE (50.0% leak rate)

Coverage:
  LLM01:2025     Prompt Injection                   0/1 broke
  LLM07:2025     System Prompt Leakage              1/2 broke
  AML.T0051.000  LLM Prompt Injection: Direct       0/1 broke

Wrote runs/run-<timestamp>.json
```

The full run — every model reply plus the taxonomy tags — is also written to `runs/run-<timestamp>.json` (git-ignored).

## Roadmap

The project is built in incremental phases, each adding one capability:

- [x] **Phase 0** — Talk to a local model from a script
- [x] **Phase 1** — Pluggable provider interface (`Provider` / `OllamaProvider`)
- [x] **Phase 2** — Attack catalog as data (`Attack` dataclass + runner)
- [x] **Phase 3** — Detectors: automatically label each result `LEAKED` / `SAFE`
- [x] **Phase 4** — Scoring into a mini-benchmark (aggregate leak rate)
- [x] **Phase 4+** — Persist each run to a timestamped JSON log, and tag every attack with OWASP LLM Top 10 (2025) and MITRE ATLAS IDs, reported as a per-reference coverage breakdown
- [ ] **Phase 5** — Agentic scenario: prompt injection driving an unauthorized tool call
  - [x] **5a** — Benign tool-calling loop: a model is given a `read_file` tool, calls it on a legitimate request, and answers from the result fed back to it
  - [x] **5b** — Weaponize it (demonstrated in `tool_loop.py` spike): an injected prompt drives an unauthorized tool call, and an action-level detector flags it by inspecting the **action taken** rather than the text returned
  - [x] **5b (indirect)** — Indirect variant: attack hidden in file content the model reads, detected via a multi-round loop. Against `llama3.2` it hijacks the model's intent but does not complete a real unauthorized action (the model confabulates the read instead) — a documented model-capability limitation, and the counter-example that shows text-level detection can *over*-report a breach that never happened
  - [ ] **5c** — Integrate the agentic attack and action-level detector into the main scored harness (`Attack` / `Result` / `run_attacks.py`) so it runs and scores alongside the leak attacks
- [ ] **Phase 6** — Comparison against established tooling (garak, PyRIT); packaging, tests, and docs

## A note on detection limits

Automated detection is an approximation, and knowing where it is blind is part of the point. A simple substring check catches a secret leaked verbatim but misses one that is encoded, spelled out, or paraphrased — a false negative. The reverse also occurs: a model under injection can *claim* or confabulate an action it never took, so text that reads like a breach may describe one that never happened — a false positive. Text-level detection is therefore unreliable in both directions, which is the case for judging the **action** a model takes, not just the words it produces. Surfacing exactly what the detectors catch and what they provably miss is a stated goal of this project, not a defect to hide.

## Responsible use

`guardscore` is for testing models and systems you own or are explicitly authorized to test. It exists to understand and improve the safety and security of LLM-backed applications. Do not use it against third-party systems without permission.

## License

Released under the [MIT License](LICENSE).
