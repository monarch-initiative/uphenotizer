"""Append-only ID maps for the components (``idmaps/<component>.tsv``).

An ID, once minted for a key, is never reassigned or deleted. Keys missing from the current data are
marked ``deprecated``; a key that comes back is marked ``active`` again under its old ID.
"""

import csv
from pathlib import Path

from uphenotizer.components import Component

ACTIVE = "active"
DEPRECATED = "deprecated"
HEADER = ["id", "key", "status"]


class ComponentIdMap:
    def __init__(self, component: Component, path: str | Path):
        self.component = component
        self.path = Path(path)
        self.rows: dict[str, dict] = {}  # key -> row
        self.stats: dict[str, int] = {}  # changes from the last update()
        if self.path.exists():
            with open(self.path, encoding="utf-8") as f:
                for row in csv.DictReader(f, delimiter="\t"):
                    self.rows[row["key"]] = row

    def _next_number(self) -> int:
        numbers = [int(r["id"].rsplit(":", 1)[1]) for r in self.rows.values()]
        return max(numbers, default=self.component.first - 1) + 1

    def update(self, current_keys: set[str]) -> dict[str, int]:
        """Mint IDs for new keys, (un)deprecate the rest. Returns counts per change type."""
        stats = {"minted": 0, "deprecated": 0, "reactivated": 0}
        number = self._next_number()
        for key in sorted(current_keys - self.rows.keys()):
            iri = self.component.iri(number)
            self.rows[key] = {"id": self.component.curie(iri), "key": key, "status": ACTIVE}
            number += 1
            stats["minted"] += 1
        for key, row in self.rows.items():
            if key in current_keys and row["status"] == DEPRECATED:
                row["status"] = ACTIVE
                stats["reactivated"] += 1
            elif key not in current_keys and row["status"] == ACTIVE:
                row["status"] = DEPRECATED
                stats["deprecated"] += 1
        self.stats = stats
        return stats

    def iri(self, key: str) -> str:
        return self.component.iri_base + self.rows[key]["id"].rsplit(":", 1)[1]

    def items(self):
        """(key, iri, status), ordered by ID."""
        for row in sorted(self.rows.values(), key=lambda r: r["id"]):
            yield row["key"], self.iri(row["key"]), row["status"]

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, HEADER, delimiter="\t", lineterminator="\n")
            w.writeheader()
            w.writerows(sorted(self.rows.values(), key=lambda r: r["id"]))
