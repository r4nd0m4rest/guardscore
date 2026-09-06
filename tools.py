# tools.py — input a file (a dict of filename → contents) and returns a function read_file(filename) that looks up and returns the contents from that dict.

def make_read_file(files: dict[str, str]):
    def read_file(filename: str) -> str:
        """Read a text file and return its contents.

        Args:
            filename: The name of the file to read, e.g. "notes.txt".

        Returns:
            The full contents of the file as a single string.
        """
        return files.get(filename, f"[no such file: {filename}]")
    return read_file

