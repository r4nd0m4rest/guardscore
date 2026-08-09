# hello_model.py — Phase 0/1: send a prompt to a model via a provider

import argparse
from providers import OllamaProvider


def main():
    parser = argparse.ArgumentParser(description="Send a prompt to a local model.")
    parser.add_argument("--prompt", required=True, help="the text to send")
    parser.add_argument("--model", default="llama3.2", help="which model to use")
    args = parser.parse_args()

    provider = OllamaProvider(model=args.model)   # create the provider
    reply = provider.chat(args.prompt)            # use it — no ollama here
    print(reply)


if __name__ == "__main__":
    main()