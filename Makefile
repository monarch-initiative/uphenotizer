
# TODO replace with SGD & FB phneotype file downloads
ALLIANCE_FB_URL = https://fms.alliancegenome.org/download/PHENOTYPE_FB.json.gz
ALLIANCE_SGD_URL = https://fms.alliancegenome.org/download/PHENOTYPE_SGD.json.gz
PATTERNDIR = dosdp_data

#############################
### Core Workflows ##########
#############################

all:
	# Prepare dosdp data
	$(MAKE) flybase_fbbt_phenotypes
	$(MAKE) sgd_phenotypes
	$(MAKE) all_dosdp_to_owl

#############################
### Alliance Data ###########
#############################

PHENOTYPE_FB.json.gz:
	wget $(ALLIANCE_FB_URL) -O

PHENOTYPE_FB.json:  PHENOTYPE_FB.json.gz
	gunzip $<

PHENOTYPE_SGD.json.gz:
	wget $(ALLIANCE_SGD_URL) -O

PHENOTYPE_SGD.json:  PHENOTYPE_SGD.json.gz
	gunzip $<

#############################
### Ontology Dependencies ###
#############################

SOURCES=pato go fbcv fbbt fbdv

data/%.owl:
	robot convert -I http://purl.obolibrary.org/obo/$*-base.owl -o $@

data/merged.owl: $(foreach n,$(SOURCES), data/$(n).owl)
	robot merge $(foreach n,$^, -i $(n)) -o $@

#############################
### DOSDP TSV GENERATION ####
#############################

# Takes as an input the alliance_phenotypes.json file and 
# generates one ore more DOSDP TSV files
flybase_fbbt_phenotypes: PHENOTYPE_FB.json
	mkdir -p $(PATTERNDIR)
	python3 scripts/extract_flybase_fbbt_phenotypes.py

# Takes as an input the alliance_phenotypes.json file and 
# generates one ore more DOSDP TSV files

APO_OBA_URL=https://docs.google.com/spreadsheets/d/e/2PACX-1vSsKbr0TJHfigCvG1RNQgybZrSl3Eh8DRLpnQR-51bFe0Stxt7DdBKBF6E4SQ6NPqJr82UTFZmjindF/pub?gid=0&single=true&output=tsv
data/apo_oba.sssom.tsv:
	wget "$(APO_OBA_URL)" -O $@

APO_GO_URL=https://docs.google.com/spreadsheets/d/e/2PACX-1vSsKbr0TJHfigCvG1RNQgybZrSl3Eh8DRLpnQR-51bFe0Stxt7DdBKBF6E4SQ6NPqJr82UTFZmjindF/pub?gid=575540781&single=true&output=tsv
data/apo_go.sssom.tsv:
	wget "$(APO_GO_URL)" -O $@

APO_PATO_URL=https://docs.google.com/spreadsheets/d/e/2PACX-1vSsKbr0TJHfigCvG1RNQgybZrSl3Eh8DRLpnQR-51bFe0Stxt7DdBKBF6E4SQ6NPqJr82UTFZmjindF/pub?gid=1739417682&single=true&output=tsv
data/apo_pato.sssom.tsv:
	wget "$(APO_PATO_URL)" -O $@

download_mappings: data/apo_oba.sssom.tsv data/apo_go.sssom.tsv data/apo_pato.sssom.tsv

sgd_phenotypes: PHENOTYPE_SGD.json
	mkdir -p $(PATTERNDIR)
	python3 scripts/extract_sgd_phenotypes.py

#############################
### DOSDP OWL GENERATION ####
#############################

%.dosdp.owl: data/merged.owl $(PATTERNDIR)/%.dosdp.tsv
	dosdp-tools generate --obo-prefixes=true \
		--template=patterns/$*.yaml \
		--infile=$(PATTERNDIR)/$*.dosdp.tsv \
		--outfile=$@ \
		--ontology=$<

PATTERN_DATA=fbbt_simple #sgd_simple

all_dosdp_to_owl: $(foreach n,$(PATTERN_DATA), $(PATTERNDIR)/$(n).owl)
