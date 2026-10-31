# uphenotizer: Alliance FlyBase/SGD phenotype annotations -> DPO-ext / APO-ext components + uPheno bridges.
# `make all` is what the weekly GitHub Action runs. Python steps run via uv; ROBOT/dosdp-tools steps run
# in the ODK container (set ODK= to run them natively, e.g. inside an ODK image).

TMP          := tmp
CTX          := $(TMP)/ctx
ALLIANCE     := https://fms.alliancegenome.org/download
OBO          := http://purl.obolibrary.org/obo
SHEET        := https://docs.google.com/spreadsheets/d/e/2PACX-1vSsKbr0TJHfigCvG1RNQgybZrSl3Eh8DRLpnQR-51bFe0Stxt7DdBKBF6E4SQ6NPqJr82UTFZmjindF/pub
# Class IRIs (both components, disjoint number ranges) and release file IRIs; see components.py.
ENTITY_BASE  := https://w3id.org/monarch-initiative/entity/PHENOTYPE_
FILE_BASE    := https://w3id.org/monarch-initiative/uphenotizer/release/
VERSION      := $(shell date +%Y-%m-%d)
# Set to a local uPheno checkout to avoid fetching patterns and the ID map from GitHub.
UPHENO_DIR   ?=
CURL         := curl -fsSL --retry 3 -o

ODK_IMAGE    ?= obolibrary/odkfull:v1.7
ODK_MEM      ?= 12G
ODK          ?= docker run --rm -i -v $(CURDIR):/work -w /work \
                  -e ROBOT_JAVA_ARGS=-Xmx$(ODK_MEM) -e JAVA_OPTS=-Xmx$(ODK_MEM) $(ODK_IMAGE)

.PHONY: all install test lint download mappings route components generate classify release assemble clean

all: download mappings route components

install:
	uv sync

test:
	uv run pytest -q

lint:
	uv run ruff check src tests

$(TMP) $(CTX):
	mkdir -p $@

#############################
### Inputs ##################
#############################

CTX_FILES := $(CTX)/upheno.owl $(CTX)/fbbt-base.owl $(CTX)/uberon-base.owl $(CTX)/cl-base.owl \
             $(CTX)/go-base.owl $(CTX)/chebi_lite.owl $(CTX)/uberon-bridge-to-fbbt.owl \
             $(CTX)/cl-bridge-to-fbbt.owl

download: $(TMP)/PHENOTYPE_FB.json.gz $(TMP)/PHENOTYPE_SGD.json.gz $(TMP)/fbcv.obo $(TMP)/go-basic.obo \
          $(CTX_FILES)

$(TMP)/PHENOTYPE_%.json.gz: | $(TMP)
	$(CURL) $@ $(ALLIANCE)/PHENOTYPE_$*.json.gz

$(TMP)/fbcv.obo: | $(TMP)
	$(CURL) $@ $(OBO)/fbcv.obo

$(TMP)/go-basic.obo: | $(TMP)
	$(CURL) $@ $(OBO)/go/go-basic.obo

# Reasoning context: uPheno full release + what it lacks (FBbt, full UBERON/CL/GO, ChEBI, FBbt bridges).
$(CTX)/upheno.owl: | $(CTX)
	$(CURL) $@ $(OBO)/upheno.owl

$(CTX)/%-base.owl: | $(CTX)
	$(CURL) $@ $(OBO)/$*/$*-base.owl

$(CTX)/chebi_lite.owl: | $(CTX)
	$(CURL) $@.gz $(OBO)/chebi/chebi_lite.owl.gz && gunzip -f $@.gz

$(CTX)/uberon-bridge-to-fbbt.owl $(CTX)/cl-bridge-to-fbbt.owl: | $(CTX)
	$(CURL) $@ $(OBO)/uberon/bridge/$(notdir $@)

# APO -> PATO/OBA/GO mappings, curated in a Google Sheet. Committed so changes show up in PRs.
mappings:
	$(CURL) data/apo_oba.sssom.tsv "$(SHEET)?gid=0&single=true&output=tsv"
	$(CURL) data/apo_go.sssom.tsv "$(SHEET)?gid=575540781&single=true&output=tsv"
	$(CURL) data/apo_pato.sssom.tsv "$(SHEET)?gid=1739417682&single=true&output=tsv"

#############################
### Pipeline ################
#############################

# Route annotations, mint component IDs, write DOSDP tables (tmp/dosdp) and reports (output/).
route:
	uv run uphenotizer run \
		--fb $(TMP)/PHENOTYPE_FB.json.gz \
		--sgd $(TMP)/PHENOTYPE_SGD.json.gz \
		--fbcv $(TMP)/fbcv.obo \
		--go $(TMP)/go-basic.obo \
		$(if $(UPHENO_DIR),--upheno-dir $(UPHENO_DIR),) \
		--out output --idmaps idmaps --dosdp-out $(TMP)/dosdp

components: generate classify release assemble

generate:
	$(ODK) sh scripts/odk-generate.sh

classify:
	$(ODK) sh scripts/odk-classify.sh

release:
	uv run uphenotizer release --classified $(TMP)/classified.tsv --idmaps idmaps \
		--source-map output/source_map.tsv --templates $(TMP)/templates --mappings-out release \
		--summary output/summary.md

assemble:
	$(ODK) sh scripts/odk-assemble.sh dpo-ext $(ENTITY_BASE) $(FILE_BASE) \
		"DPO-ext: FlyBase phenotypes pre-composed from Alliance annotations" $(VERSION)
	$(ODK) sh scripts/odk-assemble.sh apo-ext $(ENTITY_BASE) $(FILE_BASE) \
		"APO-ext: SGD phenotypes pre-composed from Alliance annotations" $(VERSION)

clean:
	rm -rf $(TMP)
