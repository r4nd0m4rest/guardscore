# providers.py — the pluggable interface for talking to models

import ollama


class Provider:
    """Base contract: every provider must implement chat()."""

    def chat(self, messages):
        # The base class declares the method but refuses to implement it.
        # Subclasses MUST override this, or calling it raises an error.
        raise NotImplementedError("Subclasses must implement chat()")


class OllamaProvider(Provider):
    """Talks to a local model via Ollama."""

    def __init__(self, model):
        self.model = model  # remember which model this provider uses

    # def chat(self, prompt):
    #     response = ollama.chat(
    #         model=self.model,
    #         messages=[{"role": "user", "content": prompt}],
    #     )
    #     return response["message"]["content"]

    def chat(self, messages):
        response = ollama.chat(
            model=self.model, 
            messages=messages)
        return response["message"]["content"]