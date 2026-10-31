"""Route SGD source units (APO qualifier + APO observable [+ ChEBI condition]) to uPheno patterns."""

import csv
from dataclasses import dataclass
from pathlib import Path

from uphenotizer.alliance import UNMAPPED_CHEMICAL
from uphenotizer.model import ROUTED, SKIPPED, UNROUTED, Outcome, Route, Unit
from uphenotizer.obo import Term

GO_WILDCARD = "GO"


@dataclass(frozen=True)
class SgdRule:
    qualifier: str
    observable: str
    pattern: str
    filler_var: str
    filler: str  # "chemical" or "observable_go"
    fallback: str

    @property
    def name(self) -> str:
        return f"sgd:{self.qualifier}:{self.observable}"


def read_tsv(path: str | Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader((line for line in f if not line.startswith("#")),
                                   delimiter="\t"))


def load_rules(path: str | Path) -> list[SgdRule]:
    rules = []
    for row in read_tsv(path):
        if row["filler"] not in ("chemical", "observable_go"):
            raise ValueError(f"{path}: unknown filler {row['filler']!r}")
        rules.append(SgdRule(row["qualifier"], row["observable"], row["pattern"],
                             row["filler_var"], row["filler"], (row["fallback"] or "").strip()))
    return rules


def load_exact_go(sssom_path: str | Path) -> dict[str, str]:
    """APO observable -> GO term, for skos:exactMatch rows only."""
    return {
        r["subject_id"]: r["object_id"].strip()
        for r in read_tsv(sssom_path)
        if r.get("predicate_id") == "skos:exactMatch" and r.get("object_id", "").startswith("GO:")
    }


class SgdRouter:
    def __init__(self, rules: list[SgdRule], skip: set[str], apo_go: dict[str, str],
                 go: dict[str, Term]):
        self.specific = {(r.qualifier, r.observable): r for r in rules
                         if r.observable != GO_WILDCARD}
        self.wildcard = {r.qualifier: r for r in rules if r.observable == GO_WILDCARD}
        self.rules = rules
        self.skip = skip
        self.apo_go = apo_go
        self.go = go

    def configured_patterns(self) -> dict[str, list[str]]:
        return {r.pattern: [r.filler_var] for r in self.rules}

    def route(self, unit: Unit) -> Outcome:
        if not unit.terms:
            return Outcome(unit, SKIPPED, reason="no phenotype terms")
        qualifier = unit.terms[0]
        if qualifier in self.skip:
            return Outcome(unit, SKIPPED, reason=f"{qualifier} is not an abnormal phenotype")
        if len(unit.terms) != 2:
            return Outcome(unit, UNROUTED, reason=f"expected qualifier + observable, "
                                                  f"got {len(unit.terms)} term(s)")
        observable = unit.terms[1]

        rule = self.specific.get((qualifier, observable))
        if rule is None and qualifier in self.wildcard and observable in self.apo_go:
            rule = self.wildcard[qualifier]
        if rule is None:
            return Outcome(unit, UNROUTED, reason="no rule for qualifier/observable")

        if rule.filler == "chemical":
            if unit.chemical and unit.chemical.startswith(UNMAPPED_CHEMICAL):
                return Outcome(unit, UNROUTED, rule=rule.name,
                               reason=f"chemical condition not mapped to ChEBI: "
                                      f"{unit.chemical[len(UNMAPPED_CHEMICAL):]}")
            if unit.chemical:
                value = unit.chemical
            elif rule.fallback:
                # Bound to a generic class for now. When the Alliance export later carries the
                # chemical, the record becomes a different unit and is re-bound to the specific class.
                return Outcome(unit, ROUTED, rule=rule.name,
                               route=Route.of(rule.pattern, **{rule.filler_var: rule.fallback}),
                               reason=f"fallback {rule.fallback}: no ChEBI condition in Alliance export",
                               extra={"fallback": True})
            else:
                return Outcome(unit, UNROUTED, rule=rule.name,
                               reason="rule needs a chemical condition and has no fallback")
        else:
            value = self.apo_go[observable]
            term = self.go.get(value)
            if term is None or term.obsolete or term.namespace != "biological_process":
                return Outcome(unit, UNROUTED, rule=rule.name,
                               reason=f"{value} is not a current GO biological process")
        return Outcome(unit, ROUTED, rule=rule.name,
                       route=Route.of(rule.pattern, **{rule.filler_var: value}))
