
# TODO replace with SGD & FB phneotype file downloads
ALLIANCE_FB_URL = https://fms.alliancegenome.org/download/PHENOTYPE_FB.json.gz
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
sgd_phenotypes: alliance_phenotypes.json.gz
	mkdir -p $(PATTERNDIR)
	python3 scripts/extract_sgd_phenotypes.py $< $(PATTERNDIR)

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
