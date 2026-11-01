"""Command line entry points: ``uphenotizer run`` (route, mint, DOSDP tables) and
``uphenotizer release`` (templates, SSSOM, summary after ODK classification)."""

import argparse
import sys
from pathlib import Path

import yaml

from uphenotizer.alliance import load_records, units_flybase, units_sgd
from uphenotizer.dosdp_tables import bind, update_idmaps, write_dosdp_tables
from uphenotizer.obo import load_obo
from uphenotizer.release import release
from uphenotizer.route_fb import FlybaseRouter
from uphenotizer.route_sgd import SgdRouter, load_exact_go, load_rules, read_tsv
from uphenotizer.upheno import PatternCatalog, UphenoIdMap, UphenoSource
from uphenotizer.write import ConfigError, finalize, validate_patterns, write_outputs


def run(args: argparse.Namespace) -> int:
    if not args.fb and not args.sgd:
        print("Nothing to do: pass --fb and/or --sgd", file=sys.stderr)
        return 2
    config = Path(args.config)
    source = UphenoSource(args.upheno_dir, cache_dir=args.cache)
    catalog = PatternCatalog(source, args.patterns)
    go = load_obo(args.go)

    routers = []
    if args.fb:
        fb_router = FlybaseRouter(yaml.safe_load((config / "flybase.yaml").read_text()),
                                  load_obo(args.fbcv), go)
        routers.append((fb_router, lambda: units_flybase(load_records(args.fb))))
    if args.sgd:
        sgd_router = SgdRouter(load_rules(config / "sgd_rules.tsv"),
                               {r["qualifier"] for r in read_tsv(config / "sgd_skip.tsv")},
                               load_exact_go(Path(args.mappings) / "apo_go.sssom.tsv"), go)
        routers.append((sgd_router, lambda: units_sgd(load_records(args.sgd))))

    configured: dict[str, list[str]] = {}
    for router, _ in routers:
        configured.update(router.configured_patterns())
    try:
        validate_patterns(configured, catalog)
    except ConfigError as e:
        print(e, file=sys.stderr)
        return 1

    upheno_ids = UphenoIdMap.from_source(source)
    outcomes = []
    for router, load_units in routers:
        outcomes.extend(router.route(u) for u in load_units())

    # Keys first, then IDs, then the binding table (source_map) can carry the class ID.
    finalize(outcomes, catalog, upheno_ids)
    sources = {s for s, given in (("FB", args.fb), ("SGD", args.sgd)) if given}
    maps = update_idmaps(outcomes, args.idmaps, sources)
    bind(outcomes, maps)
    summary = write_outputs(outcomes, catalog, upheno_ids, args.out)
    write_dosdp_tables(maps, catalog, args.dosdp_out)
    id_lines = ["", "## Component IDs", "",
                "| component | classes | minted this run | not used by current annotations |",
                "|---|---:|---:|---:|"]
    for src in sorted(sources):
        m = maps[src]
        id_lines.append(f"| {m.component.name} | {len(m.rows)} | {m.stats.get('minted', 0)} | "
                        f"{m.stats.get('unused', 0)} |")
    summary = summary.rstrip("\n") + "\n" + "\n".join(id_lines) + "\n"
    (Path(args.out) / "summary.md").write_text(summary, encoding="utf-8")
    print(summary)
    return 0


def release_cmd(args: argparse.Namespace) -> int:
    print(release(args.idmaps, args.classified, args.source_map, args.templates, args.mappings_out,
                  args.summary))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="uphenotizer")
    sub = parser.add_subparsers(dest="command", required=True)
    r = sub.add_parser("run", help="translate Alliance phenotype dumps into uPheno pattern tables")
    r.add_argument("--fb", help="PHENOTYPE_FB.json(.gz)")
    r.add_argument("--sgd", help="PHENOTYPE_SGD.json(.gz)")
    r.add_argument("--fbcv", default="tmp/fbcv.obo")
    r.add_argument("--go", default="tmp/go-basic.obo")
    r.add_argument("--mappings", default="data", help="directory with apo_*.sssom.tsv")
    r.add_argument("--config", default="config")
    r.add_argument("--patterns", default="patterns", help="local (not yet upstreamed) patterns")
    r.add_argument("--upheno-dir", help="local uPheno checkout; default: GitHub master")
    r.add_argument("--cache", default="tmp/upheno", help="cache for files fetched from GitHub")
    r.add_argument("--out", default="output")
    r.add_argument("--idmaps", default="idmaps", help="component ID maps (append-only)")
    r.add_argument("--dosdp-out", default="tmp/dosdp", help="per-component DOSDP tables")
    r.set_defaults(func=run)

    rel = sub.add_parser("release", help="templates, SSSOM and summary from the reasoned hierarchy")
    rel.add_argument("--classified", default="tmp/classified.tsv")
    rel.add_argument("--idmaps", default="idmaps")
    rel.add_argument("--source-map", default="output/source_map.tsv")
    rel.add_argument("--templates", default="tmp/templates")
    rel.add_argument("--mappings-out", default="mappings")
    rel.add_argument("--summary", default="output/summary.md")
    rel.set_defaults(func=release_cmd)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
