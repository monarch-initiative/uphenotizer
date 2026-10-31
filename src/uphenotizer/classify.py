"""Read the reasoned hierarchy (ROBOT export) and derive groupings for component classes.

The export has columns ``ID | LABEL | SubClass Of | Equivalent Class`` with direct inferred
superclasses and named equivalents (ROBOT ``reason --axiom-generators "SubClass EquivalentClass"``).
"""

import csv
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

UPHENO_PREFIX = "UPHENO:"


def is_upheno(c: str) -> bool:
    return c.startswith(UPHENO_PREFIX)


def _named(cell: str) -> set[str]:
    return {x for x in cell.split("|") if x and " " not in x and not x.startswith("(")}


@dataclass
class Hierarchy:
    supers: dict[str, set[str]] = field(default_factory=dict)
    equivs: dict[str, set[str]] = field(default_factory=dict)
    labels: dict[str, str] = field(default_factory=dict)
    _anc: dict[str, frozenset] = field(default_factory=dict, repr=False)

    @classmethod
    def from_export(cls, path: str | Path) -> "Hierarchy":
        csv.field_size_limit(sys.maxsize)
        h = cls()
        with open(path, encoding="utf-8") as f:
            reader = csv.reader(f, delimiter="\t")
            next(reader)
            for row in reader:
                row += [""] * (4 - len(row))
                cid, label, sub, eq = row[:4]
                if label:
                    h.labels[cid] = label
                if s := _named(sub) - {"owl:Thing"}:
                    h.supers[cid] = s
                if e := _named(eq):
                    h.equivs[cid] = e
        return h

    def ancestors(self, c: str) -> frozenset:
        """All strict named ancestors (iterative, memoised)."""
        if c in self._anc:
            return self._anc[c]
        stack, seen = [c], {c}
        while stack:  # post-order so parents are memoised before children
            x = stack[-1]
            pending = [p for p in self.supers.get(x, ()) if p not in self._anc and p not in seen]
            if pending:
                seen.update(pending)
                stack.extend(pending)
                continue
            stack.pop()
            acc = set()
            for p in self.supers.get(x, ()):
                acc.add(p)
                acc |= self._anc.get(p, frozenset())
            self._anc[x] = frozenset(acc)
        return self._anc[c]

    def irredundant(self, targets: set[str]) -> set[str]:
        return {t for t in targets if not any(t in self.ancestors(o) for o in targets if o != t)}

    def nearest(self, c: str, is_target: Callable[[str], bool]) -> set[str]:
        """The most specific targets above ``c``, walking through non-target classes."""
        found: set[str] = set()
        seen = {c}
        stack = list(self.supers.get(c, ()))
        while stack:
            x = stack.pop()
            if x in seen:
                continue
            seen.add(x)
            hits = {y for y in {x} | self.equivs.get(x, set()) if is_target(y)}
            if hits:
                found |= hits
            else:
                stack.extend(self.supers.get(x, ()))
        return self.irredundant(found)

    def exact(self, c: str, is_target: Callable[[str], bool]) -> set[str]:
        return {e for e in self.equivs.get(c, set()) if is_target(e)}
