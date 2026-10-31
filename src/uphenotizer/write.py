"""Validate routes against uPheno and write pattern tables, the source map and reports."""

import csv
from collections import Counter, defaultdict
from pathlib import Path

from uphenotizer.curie import expand, is_curie
from uphenotizer.model import PENDING, ROUTED, UNROUTED, Outcome
from uphenotizer.upheno import PatternCatalog, UphenoIdMap, make_key

STATUSES = ["routed", "pending", "covered_upstream", "skipped", "unrouted"]


class ConfigError(Exception):
    pass


def validate_patterns(configured: dict[str, list[str]], catalog: PatternCatalog) -> None:
    """Every configured pattern must resolve, and its vars must equal the configured fillers."""
    problems = []
    for pattern, filler_vars in sorted(configured.items()):
        vars_ = catalog.vars(pattern)
        if vars_ is None:
            problems.append(f"{pattern}: not found in uPheno or in local patterns/")
        elif sorted(vars_) != sorted(filler_vars):
            problems.append(f"{pattern}: pattern vars {vars_} != configured {sorted(filler_vars)}")
    if problems:
        raise ConfigError("Invalid routing configuration:\n  " + "\n  ".join(problems))


def finalize(outcomes: list[Outcome], catalog: PatternCatalog, idmap: UphenoIdMap) -> None:
    """Mark local-pattern routes as pending, reject malformed fillers, attach keys and IDs."""
    for o in outcomes:
        if o.route is None or o.status != ROUTED:
            continue
        fillers = o.route.filler_dict()
        bad = [v for v in fillers.values() if not is_curie(v)]
        if bad:
            o.status, o.reason = UNROUTED, "malformed filler: " + " ".join(bad)
            continue
        o.extra["key"] = make_key(fillers, o.route.pattern)
        if catalog.is_local(o.route.pattern):
            o.status = PENDING
        else:
            o.extra["defined_class"] = idmap.lookup(fillers, o.route.pattern) or ""


