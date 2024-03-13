import json
from oaklib import get_adapter
import pandas as pd

adapter = get_adapter("sqlite:obo:apo")

# Path to the file
sgd_raw_data_path = '../data/PHENOTYPE_SGD.json'
sgd_dosdp_path = '../data/sgd_dosdp.tsv'
sgd_pato_mapping_path = '../data/sgd_pato.sssom.tsv'


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

