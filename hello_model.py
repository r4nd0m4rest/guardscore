import argparse
import ollama


def main():
    # 1. Figure out what the user asked for
    parser = argparse.ArgumentParser(description="Send a prompt to a local model.")
    parser.add_argument("--prompt", required=True, help="the text to send")
    parser.add_argument("--model", default="llama3.2", help="which model to use")
    args = parser.parse_args()

    # 2. Ask the model
    response = ollama.chat(
        model=args.model,
        messages=[{"role": "user", "content": args.prompt}],
    )

    # 3. Show the answer
    print(response["message"]["content"])


if __name__ == "__main__":
    main() 