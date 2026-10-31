"""Access to uPheno: pattern definitions and the uPheno ID map.

uPheno is read either from a local checkout (``--upheno-dir``) or from raw GitHub (master),
with downloaded files cached under ``cache_dir``.
"""

import csv
import io
import urllib.error
import urllib.request
from pathlib import Path

import yaml

from uphenotizer.curie import expand

RAW_BASE = "https://raw.githubusercontent.com/obophenotype/upheno/master/"
PATTERN_DIRS = (
    "src/patterns/dosdp-patterns",
    "src/patterns/dosdp-dev",
    "src/patterns/dosdp-patterns-curated",
)
ID_MAP_PATH = "src/curation/upheno_id_map.txt"


class UphenoSource:
    """Reads files from a uPheno checkout or from GitHub. Returns None for missing files."""

    def __init__(self, local_dir: str | Path | None = None, cache_dir: str | Path = "tmp/upheno",
                 base_url: str = RAW_BASE):
        self.local_dir = Path(local_dir) if local_dir else None
        self.cache_dir = Path(cache_dir)
        self.base_url = base_url

    def read(self, relpath: str) -> str | None:
        if self.local_dir:
            p = self.local_dir / relpath
            return p.read_text(encoding="utf-8") if p.exists() else None
        cached = self.cache_dir / relpath
        if cached.exists():
            return cached.read_text(encoding="utf-8")
        try:
            with urllib.request.urlopen(self.base_url + relpath, timeout=120) as resp:
                text = resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            raise
        cached.parent.mkdir(parents=True, exist_ok=True)
        cached.write_text(text, encoding="utf-8")
        return text


class PatternCatalog:
    """Resolves pattern names to their variable names, preferring uPheno over local patterns."""

    def __init__(self, source: UphenoSource, local_patterns_dir: str | Path = "patterns"):
        self.source = source
        self.local_dir = Path(local_patterns_dir)
        self._cache: dict[str, tuple[list[str], bool, str] | None] = {}

    def _resolve(self, pattern: str) -> tuple[list[str], bool, str] | None:
        if pattern not in self._cache:
            found = None
            for d in PATTERN_DIRS:
                text = self.source.read(f"{d}/{pattern}.yaml")
                if text is not None:
                    found = (sorted(yaml.safe_load(text).get("vars", {})), False, text)
                    break
            if found is None:
                local = self.local_dir / f"{pattern}.yaml"
                if local.exists():
                    text = local.read_text()
                    found = (sorted(yaml.safe_load(text).get("vars", {})), True, text)
            self._cache[pattern] = found
        return self._cache[pattern]

    def yaml_text(self, pattern: str) -> str | None:
        resolved = self._resolve(pattern)
        return resolved[2] if resolved else None

    def vars(self, pattern: str) -> list[str] | None:
        resolved = self._resolve(pattern)
        return resolved[0] if resolved else None

    def is_local(self, pattern: str) -> bool:
        resolved = self._resolve(pattern)
        return bool(resolved and resolved[1])


def make_key(fillers: dict[str, str], pattern: str) -> str:
    """ZP-style key: filler CURIEs ordered by variable name, then the pattern name."""
    return "-".join([fillers[v] for v in sorted(fillers)] + [pattern])


def upheno_key(fillers: dict[str, str], pattern: str) -> str:
    """The same key in uPheno's upheno_id_map.txt form (full IRIs, ``.tsv`` suffix)."""
    return "-".join([expand(fillers[v]) for v in sorted(fillers)] + [f"{pattern}.tsv"])


class UphenoIdMap:
    """uPheno's ID map: key (IRI form) -> UPHENO IRI. Duplicate keys resolve to the lowest IRI."""

    def __init__(self, text: str):
        self._map: dict[str, str] = {}
        for row in csv.DictReader(io.StringIO(text), delimiter="\t"):
            key, iri = row["id"], row["defined_class"]
            if key not in self._map or iri < self._map[key]:
                self._map[key] = iri

    @classmethod
    def from_source(cls, source: UphenoSource) -> "UphenoIdMap":
        text = source.read(ID_MAP_PATH)
        if text is None:
            raise FileNotFoundError(f"uPheno ID map not found at {ID_MAP_PATH}")
        return cls(text)

    def lookup(self, fillers: dict[str, str], pattern: str) -> str | None:
        return self._map.get(upheno_key(fillers, pattern))

    def __len__(self) -> int:
        return len(self._map)
