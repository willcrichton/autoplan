from .labels import Labels
from .generator import ProgramGenerator
import torch
from torch import tensor
from torch.utils.data import Dataset as TorchDataset, DataLoader, random_split
from iterextras import unzip
from dataclasses import dataclass
from typing import List, Dict, Tuple
from torch.utils.data.dataloader import default_collate
import torch.nn.functional as F
import pickle
import numpy as np

from pprint import pprint

@dataclass
class BaseDataset:
    dataset: TorchDataset
    vocab_size: int
    vocab_index: Dict[str, int]
    label_set: Labels
    class_balance: List[float]

    def loader(self, data, batch_size=100):
        return DataLoader(data,
                          batch_size=batch_size,
                          collate_fn=self._collate)

    # Compacts a list of sequences length [n1, n2, .. nk] into a tensor [k x max(n)]
    def _collate(self, batch):
        seq_keys = ['program', 'trace']
        collated = default_collate([{k: v
                                     for k, v in item.items() if k not in seq_keys}
                                    for item in batch])
        for k in seq_keys:
            if not k in batch[0]:
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
class PrelabeledDataset(BaseDataset):
    pass

class TrainValSplit:
    def set_train_val(self, val_frac):
        raise NotImplementedError

@dataclass
class RandomSplit(TrainValSplit):
    dataset: TorchDataset

    def set_train_val(self, val_frac=0.33):
        N = len(self.dataset.dataset)
        val_size = int(N * val_frac)
        return tuple(map(lambda ds: (ds, self.dataset.loader(ds)),
                         random_split(self.dataset.dataset, [N - val_size, val_size])))


@dataclass
class TrainVal(TrainValSplit):
    dataset: TorchDataset
    val_dataset: TorchDataset

    def set_train_val(self, val_frac=None):
        return (self.dataset.dataset, self.dataset.loader(self.dataset.dataset)), \
                (self.val_dataset.dataset, self.val_dataset.loader(self.val_dataset.dataset))


def build_synthetic_dataset(label_set, N, tokenizer, generator, vocab_index=None, unique=False):
    if unique:
        programs = []
        choices = []
        choice_options = []
        labels = []

        while len(programs) < N:
            program, choice, choice_option, label = unzip([generator.generate()])

            if (program[0] not in programs):
                programs.extend(program)
                choices.extend(choice)
                choice_options.extend(choice_option)
                labels.extend(label)
    else:
        programs, choices, choice_options, labels = unzip([generator.generate() for _ in range(N)])

    # Grammar parser
    tokens, token_to_index, token_indices, programs = tokenizer.tokenize_all(programs, vocab_index)

    vocab_size = len(token_to_index)

    all_choices = {}
    for opts in choice_options:
        all_choices = {**opts, **all_choices}
    choice_indices = {s: i for i, s in enumerate(all_choices.keys())}

    # Logistic classification
    label_list = list(label_set)
    program_labels = [torch.tensor(int(prog_label), dtype=torch.long) for prog_label in labels]

    class_hist = {lbl: 0 for lbl in label_list}
    for lbl in labels:
        class_hist[lbl] += 1
    class_balance = torch.tensor([class_hist[lbl] / sum(class_hist.values()) for lbl in label_list])

    dataset = ProgramDataset(
        programs, token_indices, program_labels, choices, choice_indices)

    return SyntheticDataset(
        dataset=dataset,
        vocab_size=vocab_size,
        vocab_index=token_to_index,
        label_set=label_list,
        class_balance=class_balance,
        choices=all_choices,
        choice_indices=choice_indices)


def build_prelabeled_dataset(label_set, programs, labels, codes, tokenizer):
    tokens, token_to_index, token_indices, programs = tokenizer.tokenize_all(programs)
    vocab_size = len(token_to_index)

    label_list = list(label_set)
    program_labels = [torch.tensor(int(prog_label), dtype=torch.long) for prog_label in labels]

    class_hist = {lbl: 0 for lbl in label_list}
    for lbl in labels:
        class_hist[lbl] += 1
    class_balance = torch.tensor([class_hist[lbl] / sum(class_hist.values()) for lbl in label_list])

    return PrelabeledDataset(
        dataset=ProgramDataset(programs, token_indices, program_labels, codes=codes),
        vocab_size=vocab_size,
        vocab_index=token_to_index,
        label_set=label_list,
        class_balance=class_balance)


class ProgramDataset(TorchDataset):
    def __init__(self, programs, token_indices, labels, choices=None, choice_index_map=None, codes=None):
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


    def __len__(self):
        return len(self.items)

    def __getitem__(self, idx):
        return self.items[idx]


def set_random_seed(i=0):
    torch.manual_seed(i)
    np.random.seed(i)
