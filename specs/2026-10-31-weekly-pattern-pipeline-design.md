# uphenotizer: DPO-ext and APO-ext phenotype components with uPheno bridges — design

Issue: `issues/issue_weekly_pattern_pipeline.md` (draft, not yet posted). Related: #3 (SGD
chemical phenotypes; the `chemical` filler implements it), #1 (APO mappings).

Revision 2 (2026-10-31). It supersedes revision 1, "emit DOSDP tables, uPheno mints UPHENO IDs". The
decision log at the end explains why.

## Intent

FlyBase and SGD annotate phenotypes in post-composed form, which reaches the Alliance as
`PHENOTYPE_FB.json` / `PHENOTYPE_SGD.json`: FlyBase uses FBbt, GO and FBcv terms with
qualifiers, and SGD uses an APO qualifier plus an APO observable, often with a ChEBI condition.
Monarch needs a pre-composed class for each combination, placed in the uPheno hierarchy, so that
the gene→phenotype associations integrate with every other species.

uphenotizer turns the annotations into **two phenotype ontology components** and **bridges them to
uPheno**:

- **DPO-ext** is the FlyBase phenotypes DPO doesn't pre-compose (anatomy- and GO-based). It's formally a
  legal extension of DPO, i.e. a DPO component.
- **APO-ext** is the SGD phenotypes. It plays the role ZP plays for ZFIN: the pre-composed phenotype
  ontology for a MOD's EQ-style annotations. (APO itself is really a trait ontology; ideally it would have been
  called ATO and this module APO.)

The components are imported into **PHENIO** (`~/ws/ont/phenio`), **not into uPheno**. uPheno can later
pull new classes from here voluntarily, through a separate process on its side, and mint UPHENO IDs for them.

## Goals

- A weekly GitHub Actions run that downloads the current Alliance dumps, regenerates both components and
  their bridges, and opens a PR when anything changed.
- Every class is an instance of a **uPheno DOSDP pattern**, with species-specific or species-neutral fillers.
  The logical definition is used **internally** for classification only, and the released components don't
  contain it (Nico's decision).
- **The best possible uPheno grouping for every class**: the most specific existing UPHENO classes
  that subsume it, found by reasoning over the logical definitions together with uPheno and the
  FBbt→UBERON/CL bridges. These groupings are materialised as a bridge file.
- Stable IDs: append-only ID maps keyed ZP-style (filler CURIEs ordered by variable name, then
  the pattern name).
- A ranked report of everything not translated yet, so curation goes where the volume is.

## Non-goals

- **No changes to uPheno's design.** uPheno's `legal_fillers` stay species-neutral, and nothing here
  requires a uPheno code change.
- No import into uPheno. PHENIO is the consumer.
- No re-emitting of classes DPO already has. FlyBase annotations whose head term is an FBcv
  `phenotypic_class` term are DPO classes (`covered_upstream`).

## Anti-goals

- **Lossy translation.** A class must mean what the annotation means. Context that isn't phenotypic
  (dominance, clone type, sex, maternal effect, stage of observation) may be dropped. Qualifiers that
  change the phenotype (spatial, structural, intensity) may not. A bare FBbt annotation means
  *phenotype manifest in X* (`abnormalAnatomicalEntity`), **not** "abnormal X morphology".
- A grouping that isn't entailed. Bridge axioms come from reasoning (or, later, from explicitly curated
  and documented mappings), never from lexical guesses.
- ID churn. An ID once minted is never reused for a different key and never deleted.

## Decisions (Nico's)

- There are two components here, DPO-ext and APO-ext, and this repo mints their IDs.
- The namespaces use w3id IRIs under `https://w3id.org/monarch-initiative/`.
- **The bridges to uPheno are built here, not in uPheno.**
- PHENIO imports the components and bridges. uPheno doesn't import them, and may pull classes voluntarily later.
- Keys use ZP's scheme (filler CURIEs ordered by variable name, then the pattern name).
- uPheno patterns are the templates. The target is current uPheno (`obophenotype/upheno`), and upheno-dev is dead.
- **No logical definitions in the released components.** They're generated and reasoned over here, then
  stripped. Released components carry only the materialised hierarchy and bridges. As a result, PHENIO never
  infers `ext ≡ UPHENO` equivalence cliques.

## Design

### Namespaces and IDs

**Nico's decision (revised):** one shared class namespace,
`https://w3id.org/monarch-initiative/entity/PHENOTYPE_<7 digits>`, registered in
[perma-id/w3id.org#7041](https://github.com/perma-id/w3id.org/pull/7041) (`entity/<id>` → `monarchinitiative.org/<id>`;
any other path → `monarch-initiative.github.io/<path>`).

