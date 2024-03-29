from .labels import Labels
from .generator import ProgramGenerator
from .parser import Parser

import torch
from torch import tensor
from torch.utils.data import Dataset as TorchDataset, DataLoader, random_split
from iterextras import unzip
from dataclasses import dataclass
from typing import List, Dict, Tuple
from torch.utils.data.dataloader import default_collate
from torch.utils.data import ConcatDataset, Subset
import torch.nn.functional as F
import pickle
import numpy as np
import dataclasses

from pprint import pprint

@dataclass
class BaseDataset:
    dataset: TorchDataset
    vocab_size: int
    vocab_index: Dict[str, int]
    label_set: Labels
    parser: Parser

    def class_balance(self):
        labels = np.array([item['labels'].item() for item in self.dataset])
        return tensor([np.count_nonzero(labels == int(l)) for l in self.label_set], dtype=torch.float) / len(labels)

    def loader(self, data, batch_size=100, shuffle=False):
        return DataLoader(data,
                          batch_size=batch_size,
                          shuffle=shuffle,
                          collate_fn=self._collate)

    def subset(self, length):
        idxs = np.random.permutation(len(self.dataset))
        return dataclasses.replace(self, dataset=Subset(self.dataset, idxs[:length]))

    # Compacts a list of sequences length [n1, n2, .. nk] into a tensor [k x max(n)]
    def _collate(self, batch):
        seq_keys = ['program', 'trace']
        other_keys = [k for k in batch[0].keys() if k not in seq_keys and all([k in item for item in batch])]
        collated = default_collate([{k: v
                                     for k, v in item.items() if k in other_keys}
                                    for item in batch])
        for k in seq_keys:
            if not all([k in item for item in batch]):
                continue
            seqs = [item[k] for item in batch]
            seq_lens = tensor([s.size(0) for s in seqs])
            max_len = max(seq_lens)
            collated[k] = torch.stack(
                [F.pad(seq, [0, max_len - seq.size(0)]) for seq in seqs])
            collated[k + '_len'] = seq_lens
        return collated

    # Takes a ProgramDataset item and converts the trace/choice indices to readable strings
    # e.g. dataset.readable_choices(dataset.train_dataset[0])
    def readable_choices(self, item):
        choice_names = {v: k for k, v in self.choice_indices.items()}
        return [
            (choice_names[name_index.item()],
             self.choices[choice_names[name_index.item()]][value_index][1])
            for name_index, value_index in zip(item['trace'], item['choices'])
        ]

    def save(self, path):
        pickle.dump(self, open(path, 'wb'))

    @staticmethod
    def load(path):
        return pickle.load(open(path, 'rb'))

@dataclass
class SyntheticDataset(BaseDataset):
    choices: Dict[str, List[Tuple[float, str]]]
    choice_indices: Dict[str, int]


@dataclass
class LabeledDataset(BaseDataset):
    pass

class TrainTestSplit:
    def set_train_test(self, test_frac):
        raise NotImplementedError

@dataclass
class RandomSplit(TrainTestSplit):
    dataset: TorchDataset
    shuffle: bool = True

    def set_train_test(self, test_frac=0.33):
        N = len(self.dataset.dataset)
        test_size = int(N * test_frac)
        return tuple(map(lambda ds: (ds, self.dataset.loader(ds, shuffle=self.shuffle)),
                         random_split(self.dataset.dataset, [N - test_size, test_size])))


@dataclass
class TrainVal(TrainTestSplit):
    dataset: TorchDataset
    test_dataset: TorchDataset

    def set_train_test(self, test_frac=None):
        return (self.dataset.dataset, self.dataset.loader(self.dataset.dataset, shuffle=True)), \
                (self.test_dataset.dataset, self.test_dataset.loader(self.test_dataset.dataset))


def build_synthetic_dataset(label_set, N, parser, generator, vocab_index=None, unique=False):
    if unique:
        programs = []
        choices = []
        choice_options = []
        labels = []

        while len(programs) < N:
            program, choice, choice_option, label = generator.generate()

            if program not in programs:
                programs.append(program)
                choices.append(choice)
                choice_options.append(choice_option)
                labels.append(label)
    else:
        programs, choices, choice_options, labels = unzip([generator.generate() for _ in range(N)])

    # Grammar parser
    tokens, token_to_index, token_indices, new_programs = parser.tokenize_all(programs, vocab_index)

    for prog, tok in zip(programs, tokens):
        if len(tok) == 0:
            raise Exception(f'Created zero-length program from original source:\n{prog}')

    vocab_size = len(token_to_index)

    all_choices = {}
    for opts in choice_options:
        all_choices = {**opts, **all_choices}
    choice_indices = {s: i for i, s in enumerate(all_choices.keys())}

    # Logistic classification
    label_list = list(label_set)
    program_labels = [torch.tensor(int(prog_label), dtype=torch.long) for prog_label in labels]

    dataset = ProgramDataset(
        new_programs, token_indices, program_labels, choices, choice_indices)

    return SyntheticDataset(
        dataset=dataset,
        vocab_size=vocab_size,
        vocab_index=token_to_index,
        label_set=label_list,
        choices=all_choices,
        choice_indices=choice_indices,
        parser=parser)


def build_labeled_dataset(label_set, programs, labels, parser, codes=None, countwhere=None, vocab_index=None):
    tokens, token_to_index, token_indices, programs = parser.tokenize_all(
        programs, vocab_index=vocab_index)
    vocab_size = len(token_to_index)

    label_list = list(label_set)
    program_labels = [torch.tensor(int(prog_label), dtype=torch.long) for prog_label in labels]

    return LabeledDataset(
        dataset=ProgramDataset(programs, token_indices, program_labels, codes=codes, countwhere=countwhere),
        vocab_size=vocab_size,
        vocab_index=token_to_index,
        label_set=label_list,
        parser=parser)


class ProgramDataset(TorchDataset):
    def __init__(self, programs, token_indices, labels, choices=None, choice_index_map=None, codes=None, countwhere=None):
        self.items = [
            {
                'source': programs[idx],
                'program': token_indices[idx],
                'labels': labels[idx],
            }
            for idx in range(len(token_indices))
        ]

        if choices is not None:
            traces = [
                tensor([choice_index_map[name] for (name, choice) in cs])
                for cs in choices
            ]

            choices = [
                torch.zeros(len(choice_index_map), dtype=torch.long).scatter(
                    dim=0, index=tensor([choice_index_map[name] for name, _ in cs]),
                    src=tensor([choice for _, choice in cs]))
                for cs in choices
            ]

            self.items = [
                {**self.items[idx], **{
                    'trace': traces[idx],
                    'choices': choices[idx],
                }}
                for idx in range(len(token_indices))
            ]


        if codes is not None:
            self.items = [
                {**self.items[idx], 'code': codes[idx]}
                for idx in range(len(token_indices))
            ]

        if countwhere is not None:
            self.items = [
                {**self.items[idx], 'countwhere': countwhere[idx]}
                for idx in range(len(token_indices))
            ]


    def __len__(self):
        return len(self.items)

    def __getitem__(self, idx):
        return self.items[idx]


def set_random_seed(i=0):
    torch.manual_seed(i)
    np.random.seed(i)


def concat_datasets(ds1, ds2):
    return dataclasses.replace(ds1, dataset=ConcatDataset([ds1.dataset, ds2.dataset]))
