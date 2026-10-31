#!/bin/sh
# Runs inside ODK. Filler labels from the reasoning context, then dosdp-tools generate per
# component and pattern (logical definitions + labels/definitions from the pattern templates).
set -e
CTX=$(for f in tmp/ctx/*.owl; do printf -- '-i %s ' "$f"; done)

robot merge $CTX \
  filter --term-file tmp/dosdp/fillers.txt --select "self annotations" --axioms annotation \
    --signature true \
  -o tmp/filler-labels.owl

for dir in tmp/dosdp/*/; do
  comp=$(basename "$dir")
  [ "$comp" = patterns ] && continue
  rm -rf "tmp/gen/$comp" && mkdir -p "tmp/gen/$comp"
  for tsv in "$dir"*.tsv; do
    [ -e "$tsv" ] || continue
    p=$(basename "$tsv" .tsv)
    dosdp-tools generate --obo-prefixes=true --ontology=tmp/filler-labels.owl \
      --template="tmp/dosdp/patterns/$p.yaml" --infile="$tsv" --outfile="tmp/gen/$comp/$p.ofn"
  done
  robot merge $(for f in tmp/gen/$comp/*.ofn; do printf -- '-i %s ' "$f"; done) \
    -o "tmp/gen/$comp.owl"
done
