#!/bin/sh
# Runs inside ODK. Merge generated classes with the uPheno reasoning context, drop disjointness
# (as uPheno does), classify with ELK and export direct superclasses + named equivalents.
# "EquivalentClass" must be generated, otherwise ext == UPHENO equivalences are not materialised.
set -e
robot merge $(for f in tmp/ctx/*.owl tmp/gen/*.owl; do printf -- '-i %s ' "$f"; done) \
  remove --axioms disjoint \
  reason --reasoner ELK --equivalent-classes-allowed all --exclude-tautologies structural \
    --axiom-generators "SubClass EquivalentClass" --dump-unsatisfiable tmp/unsatisfiable.txt \
  export --header "ID|LABEL|SubClass Of|Equivalent Class" --entity-format ID \
    --include classes --format tsv --export tmp/classified.tsv
