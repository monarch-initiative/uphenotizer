import json
from typing import List, Optional

from oaklib import get_adapter
from pydantic import BaseModel, Field
import pandas as pd

class SGDPhenotype(BaseModel):
    phenotype_id: str = Field(...)
    phenotype_label: Optional[str] = Field(None)
    direction_id: Optional[str] = Field(None)
    direction_label: Optional[str] = Field(None)
    chemical_ids: Optional[List[str]] = Field(default_factory=list)
    pato_id: Optional[str] = Field(None)
    pato_label: Optional[str] = Field(None)

def get_mapped_pato_id(direction_id, df_sgd_pato_mapping, phenotype_id = None):
    try:
        pato_id = df_sgd_pato_mapping[df_sgd_pato_mapping['subject_id'] == direction_id]['object_id'].iloc[0]
        pato_label = \
            df_sgd_pato_mapping[df_sgd_pato_mapping['subject_id'] == direction_id]['object_label'].iloc[0]
    except IndexError:
        print(f"Could not find PATO mapping for {direction_id}")
        pato_from_phenotype_id, pato_from_phenotype_label = get_mapped_pato_id(phenotype_id, df_sgd_pato_mapping)
        print(f"Could find PATO for phenotype_id {phenotype_id}: {pato_from_phenotype_id} {pato_from_phenotype_label}")
        pato_id = None
        pato_label = None
    return pato_id, pato_label


def export_sgd_phenotypes():
    adapter = get_adapter("sqlite:obo:apo")

    # Path to the file
    sgd_raw_data_path = 'data/PHENOTYPE_SGD.json'
    sgd_dosdp_path = 'data/sgd_dosdp.tsv'
    sgd_pato_mapping_path = 'data/apo_pato.sssom.tsv'

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
        phenotype_id = None
        phenotype_label = None
        direction_id = None
        direction_label = None
        chemical_ids: List[str] = []


        if "phenotypeTermIdentifiers" in item:
            for pheno in item["phenotypeTermIdentifiers"]:

                if pheno['termOrder'] == 1:
                    if direction_id:
                        raise ValueError(
                            f"Phenotype description has unexpected term item: {pheno['termOrder']} ({pheno})")
                    direction_id = pheno['termId']
                    if not direction_id:
                        raise ValueError(f"Phenotype description has unexpected term order 1 item: {pheno}")
                    direction_label = adapter.label(direction_id)
                elif pheno['termOrder'] == 2:
                    if phenotype_id:
                        raise ValueError(
                            f"Phenotype description has unexpected term item: {pheno['termOrder']} ({pheno})")
                    phenotype_id = pheno['termId']
                    phenotype_label = adapter.label(phenotype_id)
                    if not phenotype_id:
                        raise ValueError(f"Phenotype description has unexpected term order 2 item: {pheno}")

                else:
                    raise ValueError(f"Phenotype description has unexpected order: {pheno['termOrder']} ({pheno})")

                if "conditionRelations" in item:
                    if "conditions" in item["conditionRelations"]:
                        for condition in item["conditionRelations"]["conditions"]:
                            if "chemicalOntologyId" in condition:
                                chemical_ids.append(condition["chemicalOntologyId"])
                            elif "chemicalOntologyId" not in condition and "conditionStatement" in condition:
                                print(f"Skipping {phenotype_id} {direction_id if direction_id else ''} with no chemical ID for: {condition['conditionStatement']}")
                                continue

        if direction_id is not None:
            pato_id, pato_label = get_mapped_pato_id(direction_id, df_sgd_pato_mapping, phenotype_id)
        else:
            pato_id = None
            pato_label = None
        # phenotype_record = SGDPhenotype(
        #              pato_id=pato_id,
        #              pato_label=pato_label,
        #              phenotype_id=phenotype_id,
        #              phenotype_name=phenotype_label,
        #              direction_id=direction_id,
        #              direction_name=direction_label)
        #              # chemical_ids=chemical_ids)
        # data.append(phenotype_record.dict())

        data.append({
            "pato_id": pato_id,
            "pato_id_name": pato_label,
            "phenotype_id": phenotype_id,
            "phenotype_label": phenotype_label,
            "direction_id": direction_id,
            "direction_label": direction_label,
            "chemical_ids": "|".join(chemical_ids) if chemical_ids else None
        })

    df = pd.DataFrame.from_records(data, columns=[
        "pato_id",
        "pato_id_name",
        "phenotype_id",
        "phenotype_label",
        "direction_id",
        "direction_label",
        "chemical_ids"
    ])

    print(df.head())

    df.to_csv('sgd_phenotype.csv', index=False)


export_sgd_phenotypes()