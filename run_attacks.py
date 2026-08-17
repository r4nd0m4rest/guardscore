# run_attacks.py — fire every attack in the catalog at a model
from providers import OllamaProvider
from attacks import CATALOG
from detectors import detect

def main():
    provider = OllamaProvider(model="llama3.2")

    for attack in CATALOG:                    # each pass: attack = one Attack object
        messages = [
            {"role": "system", "content": attack.system_prompt},
            {"role": "user", "content": attack.attack_prompt},
        ]
        reply = provider.chat(messages)
        verdict = detect(reply,attack.planted_secret)
        print(f"=== {attack.name}: {verdict} ===")       # which attack this was
        print(reply)
        print()                               # blank line between attacks

if __name__ == "__main__":
    main()