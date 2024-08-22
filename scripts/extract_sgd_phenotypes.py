import json
from oaklib import get_adapter
from pydantic import BaseModel
import pandas as pd

class SGDPhenotype(BaseModel):
    pato_id: str
    pato_name: str
    original_id: str
    original_label: str
    affected_entity_1_super: str
    affected_entity_1_super_name: str
    chemical_id: str
    chemical_label: str

def get_mapped_pato_id(phenotype_term_id_order1, df_sgd_pato_mapping):
    pato_id = df_sgd_pato_mapping[df_sgd_pato_mapping['subject_id'] == phenotype_term_id_order1]['object_id'].iloc[0]
    pato_label = \
        df_sgd_pato_mapping[df_sgd_pato_mapping['subject_id'] == phenotype_term_id_order1]['object_label'].iloc[0]
    return pato_id, pato_label


def export_sgd_phenotypes():
    adapter = get_adapter("sqlite:obo:apo")

    # Path to the file
    sgd_raw_data_path = '../data/PHENOTYPE_SGD.json'
    sgd_dosdp_path = '../data/sgd_dosdp.tsv'
    sgd_pato_mapping_path = '../data/apo_pato.sssom.tsv'

    df_sgd_dosdp = pd.read_csv(sgd_dosdp_path, sep='\t')
    df_sgd_pato_mapping = pd.read_csv(sgd_pato_mapping_path, sep='\t')

    # Read and parse the JSON file
    try:
        with open(sgd_raw_data_path, 'r') as file:
            json_data = json.load(file)
    except FileNotFoundError:
        print(f"File not found: {sgd_raw_data_path}")
    except json.JSONDecodeError:
        print("Error decoding JSON from the file")


    data = []

    for item in json_data["data"]:
        phenotype_term_id_order1 = None
        phenotype_term_id_order2 = None
        phenotype_term_id_order1_label = None
        phenotype_term_id_order2_label = None
        chemical_id = None
        chemical_label = None

        if "phenotypeTermIdentifiers" in item:
            for pheno_id in item["phenotypeTermIdentifiers"]:

                if pheno_id['termOrder'] == 1:
                    if phenotype_term_id_order1:
                        raise ValueError(
                            f"Phenotype description has unexpected term item: {pheno_id['termOrder']} ({pheno_id})")
                    phenotype_term_id_order1 = pheno_id['termId']
                    if not phenotype_term_id_order1:
                        raise ValueError(f"Phenotype description has unexpected term order 1 item: {pheno_id}")
                    phenotype_term_id_order1_label = adapter.label(phenotype_term_id_order1)
                elif pheno_id['termOrder'] == 2:
                    if phenotype_term_id_order2:
                        raise ValueError(
                            f"Phenotype description has unexpected term item: {pheno_id['termOrder']} ({pheno_id})")
                    phenotype_term_id_order2 = pheno_id['termId']
                    if not phenotype_term_id_order2:
                        raise ValueError(f"Phenotype description has unexpected term order 2 item: {pheno_id}")
                    phenotype_term_id_order2_label = adapter.label(phenotype_term_id_order2)
                else:
                    raise ValueError(f"Phenotype description has unexpected order: {pheno_id['termOrder']} ({pheno_id})")

                if "conditionRelations" in item:
                    if "conditions" in item["conditionRelations"]:
                        for condition in item["conditionRelations"]["conditions"]:
                            if "chemical" in condition:
                                if chemical_id is not None:
                                    raise ValueError(f"Phenotype description has multiple chemical item: {condition}")
                                chemical_id = condition["chemical"]["termId"]
                                chemical_label = adapter.label(chemical_id)


        pato_id, pato_label = get_mapped_pato_id(phenotype_term_id_order1, df_sgd_pato_mapping)
        phenotype_record = SGDPhenotype(pato_id=pato_id,
                     pato_name=pato_label,
                     phenotype_term_id_order1=phenotype_term_id_order1,
                     phenotype_term_id_order1_label=phenotype_term_id_order1_label,
                     affected_entity_1_super=phenotype_term_id_order2,
                     affected_entity_1_super_name=phenotype_term_id_order2_label,
                     chemical_id=chemical_id,
                     chemical_label=chemical_label)

        data.append(phenotype_record.dict())

    df = pd.DataFrame.from_records(data, columns=["pato_id",
                                                  "pato_id_name",
                                                  "original_id",
                                                  "original_label",
                                                  "affected_entity_1_super",
                                                  "affected_entity_1_super_name",
                                                  "chemical_id",
                                                  "chemical_label"])

    print(df.head())

    df.to_csv('sgd_phenotype.csv', index=False)


export_sgd_phenotypes()