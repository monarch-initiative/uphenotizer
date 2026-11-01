"""Append-only ID maps for the components (``idmaps/<component>.tsv``).

An ID, once minted for a key, is never reassigned or removed, and its class stays in the release even
when no current annotation uses the key. There is no deprecation: these classes are not meant for
curation or annotation (see the usage note on every class), so they have no curation lifecycle.
Rows for classes that were never released may be removed by hand.
"""

import csv
from pathlib import Path

from uphenotizer.components import Component

HEADER = ["id", "key"]


class ComponentIdMap:
    def __init__(self, component: Component, path: str | Path):
        self.component = component
        self.path = Path(path)
        self.rows: dict[str, dict] = {}  # key -> row
        self.stats: dict[str, int] = {}  # from the last update()
        if self.path.exists():
            with open(self.path, encoding="utf-8") as f:
                for row in csv.DictReader(f, delimiter="\t"):
                    self.rows[row["key"]] = {"id": row["id"], "key": row["key"]}

    def _next_number(self) -> int:
        numbers = [int(r["id"].rsplit(":", 1)[1]) for r in self.rows.values()]
        return max(numbers, default=self.component.first - 1) + 1

    def update(self, current_keys: set[str]) -> dict[str, int]:
        """Mint IDs for new keys. Returns counts: minted, and keys without current annotations."""
        number = self._next_number()
        minted = 0
        for key in sorted(current_keys - self.rows.keys()):
            iri = self.component.iri(number)
            self.rows[key] = {"id": self.component.curie(iri), "key": key}
            number += 1
            minted += 1
        self.stats = {"minted": minted, "unused": len(self.rows.keys() - current_keys)}
        return self.stats

    def iri(self, key: str) -> str:
        return self.component.iri_base + self.rows[key]["id"].rsplit(":", 1)[1]

    def items(self):
        """(key, iri), ordered by ID."""
        for row in sorted(self.rows.values(), key=lambda r: r["id"]):
            yield row["key"], self.iri(row["key"])

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, HEADER, delimiter="\t", lineterminator="\n")
            w.writeheader()
            w.writerows(sorted(self.rows.values(), key=lambda r: r["id"]))
