"""Route FlyBase source units to uPheno patterns."""

from uphenotizer.model import COVERED_UPSTREAM, ROUTED, SKIPPED, UNROUTED, Outcome, Route, Unit
from uphenotizer.obo import Term

ANATOMY_VAR = "anatomical_entity"
GO_VARS = {
    "biological_process": "biological_process",
    "cellular_component": "cellular_component",
    "molecular_function": "molecular_function",
}


def _prefix(curie: str) -> str:
    return curie.split(":", 1)[0]


class FlybaseRouter:
    def __init__(self, config: dict, fbcv: dict[str, Term], go: dict[str, Term]):
        self.config = config
        self.fbcv = fbcv
        self.go = go
        self.context = set(config["context_namespaces"])
        self.covered = set(config["covered_upstream_namespaces"])
        self.drop_prefixes = set(config["drop_prefixes"])
        self.modifiers = {k for k in config["anatomy"] if k != "none"}

    def configured_patterns(self) -> dict[str, list[str]]:
        patterns = {p: [ANATOMY_VAR] for p in self.config["anatomy"].values()}
        patterns.update({p: [GO_VARS[ns]] for ns, p in self.config["go"].items()})
        return patterns

    def route(self, unit: Unit) -> Outcome:
        if not unit.terms:
            return Outcome(unit, SKIPPED, reason="no phenotype terms")
        head, rest = unit.terms[0], unit.terms[1:]

        if _prefix(head) == "FBcv":
            ns = self.fbcv.get(head, Term(head)).namespace
            if ns in self.covered:
                return Outcome(unit, COVERED_UPSTREAM, rule="fb:dpo",
                               reason="head term is a DPO class")
            return Outcome(unit, UNROUTED, reason=f"head FBcv term {head} in namespace {ns!r}")

        modifiers, blocking = [], []
        for term in rest:
            if _prefix(term) in self.drop_prefixes:
                continue
            if _prefix(term) == "FBcv":
                if term in self.modifiers:
                    modifiers.append(term)
                    continue
                if self.fbcv.get(term, Term(term)).namespace in self.context:
                    continue
            blocking.append(term)
        if blocking:
            return Outcome(unit, UNROUTED, reason="unhandled qualifiers: " + " ".join(blocking))
        if len(modifiers) > 1:
            return Outcome(unit, UNROUTED, reason="multiple modifiers: " + " ".join(modifiers))
        modifier = modifiers[0] if modifiers else "none"

        if _prefix(head) == "FBbt":
            pattern = self.config["anatomy"][modifier]
            return Outcome(unit, ROUTED, rule=f"fb:anatomy:{modifier}",
                           route=Route.of(pattern, **{ANATOMY_VAR: head}))

        if _prefix(head) == "GO":
            if modifier != "none":
                return Outcome(unit, UNROUTED, reason=f"GO head with modifier {modifier}")
            term = self.go.get(head)
            if term is None or term.obsolete:
                return Outcome(unit, UNROUTED, reason=f"{head} unknown or obsolete in GO")
            pattern = self.config["go"].get(term.namespace)
            if pattern is None:
                return Outcome(unit, UNROUTED, reason=f"no pattern for GO namespace {term.namespace}")
            return Outcome(unit, ROUTED, rule=f"fb:go:{term.namespace}",
                           route=Route.of(pattern, **{GO_VARS[term.namespace]: head}))

        return Outcome(unit, UNROUTED, reason=f"unhandled head term prefix {_prefix(head)}")