| | DPO-ext | APO-ext |
|---|---|---|
| CURIE | `PHENOTYPE:` (my call: the OBO-style contraction of the IRI) | same |
| ID range (my call) | `1000000`–`1999999` | `2000000`–`2999999` |
| Ontology (file) IRIs | `https://w3id.org/monarch-initiative/uphenotizer/release/dpo-ext-{base,bridge}.owl` | `…/release/apo-ext-{base,bridge}.owl` |

File IRIs resolve through the fallthrough rule only once GitHub Pages serves this repo (branch `main`, root),
giving `monarch-initiative.github.io/uphenotizer/release/…`. Version IRIs (`…/uphenotizer/releases/<date>/…`)
don't resolve yet, because there are no dated copies.

ID maps live in `idmaps/dpo-ext.tsv` and `idmaps/apo-ext.tsv` (`id`, `key`), and are append-only. A key
that disappears from the source data keeps its ID, and its class is marked `owl:deprecated true` (with
`IAO:0100001 term replaced by` only when an unambiguous successor exists). A key that reappears gets its old ID back, un-deprecated.

### Bindings (Nico's decision: keep the SGD fallback, but bindings must follow the data)

`output/source_map.tsv` binds each annotation shape `(source, terms, chemical)` to a `class_id`, and is
recomputed on every run. SGD chemical phenotypes with no ChEBI condition bind to the fallback class
(`CHEBI:24431` / `CHEBI:33521` filler). The reason is marked `fallback …`, and the count is reported in the summary
(81,589 annotations on 2026-10-31). The cause is upstream: SGD's own `phenotype_data.tab` names a chemical for
every "resistance to chemicals" annotation, but the Alliance export keeps only ChEBI-mapped ones. That held for
both the Jan-2024 and the current dump (51% with ChEBI in each). When a later export carries the chemical, the
record becomes a different unit and binds to the specific class. The fallback class is deprecated once unused,
and its ID is kept. This is covered by `tests/test_binding.py`.

### Pipeline

1. **Route** (as built in revision 1). Alliance records are aggregated into source units and mapped to
   `(pattern, fillers)` by `config/flybase.yaml` and `config/sgd_rules.tsv`. Statuses are `routed`,
   `pending`, `covered_upstream`, `skipped` and `unrouted`.
2. **Mint.** Each routed key gets an ID from the component's ID map.
3. **Generate.** `dosdp-tools generate` turns each pattern table into OWL, using uPheno's pattern YAMLs and the
   filler ontologies for labels. A class gets its label and definition from the pattern's text templates, plus
   an EQ logical definition, `oboInOwl:hasExactSynonym` for the MOD's own phenotype statement, and a
   provenance annotation pointing to the source tuple.
4. **Classify.** The generated classes are merged with uPheno (`upheno-base.owl`, the artefact PHENIO
   uses), the filler ontologies (FBbt, GO, CHEBI slim, PATO, UBERON, CL, RO) and the UBERON/CL→FBbt
   bridges, and ELK runs over the result. For every component class this produces:
   - its direct inferred superclasses *within the component*, written into the component itself;
   - its **most specific inferred UPHENO superclasses**, i.e. direct superclasses after
     collapsing paths through other component classes. These are written as
     `SubClassOf(ext class, UPHENO class)` in the bridge, the same shape as uPheno's own `upheno-bridge.owl`;
   - inferred equivalences to UPHENO classes. These are expected for APO-ext classes with species-neutral
     fillers (CHEBI, GO), many of which already exist in uPheno. They're recorded as `SubClassOf` in the
     bridge (as uPheno does for cross-species exact matches) and as `semapv:crossSpeciesExactMatch` in the SSSOM.
5. **Release.** The artefacts below are written, and the PR summary reports counts, unrouted units and grouping quality.

### Artefacts (committed, deterministic)

| File | Content |
|---|---|
| `release/dpo-ext-base.owl`, `release/apo-ext-base.owl` | The components: classes, labels, text definitions, synonyms, provenance and the materialised in-component hierarchy. No logical definitions |
| `release/dpo-ext-bridge.owl`, `release/apo-ext-bridge.owl` | `SubClassOf(ext class, UPHENO class)`, the best uPheno grouping |
| `release/dpo-ext-upheno.sssom.tsv`, `release/apo-ext-upheno.sssom.tsv` | The same links as SSSOM: `crossSpeciesExactMatch` for inferred equivalence, `skos:broadMatch` for grouping |
| `idmaps/*.tsv` | Append-only ID maps |
| `output/source_map.tsv`, `output/unrouted.tsv`, `output/summary.md` | Provenance and coverage reports (as in revision 1) |
| `output/patterns/*.tsv` | Species-agnostic DOSDP tables (filler columns + `defined_class` = existing UPHENO ID or empty). This is what uPheno would pull. The per-component tables fed to dosdp-tools are regenerated in `tmp/dosdp/` |

