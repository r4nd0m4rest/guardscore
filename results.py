from dataclasses import dataclass, field

@dataclass
class Result:
    name: str
    verdict: str
    reply: str
    kind: str = "leak"
    text_verdict: str = ""
    requested_files: list[str] = field(default_factory=list)