def _write_tsv(path: Path, header: list[str], rows: list[list]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


def write_pattern_tables(outcomes: list[Outcome], outdir: Path) -> dict[str, Counter]:
    """Write output/patterns and output/pending. Returns per-pattern counts (rows, reused)."""
    tables: dict[tuple[str, str], dict[tuple, str]] = defaultdict(dict)
    table_vars: dict[tuple[str, str], list[str]] = {}
    for o in outcomes:
        if o.status in (ROUTED, PENDING):
            table = ("patterns" if o.status == ROUTED else "pending", o.route.pattern)
            tables[table][tuple(v for _, v in o.route.fillers)] = o.extra.get("defined_class", "")
            table_vars[table] = [k for k, _ in o.route.fillers]

    for folder in ("patterns", "pending"):
        d = outdir / folder
        d.mkdir(parents=True, exist_ok=True)
        for stale in d.glob("*.tsv"):
            stale.unlink()

    stats: dict[str, Counter] = {}
    for (folder, pattern), rows in sorted(tables.items()):
        body = sorted([[expand(v) for v in row] + [rows[row]] for row in rows])
        _write_tsv(outdir / folder / f"{pattern}.tsv",
                   table_vars[(folder, pattern)] + ["defined_class"], body)
        stats[pattern] = Counter(rows=len(body), reused=sum(1 for r in body if r[-1]),
                                 pending=len(body) if folder == "pending" else 0)
    return stats


def write_source_map(outcomes: list[Outcome], outdir: Path) -> None:
    """The binding table: (source, source_terms, chemical) -> class_id, recomputed on every run.

    A consumer binds an Alliance record by its ordered term IDs and ChEBI condition. Because bindings
    are recomputed from the current data, a record whose chemical appears in a later export moves from
    the fallback class to the specific class without any manual step.
    """
    header = ["source", "source_terms", "chemical", "annotations", "example_statement", "status",
              "rule", "pattern", "key", "class_id", "upheno_id", "reason"]
    rows = [[o.unit.source, "|".join(o.unit.terms), o.unit.chemical or "", o.unit.annotations,
             o.unit.example_statement, o.status, o.rule, o.route.pattern if o.route else "",
             o.extra.get("key", ""), o.extra.get("class_id", ""), o.extra.get("defined_class", ""),
             o.reason]
            for o in outcomes]
    rows.sort(key=lambda r: (r[0], -r[3], r[1], r[2]))
    _write_tsv(outdir / "source_map.tsv", header, rows)


def unrouted_groups(outcomes: list[Outcome]) -> list[list]:
    """Unrouted units grouped by (source, terms, reason); chemicals are counted, not split."""
    groups: dict[tuple, list] = {}
    for o in outcomes:
        if o.status != UNROUTED:
            continue
        k = (o.unit.source, "|".join(o.unit.terms), o.reason)
        g = groups.setdefault(k, [o.unit.source, k[1], 0, set(), o.unit.example_statement, o.reason])
        g[2] += o.unit.annotations
        if o.unit.chemical:
            g[3].add(o.unit.chemical)
    rows = [[s, t, n, len(chems), ex, reason] for s, t, n, chems, ex, reason in groups.values()]
    rows.sort(key=lambda r: (-r[2], r[0], r[1]))
    return rows


def write_unrouted(outcomes: list[Outcome], outdir: Path) -> list[list]:
    rows = unrouted_groups(outcomes)
    _write_tsv(outdir / "unrouted.tsv", ["source", "source_terms", "annotations", "chemicals",
                                         "example_statement", "reason"], rows)
    return rows


def summary_markdown(outcomes: list[Outcome], pattern_stats: dict[str, Counter],
                     unrouted: list[list], top: int = 15) -> str:
    by_source: dict[str, dict[str, Counter]] = defaultdict(lambda: defaultdict(Counter))
    for o in outcomes:
        c = by_source[o.unit.source][o.status]
        c["units"] += 1
        c["annotations"] += o.unit.annotations

    lines = ["# uphenotizer run summary", "", "## Coverage by source", "",
             "| source | status | units | annotations | share of annotations |",
             "|---|---|---:|---:|---:|"]
    for source in sorted(by_source):
        total = sum(c["annotations"] for c in by_source[source].values()) or 1
        for status in STATUSES:
            c = by_source[source].get(status)
            if c:
                lines.append(f"| {source} | {status} | {c['units']} | {c['annotations']} | "
                             f"{100 * c['annotations'] / total:.1f}% |")

    fallback = [o for o in outcomes if o.extra.get("fallback") and o.status in (ROUTED, PENDING)]
    if fallback:
        lines += ["", (f"**Fallback bindings:** {sum(o.unit.annotations for o in fallback)} annotations "
                  f"({len(fallback)} units) are bound to a generic chemical class because the Alliance "
                  "export has no ChEBI condition for them. They re-bind to the specific class as soon as "
                  "the export carries the chemical.")]

    lines += ["", "## Pattern tables", "",
              "| pattern | rows | existing uPheno ID | needs minting | pending |",
              "|---|---:|---:|---:|---:|"]
    for pattern, s in sorted(pattern_stats.items()):
        new = s["rows"] - s["reused"] - s["pending"]
        lines.append(f"| {pattern} | {s['rows']} | {s['reused']} | {new} | {s['pending']} |")

    lines += ["", f"## Top {top} unrouted (by annotation count)", "",
              "| source | terms | annotations | example | reason |", "|---|---|---:|---|---|"]
    for s, t, n, _, ex, reason in unrouted[:top]:
        lines.append(f"| {s} | `{t}` | {n} | {ex} | {reason} |")
    lines.append("")
    return "\n".join(lines)


def write_outputs(outcomes: list[Outcome], catalog: PatternCatalog, idmap: UphenoIdMap,
                  outdir: str | Path) -> str:
    outdir = Path(outdir)
    finalize(outcomes, catalog, idmap)
    stats = write_pattern_tables(outcomes, outdir)
    write_source_map(outcomes, outdir)
    unrouted = write_unrouted(outcomes, outdir)
    summary = summary_markdown(outcomes, stats, unrouted)
    (outdir / "summary.md").write_text(summary, encoding="utf-8")
    return summary