### Grouping quality (reported, not hidden)

- See the spike results under Tooling for measured numbers.
- For FlyBase, `abnormal FBbt:X` is classified through the nearest *exactly bridged* FBbt ancestor
  (`FBbt:X ≡ UBERON/CL:Y and part_of some NCBITaxon:7227`, via is_a and part_of) under the most
  specific existing `UPHENO` class with a UBERON or CL filler. On the first run, 346 of the 2,999 FBbt-based
  classes have a direct exact bridge, and the other 2,653 depend on the FBbt hierarchy to reach one.
- The summary reports how many classes ended up only under a generic root (e.g. *abnormal anatomical entity*).
  Those are the targets for bridge and curation work.
- SGD trait observables (competitive fitness, vegetative growth…) aren't routed yet, so they produce no
  classes. Their grouping (OBA-trait patterns or curated groupings) is a separate design step.

### Tooling

Routing, minting and reporting are in Python (`src/uphenotizer/`, uv). Generation and classification
use ROBOT, dosdp-tools and ELK in the ODK container (`obolibrary/odkfull`), driven by the Makefile.
The weekly GitHub Action runs the ODK steps in that container.

**Spike results (2026-10-31, `obolibrary/odkfull:v1.7`).**

- Reasoning context: uPheno full release (2026-10-19), plus fbbt-base, uberon-base, cl-base, go-base,
  chebi_lite, `uberon-bridge-to-fbbt` and `cl-bridge-to-fbbt`, with disjointness axioms removed. The uPheno
  release alone lacks FBbt, most of UBERON and GO, and 1,107 of our 1,877 ChEBI fillers.
- ELK over 5,375 generated classes took **2 min 53 s at 10.3 GB peak with a 12 GB heap**, with no
  unsatisfiable classes. That fits a standard GitHub runner (16 GB). Module extraction isn't needed.
- ROBOT must use `--axiom-generators "SubClass EquivalentClass"`. Otherwise inferred equivalences between
  named classes (`ext ≡ UPHENO`) aren't materialised.
- **Every class gets at least one UPHENO grouping.** 288 are equivalent to an existing UPHENO class (273
  APO-ext, 15 DPO-ext; this matches the ID-map hits). Example: CHEBI:29699 → *decreased resistance of
  organism to tunicamycin*. Fly eye → *eye phenotype*; increased number of chaeta → *increased number of
  sense organ*.
- **Grouping specificity is limited by what exists in uPheno, not by the method.**
  - 1,705 DPO-ext classes land only under broad groupings: mostly FBbt cell types reaching uPheno only
    via *cell phenotype*, and cellular components.
  - 1,318 APO-ext classes do too: chemicals without a uPheno class reach only *decreased resistance of
    organism to chemical entity* or *increased level of chemical entity*, because uPheno's chemical layer is flat.
  - The levers for both are upstream: more FBbt→UBERON/CL bridges, and intermediate uPheno classes. The
    components' own hierarchy provides finer groupings in the meantime. For example, an APO-ext class for a
    ChEBI parent turns up as a *superclass* of an existing UPHENO class.

## Open (for Nico)

- **uPheno's organism bearer.** uPheno's whole-organism patterns use `UBERON:0000468` (*multicellular*
  organism) while labelling it "cellular organism". APO-ext inherits that through the patterns. It's an upstream fix.
- **SGD accumulation semantics and the ChEBI fallback** (`issues/issue_sgd_chemical_semantics.md`).

## Decision log

1. **Revision 1 (superseded): DOSDP tables only, uPheno mints UPHENO IDs.** It was implemented and
   verified. It fails for FlyBase anatomy: uPheno 2's `legal_fillers` admit only species-neutral fillers,
   and none of its generated tables contain species-anatomy fillers. The ZFA and WBbt keys in
   `upheno_id_map.txt` are uPheno 1 leftovers. 2,653 fly-specific classes (62,681 annotations) have no
   exact UBERON/CL bridge, so they can't become legal without loss.
2. **Rejected: let uPheno accept FBbt fillers** (globally, or per-source for external tables). It works
   technically, but it changes uPheno's design: species-independent classes only.
3. **Rejected: one `MONARCH_PHENOTYPE` module classified by uPheno.** It mixes two MODs in one namespace, and
   uPheno would still have to import it.
4. **Chosen: DPO-ext + APO-ext as components here, bridges here, consumed by PHENIO.** This matches how
   species phenotype ontologies already work (ZP for ZFIN, DPO for FlyBase), keeps uPheno untouched,
   and leaves uPheno free to adopt classes later.
