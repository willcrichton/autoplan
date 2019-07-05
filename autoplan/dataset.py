from .labels import Labels
from .generator import Generator
from javalang import tokenizer
import torch
from torch.utils.data import Dataset as TorchDataset
from iterextras import unzip
from dataclasses import dataclass
from typing import List


@dataclass
class Dataset:
    train_dataset: TorchDataset
    val_dataset: TorchDataset
    vocab_size: int
    label_set: Labels
    class_balance: List[float]


def token_to_key(token):
    typ = type(token)
    value = token.value

    if typ == tokenizer.String:
        return typ
    else:
        return (typ, value)


def build_dataset(N_train, N_val, grammar, label_set):
    generator = Generator(grammar=grammar)
    programs, labels = unzip([generator.generate() for _ in range(N_train + N_val)])

    token_keys = [[token_to_key(token) for token in tokenizer.tokenize(program)]
                  for program in programs]

    token_to_index = {}
    for l in token_keys:
        for k in l:
            if not k in token_to_index:
                token_to_index[k] = len(token_to_index)

    vocab_size = len(token_to_index)

    token_indices = [
        torch.tensor([token_to_index[k] for k in tk], dtype=torch.long) for tk in token_keys
    ]

    label_list = list(label_set)
    program_labels = [torch.tensor(int(prog_label), dtype=torch.long) for prog_label in labels]

    train_dataset = ProgramDataset(token_indices[:N_train], program_labels[:N_train])
    val_dataset = ProgramDataset(token_indices[N_train:], program_labels[N_train:])

    class_hist = {lbl: 0 for lbl in label_list}
    for lbl in labels[:N_train]:
        class_hist[lbl] += 1
    class_balance = torch.tensor([class_hist[lbl] / sum(class_hist.values()) for lbl in label_list])

    return Dataset(train_dataset=train_dataset,
                   val_dataset=val_dataset,
                   vocab_size=vocab_size,
                   label_set=label_set,
                   class_balance=class_balance)


class ProgramDataset(TorchDataset):
    def __init__(self, token_indices, labels):
        self.token_indices = token_indices
        self.labels = labels

    def __len__(self):
        return len(self.token_indices)

    def __getitem__(self, idx):
        return {
            'input_sequence': self.token_indices[idx],
            'seq_lengths': len(self.token_indices[idx]),
            'labels': self.labels[idx]
        }
