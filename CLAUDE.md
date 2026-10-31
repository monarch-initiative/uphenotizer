# CLAUDE.md

uphenotizer turns Alliance FlyBase/SGD phenotype annotations into two phenotype components, DPO-ext
and APO-ext, plus bridges classifying them under uPheno. Both mint IRIs
`https://w3id.org/monarch-initiative/entity/PHENOTYPE_<7 digits>` (CURIE `PHENOTYPE:`) from disjoint ranges:
DPO-ext 1000000–1999999, APO-ext 2000000–2999999 (`components.py`; enforced, never overlap).
PHENIO consumes them, and uPheno never imports them. Read `README.md` for the design decisions and
`specs/2026-10-31-weekly-pattern-pipeline-design.md` for the full design, spike numbers and decision log.

## Commands

```bash
make install                           # uv sync
make test                              # pytest, offline (no network in tests, ever)
make lint                              # ruff
make download                          # Alliance dumps, OBO files, reasoning context (~1 GB) into tmp/
make route UPHENO_DIR=~/ws/ont/upheno  # Python: route, mint IDs, DOSDP tables, reports (~20 s)
make components                        # ODK: generate, classify (ELK, ~3 min, ~10 GB), release, assemble
make all                               # what CI runs: download + mappings + route + components
```

ODK steps run as `docker run -i obolibrary/odkfull:v1.7 sh scripts/odk-*.sh`. Never use `-t` (it breaks
non-TTY shells). Set `ODK=` to run them natively inside an ODK image, and `ODK_MEM` to change the heap.

## Layout

- `src/uphenotizer/`
  - `alliance.py`: loads the dumps and aggregates them into `Unit`s. FB: term tuple. SGD: terms + one ChEBI condition.
  - `route_fb.py`, `route_sgd.py`: map `Unit` to an `Outcome` (status, rule, `Route(pattern, fillers)`, reason).
  - `upheno.py`: uPheno access (local checkout or raw GitHub, cached in `tmp/upheno`), `PatternCatalog`,
    `UphenoIdMap` (uPheno's own ID map, used only to report reuse), keys.
  - `write.py`: validation, `output/patterns`, `source_map.tsv`, `unrouted.tsv`, `summary.md`.
  - `components.py`, `idmap.py`: the two components and their append-only ID maps.
  - `dosdp_tables.py`: mints IDs and writes `tmp/dosdp/<component>/<pattern>.tsv`, the pattern YAMLs and `fillers.txt`.
  - `classify.py`: reads the ELK export and finds the nearest targets, walking through other classes and
    their equivalents, without redundant targets.
  - `release.py`: ROBOT templates (base, bridge), SSSOM, and the summary section.
- `scripts/odk-{generate,classify,assemble}.sh`: the ODK steps. `sparql/obsolete-labels.ru` handles deprecated labels.
- `config/`: routing tables. **Curation lives here, not in code.**
- `data/apo_*.sssom.tsv`: APO mappings downloaded from a Google Sheet (the source of truth). Never hand-edit them.
- `patterns/`: local patterns not yet in uPheno. Rows routed to them go to `output/pending/`.
- `idmaps/`, `release/` and `output/`: generated and committed. Never hand-edit them (except to fix `idmaps/`
  by deliberate curation); rerun the pipeline instead.

## Invariants (do not break)

- **IDs are minted here, append-only.** `idmaps/*.tsv` rows are never deleted or reassigned. When a key
  disappears from the data, its class is deprecated. A run with only one source must never touch the
  other component's map (`update_idmaps(..., sources)`).
- **Never mint UPHENO IDs or change uPheno.** uPheno may pull classes from here, but that's its process, not ours.
- **Released components contain no logical definitions.** They're generated and reasoned over, then removed in
  `odk-assemble.sh`. The hierarchy and bridges are materialised.
- **Bridges come from reasoning.** `SubClassOf(ext class, UPHENO class)` must be entailed, never a lexical
  guess. ROBOT needs `--axiom-generators "SubClass EquivalentClass"`, or `ext ≡ UPHENO` is lost.
- **The key format matches uPheno's minter** (`lib.add_upheno_id` in obophenotype/upheno): filler values
  ordered by *variable name*, joined with `-`, then the pattern name. uPheno's form uses full IRIs plus
  `.tsv`, and ours uses CURIEs. If you change ordering or format, ID reuse silently breaks.
- **`output/patterns` tables contain only the pattern vars (sorted) plus `defined_class`.** uPheno builds its key
  from every non-`defined_class` column.
- **No lossy routing.** Only drop qualifiers that are genetic or experimental context. A qualifier
  that changes the phenotype makes the unit `unrouted` until a rule covers it faithfully.
- **Output is deterministic and sorted**, so weekly PR diffs stay readable.
- Patterns resolve from uPheno `src/patterns/{dosdp-patterns,dosdp-dev,dosdp-patterns-curated}`, in that
  order. Some patterns in active use, such as `abnormalAnatomicalEntity`, live in `dosdp-dev`.

## Adding coverage

1. Look at the top of `output/unrouted.tsv`.
2. SGD: add a row to `config/sgd_rules.tsv`. FlyBase: extend `config/flybase.yaml`, or `route_fb.py` if the
   logic is new.
3. Check that the target pattern exists in uPheno and that its `vars` match your filler variable. The run fails
   loudly if they don't.
4. Add a router test for the new case, run `make test`, then `make route components`, and check `output/summary.md`.

## Context

- The target is current uPheno (`~/ws/ont/upheno`, `obophenotype/upheno@master`). `upheno-dev` is dead.
- The consumer is PHENIO (`~/ws/ont/phenio`, components in `src/ontology/phenio-odk.yaml`).
- The ID-map idea is borrowed from ZP (`~/ws/ont/zebrafish-phenotype-ontology`, `src/curation/id_map.tsv`).
- Related issues: #3 (SGD chemical conditions as fillers, implemented by the `chemical` filler), #1 (APO mappings).
