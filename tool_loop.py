def read_file(filename: str) -> str:
    """Read a text file from the local filesystem and return its contents.

    Args:
        filename: The name of the file to read, e.g. "notes.txt".

    Returns:
        The full contents of the file as a single string.
    """
    with open(filename, "r") as f:
        return f.read()
print(read_file("notes.txt"))