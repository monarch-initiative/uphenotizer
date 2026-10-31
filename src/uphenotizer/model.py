"""Core data types shared by loaders, routers and writers."""

from dataclasses import dataclass, field

ROUTED = "routed"
PENDING = "pending"
COVERED_UPSTREAM = "covered_upstream"
SKIPPED = "skipped"
UNROUTED = "unrouted"


@dataclass
class Unit:
    """One distinct source annotation shape, aggregated over all records that share it."""

    source: str
    terms: tuple[str, ...]
    chemical: str | None = None
    annotations: int = 0
    example_statement: str = ""


@dataclass(frozen=True)
class Route:
    """A target pattern and its fillers (variable name -> CURIE)."""

    pattern: str
    fillers: tuple[tuple[str, str], ...]

    @classmethod
    def of(cls, pattern: str, **fillers: str) -> "Route":
        return cls(pattern, tuple(sorted(fillers.items())))

    def filler_dict(self) -> dict[str, str]:
        return dict(self.fillers)


@dataclass
class Outcome:
    """What happened to a unit: a status, the rule that fired, and the route if any."""

    unit: Unit
    status: str
    rule: str = ""
    route: Route | None = None
    reason: str = ""
    extra: dict = field(default_factory=dict)
