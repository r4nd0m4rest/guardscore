# providers.py — the pluggable interface for talking to models

import ollama


class Provider:
    """Base contract: every provider must implement chat()."""

    def chat(self, messages):
        # The base class declares the method but refuses to implement it.
        # Subclasses MUST override this, or calling it raises an error.
        raise NotImplementedError("Subclasses must implement chat()")

    def chat_with_tools(self, messages, tools):
        # Same contract as chat(), but the model is handed tools it may call,
        # and the whole response message is returned (not just its text).
        raise NotImplementedError("Subclasses must implement chat_with_tools()")


class OllamaProvider(Provider):
    """Talks to a local model via Ollama."""

    def __init__(self, model):
        self.model = model  # remember which model this provider uses

    def chat(self, messages):
        response = ollama.chat(
            model=self.model, 
            messages=messages)
        return response["message"]["content"]

    def chat_with_tools(self, messages, tools):
        """Talk to a local model via Ollama, with tools.

        Args:
            messages: A list of messages in the chat format.
            tools: A list of callable functions the model may invoke.

        Returns:
            The whole response message object — not just its text. It carries
            both `.content` (the model's words) and `.tool_calls` (the tools it
            asked to run), and can be appended straight back into `messages`.
        """
        response = ollama.chat(
            model=self.model,
            messages=messages,
            tools=tools,
        )
        return response.message