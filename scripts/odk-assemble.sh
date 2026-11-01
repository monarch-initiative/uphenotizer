#!/bin/sh
# Runs inside ODK. Assemble the released component (no logical definitions) and its uPheno bridge.
# Usage: odk-assemble.sh <component> <entity_base> <file_base> <title> <version>
#   entity_base: class IRI prefix, e.g. https://w3id.org/monarch-initiative/entity/PHENOTYPE_
#   file_base:   release file IRI prefix, e.g. https://w3id.org/monarch-initiative/uphenotizer/release/
set -e
comp=$1; entity=$2; files=$3; title=$4; version=$5
tp=$(echo "$comp" | tr -d '-')
versions=$(echo "$files" | sed 's#/release/$#/releases/#')
mkdir -p release

robot merge -i "tmp/gen/$comp.owl" -i config/declarations.ofn \
  remove --axioms "equivalent subclass" \
  template --merge-before --template "tmp/templates/$comp-base.tsv" --prefix "$tp: $entity" \
    --prefix "uphenotizer: https://w3id.org/monarch-initiative/uphenotizer#" \
  remove --base-iri "$entity" --axioms external --preserve-structure false --trim false \
  merge -i config/declarations.ofn \
  annotate --ontology-iri "$files$comp-base.owl" --version-iri "$versions$version/$comp-base.owl" \
    --annotation http://purl.org/dc/terms/title "$title" \
    --annotation owl:versionInfo "$version" \
  convert -o "release/$comp-base.owl"

robot template --template "tmp/templates/$comp-bridge.tsv" --prefix "$tp: $entity" \
    --prefix "UPHENO: http://purl.obolibrary.org/obo/UPHENO_" \
  annotate --ontology-iri "$files$comp-bridge.owl" \
    --version-iri "$versions$version/$comp-bridge.owl" \
    --annotation http://purl.org/dc/terms/title "$title: uPheno bridge" \
    --annotation owl:versionInfo "$version" \
  convert -o "release/$comp-bridge.owl"
