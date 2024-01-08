
ALLIANCE_URL = http://www.alliancegenome.org/downloads/alliance.ttl.gz

build_flybase: flybase_fbbt_phenotypes.dosdp.tsv

.PHONY: .FORCE

alliance_phenotypes.json.gz: .FORCE
	wget $(ALLIANCE_URL) -O 

alliance_phenotypes.json:  alliance_phenotypes.json.gz
	gunzip -c $< | python3 scripts/extract_flybase_fbbt_phenotypes.py > $@

flybase_fbbt_phenotypes.dosdp.tsv:  alliance_phenotypes.json.gz
	python3 scripts/extract_flybase_fbbt_phenotypes.py $< $@
