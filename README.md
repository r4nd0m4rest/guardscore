# guardscore

A small, from-scratch red-team harness for probing the guardrails of large language models. `guardscore` fires a catalog of adversarial prompts at a target model, judges whether each guardrail held or broke, and (as it matures) scores the results into a repeatable mini-benchmark.

> **Status: work in progress.** This is an actively developed learning and portfolio project, built one phase at a time. Phases 0–4 are shipped (through automated detection and scoring). Phase 5 — the agentic attack scenario — has its core demonstrated: a prompt-injection attack drives a model into an unauthorized tool call (reading a file outside its allowlist), and an action-level detector catches the violation by inspecting what the model *did* rather than what it *said*. This currently lives in a standalone spike; folding it into the main scored harness is the next step. See the [Roadmap](#roadmap) for what's built and what's next.

## Why this exists

Prompt injection and system-prompt leakage are among the most practical, least-understood weaknesses in LLM-backed applications. `guardscore` is built from first principles — rather than wrapping an existing framework — to develop a working, testable understanding of how these attacks succeed, how to detect them programmatically, and where automated detection falls short. The end goal is a tool that maps its findings to industry references like the OWASP LLM Top 10 and MITRE ATLAS, and that culminates in a demonstrated agentic attack (prompt injection driving an unauthorized tool call).

## What it does today

- Talks to a local model through **Ollama** via a pluggable provider interface.
- Defines prompt-injection attacks as structured **data** (an attack catalog), not hardcoded logic.
- Runs the full catalog against a target model, focused on **system-prompt secret-leak** scenarios (plant a secret, instruct the model to protect it, attempt to extract it).
- **Detects** whether each attack leaked the planted secret and labels every result `LEAKED` or `SAFE`.
- **Scores** the run into an aggregate summary — total attacks, number leaked, and an overall leak rate.

Making detection robust to obfuscated or encoded leaks (see [detection limits](#a-note-on-detection-limits)) and mapping results to industry taxonomies remain in progress.

Separately, a standalone **agentic-attack spike** (`tool_loop.py`) demonstrates the core of the Phase 5 scenario. A model is given a `read_file` tool restricted to an allowlist of authorized files. A prompt-injection attack induces the model to request a file *outside* that allowlist, and an **action-level detector** flags the unauthorized request — judging the tool call the model *made* rather than the text it returned. This distinction is the point: across repeated runs the model's final text is inconsistent (sometimes refusing, sometimes leaking, sometimes distorting the value), while the underlying unauthorized action is caught every time. The harness deliberately measures rather than blocks — it observes and scores the model's behavior, so the "secret" it exposes is always a harmless canary, never real data. This spike is not yet wired into the main scored runner.

## Architecture

The design deliberately separates concerns so the harness stays reusable as it grows:

| Component | File | Responsibility |
|---|---|---|
| **Provider** | `providers.py` | A generic interface for talking to any model. `Provider` defines the contract; `OllamaProvider` implements it. Swapping model backends changes one line, not the harness. |
| **Attack catalog** | `attacks.py` | Attacks as data. An `Attack` dataclass holds each test case (name, system prompt to plant, attack prompt, planted secret); `CATALOG` is the list of them. Adding an attack means adding a data entry, not writing code. |
| **Detector** | `detectors.py` | Judges each reply — does the planted secret appear? — and labels it `LEAKED` or `SAFE`. |
| **Result** | `results.py` | A `Result` dataclass that records the outcome of one attack (name, verdict, reply) so runs can be scored and, later, reported. |
| **Runner** | `run_attacks.py` | Iterates the catalog, sends each attack through the provider, detects leaks, collects results, and prints per-attack verdicts plus an aggregate score. |

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

Each attack is fired in turn, its response printed and labeled `LEAKED` or `SAFE`, followed by an aggregate summary — for example:

```
Ran 2 attacks: 1 LEAKED, 1 SAFE (50.0% leak rate)
```

## Roadmap

The project is built in incremental phases, each adding one capability:

- [x] **Phase 0** — Talk to a local model from a script
- [x] **Phase 1** — Pluggable provider interface (`Provider` / `OllamaProvider`)
- [x] **Phase 2** — Attack catalog as data (`Attack` dataclass + runner)
- [x] **Phase 3** — Detectors: automatically label each result `LEAKED` / `SAFE`
- [x] **Phase 4** — Scoring into a mini-benchmark (aggregate leak rate)
- [ ] **Phase 4+** — Persist results to file (JSON) and map findings to OWASP LLM Top 10 and MITRE ATLAS
- [ ] **Phase 5** — Agentic scenario: prompt injection driving an unauthorized tool call
  - [x] **5a** — Benign tool-calling loop: a model is given a `read_file` tool, calls it on a legitimate request, and answers from the result fed back to it
  - [x] **5b** — Weaponize it (demonstrated in `tool_loop.py` spike): an injected prompt drives an unauthorized tool call, and an action-level detector flags it by inspecting the **action taken** rather than the text returned
  - [ ] **5c** — Integrate the agentic attack and action-level detector into the main scored harness (`Attack` / `Result` / `run_attacks.py`) so it runs and scores alongside the leak attacks
- [ ] **Phase 6** — Comparison against established tooling (garak, PyRIT); packaging, tests, and docs

## A note on detection limits

Automated detection is an approximation, and knowing where it is blind is part of the point. A simple substring check catches a secret leaked verbatim but misses one that is encoded, spelled out, or paraphrased — a false negative. Surfacing exactly what the detectors catch and what they provably miss is a stated goal of this project, not a defect to hide.

## Responsible use

`guardscore` is for testing models and systems you own or are explicitly authorized to test. It exists to understand and improve the safety and security of LLM-backed applications. Do not use it against third-party systems without permission.

## License

Released under the [MIT License](LICENSE).
