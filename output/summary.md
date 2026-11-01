# uphenotizer run summary

## Coverage by source

| source | status | units | annotations | share of annotations |
|---|---|---:|---:|---:|
| FB | routed | 7711 | 123914 | 41.0% |
| FB | covered_upstream | 2831 | 164487 | 54.4% |
| FB | skipped | 1 | 7082 | 2.3% |
| FB | unrouted | 1107 | 6629 | 2.2% |
| SGD | routed | 2418 | 182526 | 46.3% |
| SGD | skipped | 296 | 16551 | 4.2% |
| SGD | unrouted | 3069 | 195192 | 49.5% |

**Fallback bindings:** 81589 annotations (6 units) are bound to a generic chemical class because the Alliance export has no ChEBI condition for them. They re-bind to the specific class as soon as the export carries the chemical.

## Pattern tables

| pattern | rows | existing uPheno ID | needs minting | pending |
|---|---:|---:|---:|---:|
| abnormalAbsenceOfBiologicalProcess | 48 | 8 | 40 | 0 |
| abnormalAnatomicalEntity | 2698 | 0 | 2698 | 0 |
| abnormalBiologicalProcess | 70 | 30 | 40 | 0 |
| abnormalCellularComponent | 274 | 5 | 269 | 0 |
| abnormallyArrestedBiologicalProcess | 15 | 7 | 8 | 0 |
| abnormallyDecreasedLevelOfChemicalEntity | 293 | 34 | 259 | 0 |
| abnormallyDecreasedNumberOfAnatomicalEntity | 80 | 0 | 80 | 0 |
| abnormallyDecreasedNumberOfCellularComponent | 33 | 3 | 30 | 0 |
| abnormallyDecreasedRateOfBiologicalProcess | 21 | 5 | 16 | 0 |
| abnormallyDecreasedResistanceOfWholeOrganismToChemicalEntity | 757 | 94 | 663 | 0 |
| abnormallyDelayedBiologicalProcess | 35 | 5 | 30 | 0 |
| abnormallyIncreasedLevelOfChemicalEntity | 372 | 35 | 337 | 0 |
| abnormallyIncreasedNumberOfAnatomicalEntity | 216 | 0 | 216 | 0 |
| abnormallyIncreasedNumberOfCellularComponent | 34 | 5 | 29 | 0 |
| abnormallyIncreasedRateOfBiologicalProcess | 19 | 5 | 14 | 0 |
| abnormallyIncreasedResistanceOfWholeOrganismToChemicalEntity | 455 | 55 | 400 | 0 |
| abnormallyPrematureBiologicalProcess | 11 | 1 | 10 | 0 |

## Top 15 unrouted (by annotation count)

| source | terms | annotations | example | reason |
|---|---|---:|---|---|
| SGD | `APO:0000003|APO:0000110` | 27507 | decreased competitive fitness | no rule for qualifier/observable |
| SGD | `APO:0000004|APO:0000110` | 7775 | increased competitive fitness | no rule for qualifier/observable |
| SGD | `APO:0000003|APO:0000106` | 7018 | decreased vegetative growth | no rule for qualifier/observable |
| SGD | `APO:0000004|APO:0000147` | 6964 | increased heat sensitivity | no rule for qualifier/observable |
| SGD | `APO:0000245|APO:0000106` | 6279 | decreased rate vegetative growth | no rule for qualifier/observable |
| SGD | `APO:0000152` | 6061 | haploinsufficient | expected qualifier + observable, got 1 term(s) |
| SGD | `APO:0000002|APO:0000059` | 5739 | abnormal vacuolar morphology | no rule for qualifier/observable |
| SGD | `APO:0000002|APO:0000209` | 4872 | abnormal protein/peptide distribution | no rule for qualifier/observable |
| SGD | `APO:0000112` | 4522 | inviable | expected qualifier + observable, got 1 term(s) |
| SGD | `APO:0000005|APO:0000309` | 3973 | absent respiratory growth | no rule for qualifier/observable |
| SGD | `APO:0000003|APO:0000083` | 3864 | decreased oxidative stress resistance | no rule for qualifier/observable |
| SGD | `APO:0000002|APO:0000095` | 3589 | abnormal chemical compound accumulation | no rule for qualifier/observable |
| SGD | `APO:0000003|APO:0000215` | 3358 | decreased toxin resistance | rule needs a chemical condition and has no fallback |
| SGD | `APO:0000003|APO:0000316` | 2950 | decreased chronological lifespan | no rule for qualifier/observable |
| SGD | `APO:0000004|APO:0000149` | 2888 | increased protein/peptide accumulation | no rule for qualifier/observable |

## Component IDs

| component | classes | minted this run | not used by current annotations |
|---|---:|---:|---:|
| dpo-ext | 3361 | 0 | 0 |
| apo-ext | 2076 | 0 | 0 |

## Components and uPheno bridges

| component | classes | equivalent to UPHENO | grouped under UPHENO | no UPHENO grouping | with in-component parent |
|---|---:|---:|---:|---:|---:|
| dpo-ext | 3361 | 23 | 3338 | 0 | 3294 |
| apo-ext | 2076 | 273 | 1803 | 0 | 1981 |

Most frequent uPheno groupings, dpo-ext:

- 1369 × `UPHENO:0086172` cell phenotype
- 1055 × `UPHENO:0003025` subdivision of organism along main body axis phenotype
- 673 × `UPHENO:0002548` ectoderm-derived structure phenotype
- 596 × `UPHENO:0002976` organ system subdivision phenotype
- 583 × `UPHENO:0004064` integumental system phenotype
- 550 × `UPHENO:0002844` head phenotype
- 435 × `UPHENO:0004523` nervous system phenotype
- 367 × `UPHENO:0002902` multi-tissue structure phenotype
- 353 × `UPHENO:0002963` anatomical system phenotype
- 344 × `UPHENO:0075949` late embryo phenotype

Most frequent uPheno groupings, apo-ext:

- 656 × `UPHENO:0076332` decreased resistance of organism to chemical entity
- 399 × `UPHENO:0076993` increased resistance of organism to chemical entity
- 228 × `UPHENO:0048707` increased level of chemical entity
- 165 × `UPHENO:0066739` decreased level of chemical entity
- 102 × `UPHENO:0046348` phosphate level phenotype
- 84 × `UPHENO:0046383` nitrogen molecular entity level phenotype
- 42 × `UPHENO:0066793` decreased level of lipid
- 36 × `UPHENO:0046286` amino acid level phenotype
- 29 × `UPHENO:0048756` increased level of phospholipid
- 27 × `UPHENO:0048763` increased level of lipid

### Duplicate labels within a component

None.
