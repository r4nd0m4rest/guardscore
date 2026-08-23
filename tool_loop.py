# tool_loop.py — input a file and its content and have the LLM read the file.

import ollama

def read_file(filename: str) -> str:
    """Read a text file from the local filesystem and return its contents.

    Args:
        filename: The name of the file to read, e.g. "notes.txt".

    Returns:
        The full contents of the file as a single string.
    """
    with open(filename, "r") as f:
        return f.read()
# print(read_file("notes.txt"))

# a normal request that SHOULD make the model want to read the file
messages = [{"role": "user", "content": "What does notes.txt say?"}]

# hand the model the tool — pass the function OBJECT, in a list
response = ollama.chat(model="llama3.2", messages=messages, tools=[read_file])

# look at what came back
# print(response.message.tool_calls)

messages.append(response.message)          # ONCE, before the loop — the assistant's turn (holds every tool_call)

for tool in response.message.tool_calls or []:
    if tool.function.name == "read_file":
        result = read_file(**tool.function.arguments)
        print("TOOL RETURNED:", result)
        messages.append({"role": "tool", "content": str(result), "name": tool.function.name})
    else:
        print("Model asked for a tool I don't have:", tool.function.name)

final = ollama.chat(model="llama3.2", messages=messages, tools=[read_file])
print("FINAL:", final.message.content)