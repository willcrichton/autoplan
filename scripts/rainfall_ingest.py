import pandas as pd
import os

from autoplan.dataset import build_prelabeled_dataset, PrelabeledDataset
from autoplan.token import OCamlTokenizer, PyretTokenizer, TokenizerError

from grammars.rainfall.labels import GeneralRainfallLabels, DetailedRainfallLabels

REPO_DIR = os.path.expanduser('~/autoplan')
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


def pyret_source_filter(src):
    src = src.replace('[', '[list:')
    src = src.replace(';', ' end')
    src = src.replace(' : Number', ' :: Number') #hack
    src = src.replace('= fun', '= lam')
    src = src.replace(' (nums', '(nums')
    src = src.replace(' (my-nums', '(my-nums')
    src = src.replace('fun(', 'lam(')
    src = src.replace('fun (', 'lam(')
    src = src.replace('f<0', 'f < 0') #hack
    src = src.replace('f>0', 'f > 0') #hack
    for tok in ['==', '/', '+', '*', '=>', '<>']:
        src = src.replace(tok, f' {tok} ')
    src = src.replace('not (', 'not(')
    src = src.replace('"', '```')
    src = src.replace('check:', 'where:')
    return src


dataset_config = {
    'T1': {
        'path': lambda id: f'{CODE_DIR}/T1/{id}.ml',
        'tokenizer': OCamlTokenizer,
        'source_filter': lambda src: src
    },
    'T1Acc': {
        'path': lambda id:
        f'{CODE_DIR}/T1Acc/{id}/cs019-2013-rainfall/rainfall-program.current.arr',
        'tokenizer': PyretTokenizer,
        'source_filter': pyret_source_filter
    }
}


def ingest_dataset(name, **kwargs):
    codes = read_and_join_coding(name)
    config = dataset_config[name]
    tokenizer = dataset_config[name]['tokenizer'](**kwargs)

    programs = []
    labels = []
    skipped = 0
    for _, entry in codes.iterrows():
        path = config['path'](entry.ID)
        try:
            src = open(path).read()
        except FileNotFoundError:
            skipped += 1
            continue

        src = config['source_filter'](src)

        try:
            general_label = GeneralRainfallLabels.from_string(entry['Gen Category'].strip())
            detailed_label = DetailedRainfallLabels.from_string(entry['Detail Category'].strip())
        except Exception:
            skipped += 1
            continue


        print(src)
        print('*'*10)
        try:
            tokens, prog = tokenizer.tokenize(src)
            print(prog)
            list(tokens)
        except TokenizerError as e:
            lines = src.split('\n')
            # print('\n'.join([f'{i:02d}: {l}' for i, l in zip(range(1, len(lines)+1), lines)]))
            # print(e.args[1])
            skipped += 1
            continue
        print('='*30)
        programs.append(src)

        labels.append(general_label)

    assert len(programs) > 0

    print('Skipped {} programs'.format(skipped))
    return build_prelabeled_dataset(GeneralRainfallLabels, programs, labels, tokenizer)


if __name__ == "__main__":
    for key in ['T1']:
        ds = ingest_dataset(key, preprocess=False)
        ds.save(f'{REPO_DIR}/data/rainfall/{key}-noprocess.pkl')
