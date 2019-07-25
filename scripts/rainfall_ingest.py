import pandas as pd
import os

from autoplan.dataset import build_prelabeled_dataset, PrelabeledDataset
from autoplan.token import OCamlTokenizer, PyretTokenizer, TokenizerError

from grammars.rainfall.labels import GeneralRainfallLabels, DetailedRainfallLabels

REPO_DIR = os.path.expanduser('~/Code/autoplan')
DATA_DIR = f'{REPO_DIR}/data/rainfall/raw'
CODE_DIR = f'{DATA_DIR}/Fall2013-RawData'

plan_codes = pd.read_csv(f'{DATA_DIR}/PlanCodes-codes.csv')


def read_coding_csv(name):
    return pd.read_csv(f'{DATA_DIR}/Fall2013Coding{name}.csv', index_col=0, header=None).T


def read_and_join_coding(name):
    coding_csv = read_coding_csv(name)
    valid_entries = coding_csv[coding_csv.PlanStructure.notnull()]
    combined_entries = valid_entries.set_index('PlanStructure').join(plan_codes.set_index('Code'))
    return combined_entries


dataset_config = {
    'T1': {
        'path': lambda id: f'{CODE_DIR}/T1/{id}.ml',
        'tokenizer': OCamlTokenizer
    },
    'T1Acc': {
        'path': lambda id:
        f'{CODE_DIR}/T1Acc/{id}/cs019-2013-rainfall/rainfall-program.current.arr',
        'tokenizer': PyretTokenizer
    }
}


def ingest_dataset(name, **kwargs):
    codes = read_and_join_coding(name)
    config = dataset_config[name]
    tokenizer = dataset_config[name]['tokenizer'](**kwargs)

    programs = []
    labels = []
    for _, entry in codes.iterrows():
        path = config['path'](entry.ID)
        try:
            src = open(path).read()
        except FileNotFoundError:
            continue

        general_label = GeneralRainfallLabels.from_string(entry['Gen Category'].strip())
        detailed_label = DetailedRainfallLabels.from_string(entry['Detail Category'].strip())

        try:
            tokens, _ = tokenizer.tokenize(src)
            list(tokens)
        except TokenizerError as e:
            continue

        programs.append(src)
        labels.append(general_label)

    return build_prelabeled_dataset(GeneralRainfallLabels, programs, labels, tokenizer)


if __name__ == "__main__":
    for key in ['T1']:
        ds = ingest_dataset(key, preprocess=False)
        ds.save(f'{REPO_DIR}/data/rainfall/{key}-noprocess.pkl')
