# uphenotizer

uphenotizer turns **FlyBase and SGD phenotype annotations** (from the
[Alliance](https://www.alliancegenome.org/) bulk downloads) into two phenotype ontology components,
**DPO-ext** and **APO-ext**, and **bridges them into [uPheno](https://github.com/obophenotype/upheno)**.
Both are consumed by [PHENIO](https://github.com/monarch-initiative/phenio).

Why it exists: both MODs annotate phenotypes *post-composed*. FlyBase uses an anatomy, GO or
FBcv term plus qualifiers; SGD uses an APO qualifier ("decreased"), an APO observable
("resistance to chemicals") and often a ChEBI condition. Monarch needs a pre-composed class for
each combination, classified under uPheno, so that fly and yeast gene→phenotype associations
integrate with every other species.

## Design decisions

1. **Two components, minted here.**
   - **DPO-ext** holds the FlyBase phenotypes DPO doesn't pre-compose (anatomy- and GO-based). It's
     formally a legal extension of DPO.
   - **APO-ext** holds the SGD phenotypes. It does for SGD what ZP does for ZFIN. (APO is really a trait
     ontology; ideally it would have been called ATO and this module APO.)

   Both components share one namespace, `https://w3id.org/monarch-initiative/entity/PHENOTYPE_<7 digits>`
   (CURIE `PHENOTYPE:<7 digits>`), and mint from disjoint number ranges:

   | | DPO-ext | APO-ext |
   |---|---|---|
   | ID range | `PHENOTYPE:1000000`–`1999999` | `PHENOTYPE:2000000`–`2999999` |
   | Example IRI | `https://w3id.org/monarch-initiative/entity/PHENOTYPE_1000000` | `…/entity/PHENOTYPE_2000000` |
   | Release files | `https://w3id.org/monarch-initiative/uphenotizer/release/dpo-ext-*.owl` | `…/release/apo-ext-*.owl` |

   Class IRIs resolve to `monarchinitiative.org/<id>`. File IRIs resolve via the w3id fallthrough to
   `monarch-initiative.github.io/uphenotizer/release/…`, which needs GitHub Pages enabled for this repo
   (branch `main`, root). See [perma-id/w3id.org#7041](https://github.com/perma-id/w3id.org/pull/7041).

2. **Classes are instances of uPheno patterns.** Every class is a uPheno DOSDP pattern filled with the
   MOD's terms: FBbt for fly anatomy, GO for processes, CHEBI for chemicals. The logical definition is
   used here for classification only. **The released components don't contain logical definitions**, just
   the computed hierarchy and bridges, so PHENIO never infers equivalences to uPheno classes. FlyBase
   records whose head term is already a DPO class are left to DPO.
3. **The bridges to uPheno are built here.** Reasoning over the logical definitions, uPheno and the
   FBbt→UBERON/CL bridges gives every class its **most specific existing uPheno grouping**. The groupings
   are shipped as `SubClassOf(ext class, UPHENO class)`, the same shape as uPheno's own `upheno-bridge.owl`.
   Many SGD classes (CHEBI or GO fillers) turn out to be equivalent to existing uPheno classes, and that is
   recorded as a cross-species exact match.
4. **uPheno is untouched.** uPheno 2 accepts only species-neutral fillers, and fly-specific classes such as
   *abnormal FBbt:X* formally don't belong there. The components are imported into **PHENIO**, not uPheno.
   uPheno can later pull classes from here voluntarily and mint UPHENO IDs for them; `output/patterns/*.tsv`
   is ready for that.
5. **Direct links to the affected entity.** Each class carries `SubClassOf(P, UPHENO:0000001 some E)`
   ("phenotype affects entity") and `SubClassOf(P, UPHENO:0000003 some E)` ("phenotype is associated
   with entity"). These are exactly what PHENIO's `upheno:extract-upheno-relations` adds to other
   phenotypes, with E being the bearer of the logical definition (the `inheres_in` /
   `inheres_in_part_of` filler). PHENIO can't derive them for our classes because they ship without
   logical definitions, so we materialise them. Following the same rule, a resistance phenotype links
   to the organism and not to the chemical.
6. **Taxon is explicit.** Both components share the `PHENOTYPE:` prefix, so unlike HP, MP or ZP the prefix
   doesn't tell you the species. Every class therefore carries
   - `SubClassOf(P, RO:0002162 some NCBITaxon:7227)` (DPO-ext) or `… some NCBITaxon:559292` (APO-ext). This
     is "in taxon" (Biolink `in_taxon`), using the same taxon the Monarch KG gives FlyBase and SGD genes.
   - `oboInOwl:inSubset` `fly_phenotype` or `yeast_phenotype`, because Monarch search can filter by subset.
7. **IDs are stable, and nothing is deprecated.** Append-only ID maps (`idmaps/`) are keyed ZP-style:
   filler CURIEs ordered by pattern variable name, then the pattern name, e.g.
   `FBbt:00004729-abnormalAnatomicalEntity`. These classes are **not intended for curation or annotation**:
   every class says so in an `rdfs:comment` and points to uPheno classes instead. So they have no curation
   lifecycle. A class whose key no longer occurs in the data stays in the release (still classified and
   bridged), and its ID is never reused. Rows for classes that were never released can be removed by hand.
8. **No lossy translation.** Context that isn't phenotypic (dominance, clone type, sex, maternal effect,
   stage) may be dropped. Qualifiers that change the phenotype (spatial, structural, intensity) leave the
   annotation unrouted until a rule covers it faithfully. A bare FBbt annotation means *phenotype
   manifest in X*, not "abnormal X morphology". SGD chemical conditions without a ChEBI ID are never
   replaced by a generic fallback class.

Rejected alternatives and the evidence behind each decision are in
[`specs/2026-10-31-weekly-pattern-pipeline-design.md`](specs/2026-10-31-weekly-pattern-pipeline-design.md)
(decision log).

## How it works

```text
Alliance PHENOTYPE_FB/SGD ─► aggregate ─► route (config/) ─► mint IDs (idmaps/) ─► dosdp-tools generate
                                                                                   │
  uPheno full + FBbt/UBERON/CL/GO bases + ChEBI lite + FBbt bridges ─► ELK ◄───────┘
                                                                        │
                                       release/<component>-base.owl ◄───┤  (no logical definitions)
                                     release/<component>-bridge.owl ◄───┤  SubClassOf(ext, UPHENO)
                              release/<component>-upheno.sssom.tsv ◄────┘
```

### Release artefacts (`release/`)

| File | Content |
|---|---|
| `dpo-ext-base.owl`, `apo-ext-base.owl` | Classes with label and text definition (from the uPheno pattern templates), synonyms, provenance and usage comments, in-component hierarchy, links to the affected entity, in-taxon axiom and subset |
| `dpo-ext-bridge.owl`, `apo-ext-bridge.owl` | `SubClassOf(ext class, UPHENO class)`: the most specific existing uPheno grouping, or the equivalent uPheno class |
| `*-upheno.sssom.tsv` | The bridge as SSSOM: `semapv:crossSpeciesExactMatch` (equivalent) or `skos:broadMatch` (grouping), `semapv:LogicalReasoning` |

Ontology IRIs are `https://w3id.org/monarch-initiative/uphenotizer/release/<component>-base.owl` (and
`-bridge.owl`). Version IRIs (`…/uphenotizer/releases/<date>/…`) don't resolve yet, because there are no dated
copies. `idmaps/<component>.tsv` holds the append-only `id → key` maps.

### Routing

- **FlyBase** (`config/flybase.yaml`):
  - A head term that is an FBcv `phenotypic_class` term is already a DPO class, so it's `covered_upstream`.
  - A head FBbt term becomes `abnormalAnatomicalEntity`, or `abnormallyIncreased/DecreasedNumberOfAnatomicalEntity` with the FBcv number qualifiers.
  - A head GO term goes to the abnormal-process, abnormal-component or abnormal-function pattern for its GO namespace. GO cellular components also accept the number qualifiers.
  - FBbt terms that duplicate a GO cellular component without saying so (e.g. `FBbt:00005110` and
    `GO:0030425`, both "dendrite") are routed as the GO term (`fbbt_as_go`), so each pair yields one class
    instead of two with the same label. The PR summary lists any remaining duplicate labels.
- **SGD** (`config/sgd_rules.tsv`): one row per qualifier and observable, naming the target pattern and
  where the filler comes from. The filler is either the ChEBI condition (with an optional fallback class) or the observable's
  `skos:exactMatch` GO term from `data/apo_go.sssom.tsv` (`observable = GO` wildcard).
  `config/sgd_skip.tsv` lists qualifiers that aren't abnormal phenotypes.

To extend coverage, pick the top rows of `output/unrouted.tsv`, add a rule, and run again. A rule that needs a
pattern uPheno doesn't have yet gets its YAML in `patterns/`, and its rows go to `output/pending/`.

### Binding annotations to classes

`output/source_map.tsv` is the **binding table**. It maps every annotation shape, `(source, source_terms,
chemical)`, to the class it's bound to (`class_id`, e.g. `PHENOTYPE:2000535`). Bindings are recomputed from the
current Alliance data on every run, so an annotation moves to the right class automatically when the data changes.

SGD chemical phenotypes without a ChEBI condition are bound to a generic fallback class (*decreased
resistance of organism to chemical entity*), marked `fallback …` in `reason` and counted in `summary.md`. About
half of SGD's chemical annotations arrive without one: SGD names the chemical in its own data, but the Alliance export
drops chemicals that SGD hasn't mapped to ChEBI. As soon as an export carries the chemical, the record binds to
the specific class. The generic class stays in the release even once nothing binds to it anymore.

### Reports (`output/`)

| File | Content |
|---|---|
| `patterns/<pattern>.tsv` | Species-agnostic DOSDP tables (filler IRIs, then `defined_class` = existing UPHENO ID or empty). This is what uPheno can pull |
| `source_map.tsv` | The binding table: every source unit with its status, rule, pattern, key, `class_id`, matching `upheno_id` and reason |
| `unrouted.tsv` | What isn't translated yet, ranked by annotation count. This is the curation to-do list |
| `summary.md` | Coverage per source, rows per pattern, top unrouted. Used as the weekly PR body |

## Running

Requires [uv](https://docs.astral.sh/uv/), `curl` and Docker (for the ODK image `obolibrary/odkfull:v1.7`).

```bash
make install      # uv sync
make test         # offline unit tests
make all          # download, refresh APO mappings, route + mint, generate, classify, assemble
make route        # Python only: route, mint IDs, DOSDP tables, reports
make components   # ODK + Python: generate, classify (ELK), release templates/SSSOM, assemble OWL
make route UPHENO_DIR=~/ws/ont/upheno   # use a local uPheno checkout instead of GitHub
```

Downloads go to `tmp/` (about 1 GB of ontologies for the reasoning context). Classification takes about
3 minutes and peaks at about 10 GB with the default 12 GB heap (`ODK_MEM`).

`data/apo_{pato,oba,go}.sssom.tsv` are the APO→PATO/OBA/GO mappings curated in a Google Sheet.
`make mappings` refreshes them, and they're committed so that mapping changes show up in review.
`.github/workflows/weekly.yaml` runs every Monday and opens a PR with `output/summary.md` as its description.
The repo must allow GitHub Actions to create pull requests.

## Status

- **Built end to end.** The current release (2026-11-01) has 3,361 DPO-ext and 2,076 APO-ext classes.
  - 98% of FlyBase annotations are handled: 41% go into the components and 54% are already DPO classes.
  - 46% of SGD annotations are handled.
  - Every class has a uPheno grouping, and 296 are equivalent to an existing uPheno class.
  - Many groupings are broad (e.g. *cell phenotype*, *decreased resistance of organism to chemical
    entity*), because uPheno lacks intermediate classes and FBbt has few exact bridges. `output/summary.md`
    reports this on every run.
- **Not done yet:**
  - Merging the w3id PR ([#7041](https://github.com/perma-id/w3id.org/pull/7041)).
  - Enabling GitHub Pages for this repo, so that file IRIs resolve.
  - The PHENIO import of the four OWL files.
- **Open:**
  - SGD trait observables (competitive fitness, vegetative growth…), which uPheno has no pattern for.
  - The semantics of SGD chemical conditions (`issues/issue_sgd_chemical_semantics.md`).
