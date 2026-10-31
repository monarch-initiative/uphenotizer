"""CURIE -> IRI expansion for OBO identifiers."""

import re

OBO = "http://purl.obolibrary.org/obo/"
_CURIE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*:[A-Za-z0-9_.\-]+$")


def is_curie(value: str) -> bool:
    return bool(_CURIE.match(value)) and not value.startswith("http")


def expand(curie: str) -> str:
    if not is_curie(curie):
        raise ValueError(f"Not a CURIE: {curie!r}")
    prefix, local = curie.split(":", 1)
    return f"{OBO}{prefix}_{local}"
