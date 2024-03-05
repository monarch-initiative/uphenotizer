import json
from typing import List

import pandas as pd
from pandas import DataFrame
from pydantic import BaseModel

UPHENO_PREFIX = 'UPHENO:'
MAPPING_FILE = 'dosdp_data/fb_upheno.dosdp.tsv'


class Mapping(BaseModel):
    anatomy_id: str
    upheno_id: str


def export_flybase_fbbt_phenotypes():
    """Export FlyBase FBbt phenotypes to single column tsv with `anatomical_term` header."""
    fb_g2p = json.load(open('PHENOTYPE_FB.json'))['data']

    phenotypes_without_terms = []

    fb_anatomical_phenotypes = []
    for record in fb_g2p:
        if len(record["phenotypeTermIdentifiers"]) == 0:
            phenotypes_without_terms.append(record["phenotypeStatement"])
            continue
        first_phenotype = record["phenotypeTermIdentifiers"][0]["termId"]
        if first_phenotype.startswith('FBbt'):
            fb_anatomical_phenotypes.append(first_phenotype)

    fb_anatomical_phenotypes.sort()
    all_unique_fb_anatomical_phenotypes = set(fb_anatomical_phenotypes)

    existing_upheno_mappings_df = load_upheno_mappings()
    mapped_anatomy_ids = set(existing_upheno_mappings_df['anatomy_id'].tolist())

    unmapped_anatomy_ids = all_unique_fb_anatomical_phenotypes - mapped_anatomy_ids

    upheno_counter = next_upheno_id(existing_upheno_mappings_df)

    new_upheno_mappings: List[Mapping] = []

    for term, index in enumerate(sorted(unmapped_anatomy_ids)):
        upheno_id = UPHENO_PREFIX + str(upheno_counter)
        upheno_counter += 1
        new_upheno_mappings.append(Mapping(anatomy_id=index, upheno_id=upheno_id))

    # convert list of pydantic instances to dataframe
    new_upheno_mappings_df = pd.DataFrame([m.dict() for m in new_upheno_mappings])
    new_upheno_mappings_df = populate_upheno_id_number_column(new_upheno_mappings_df)

    # merge new upheno mappings with existing upheno mappings
    merged_upheno_mappings_df = pd.concat([existing_upheno_mappings_df, new_upheno_mappings_df], ignore_index=True)

    # save new dataframe to tsv file
    save_upheno_mappings(merged_upheno_mappings_df)


# starting ID, UPHENO:8 000 000   max ID UPHENO:8100000  raise ValueError above

def load_upheno_mappings() -> DataFrame:
    # if the file does not exist, return an empty dataframe with the expected columns
    try:
        df = pd.read_csv(MAPPING_FILE, sep='\t')
    except FileNotFoundError:
        df = pd.DataFrame(columns=['anatomy_id', 'upheno_id'])

    df = populate_upheno_id_number_column(df)
    return df


def populate_upheno_id_number_column(df: DataFrame) -> DataFrame:
    df['upheno_id_number'] = df['upheno_id'].apply(lambda x: int(x.split(':')[1]))
    return df


def next_upheno_id(df: DataFrame) -> str:
    if df is None or df.empty:
        return 8000000
    max_id = df['upheno_id_number'].max()
    return max_id + 1


def save_upheno_mappings(df: DataFrame):
    # if there is a upheno_id_number column, drop it
    if 'upheno_id_number' in df.columns:
        df = df.drop(columns=['upheno_id_number'])
    df.to_csv(MAPPING_FILE, sep='\t', header=True, index=False)

export_flybase_fbbt_phenotypes()
