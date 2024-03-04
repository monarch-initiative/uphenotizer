
ALLIANCE_URL = http://www.alliancegenome.org/downloads/alliance.ttl.gz
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

alliance_phenotypes.json.gz: .FORCE
	wget $(ALLIANCE_URL) -O 

alliance_phenotypes.json:  alliance_phenotypes.json.gz
	gunzip -c $< | python3 scripts/extract_flybase_fbbt_phenotypes.py > $@

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
flybase_fbbt_phenotypes: alliance_phenotypes.json.gz
	mkdir -p $(PATTERNDIR)
	python3 scripts/extract_flybase_fbbt_phenotypes.py $< $(PATTERNDIR)

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
