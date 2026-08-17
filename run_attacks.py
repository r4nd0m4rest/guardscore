# run_attacks.py — fire every attack in the catalog at a model

from providers import OllamaProvider
from attacks import CATALOG
from detectors import detect
from results import Result

# def main():
#     provider = OllamaProvider(model="llama3.2")

#     for attack in CATALOG:                    # each pass: attack = one Attack object
#         messages = [
#             {"role": "system", "content": attack.system_prompt},
#             {"role": "user", "content": attack.attack_prompt},
#         ]
#         reply = provider.chat(messages)
#         verdict = detect(reply,attack.planted_secret)
#         print(f"=== {attack.name}: {verdict} ===")       # which attack this was
#         print(reply)
#         print()                               # blank line between attacks


def main():
    provider = OllamaProvider(model="llama3.2")
    results = []                      # empty list to collect into

    for attack in CATALOG:
        # build messages, get reply, get verdict
        messages = [
            {"role": "system", "content": attack.system_prompt},
            {"role": "user", "content": attack.attack_prompt},
        ]
        reply = provider.chat(messages)
        verdict = detect(reply,attack.planted_secret)
        results.append(Result(name=attack.name, verdict=verdict, reply=reply))

        # print the per-attack line
        print(f"=== {attack.name}: {verdict} ===")       # which attack this was
        print(reply)
        print()                               # blank line between attacks

    # after the loop — summarize the whole run
    total = len(results)
    leaked = sum(1 for r in results if r.verdict == "LEAKED")
    safe = total - leaked
    leak_rate = (leaked / total * 100) if total > 0 else 0
    print(f"Ran {total} attacks: {leaked} LEAKED, {safe} SAFE ({leak_rate:.1f}% leak rate)")


if __name__ == "__main__":
    main()