"""The phenotype components uphenotizer releases: DPO-ext (FlyBase) and APO-ext (SGD).

Both share one IRI space, ``https://w3id.org/monarch-initiative/entity/PHENOTYPE_<7 digits>``
(CURIE ``PHENOTYPE:<7 digits>``); each component mints from its own number range, so IDs never collide
and the number tells you the component.
"""

from dataclasses import dataclass

ENTITY_BASE = "https://w3id.org/monarch-initiative/entity/PHENOTYPE_"
CURIE_PREFIX = "PHENOTYPE"
# Release files, served via the w3id fall-through to GitHub Pages (monarch-initiative.github.io).
FILE_BASE = "https://w3id.org/monarch-initiative/uphenotizer/release/"


@dataclass(frozen=True)
class Component:
    name: str          # dpo-ext
    source: str        # FB
    title: str
    first: int         # first number of the component's ID range
    last: int          # last number of the range (inclusive)
    taxon: str         # RO:0002162 'in taxon' on every class (same taxon the KG gives the MOD's genes)
    subset: str        # oboInOwl:inSubset, for search scoping

    iri_base: str = ENTITY_BASE
    prefix: str = CURIE_PREFIX

    def iri(self, number: int) -> str:
        if not self.first <= number <= self.last:
            raise ValueError(f"{self.name}: ID {number} outside range {self.first}-{self.last}")
        return f"{ENTITY_BASE}{number:07d}"

    def curie(self, iri: str) -> str:
        return f"{CURIE_PREFIX}:{iri[len(ENTITY_BASE):]}"

    def file_iri(self, suffix: str) -> str:
        """e.g. file_iri("base.owl") -> .../uphenotizer/release/dpo-ext-base.owl"""
        return f"{FILE_BASE}{self.name}-{suffix}"


COMPONENTS = {
    "FB": Component("dpo-ext", "FB", "DPO-ext: FlyBase phenotypes pre-composed from Alliance annotations",
                    1000000, 1999999, taxon="NCBITaxon:7227", subset="fly_phenotype"),
    # NCBITaxon:559292 (S. cerevisiae S288C): the taxon SGD genes carry in the Alliance files and the KG.
    "SGD": Component("apo-ext", "SGD", "APO-ext: SGD phenotypes pre-composed from Alliance annotations",
                     2000000, 2999999, taxon="NCBITaxon:559292", subset="yeast_phenotype"),
}

