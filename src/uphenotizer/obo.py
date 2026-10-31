"""Minimal OBO reader: just enough to get names, namespaces and obsoletion status."""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Term:
    id: str
    name: str = ""
    namespace: str = ""
    obsolete: bool = False


def load_obo(path: str | Path) -> dict[str, Term]:
    terms: dict[str, Term] = {}
    current: Term | None = None
    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.rstrip("\n")
            if line.startswith("["):
                current = Term(id="") if line == "[Term]" else None
                continue
            if current is None or ": " not in line:
                continue
            tag, value = line.split(": ", 1)
            if tag == "id":
                current.id = value
                terms[value] = current
            elif tag == "name":
                current.name = value
            elif tag == "namespace":
                current.namespace = value
            elif tag == "is_obsolete":
                current.obsolete = value.strip() == "true"
    return terms
