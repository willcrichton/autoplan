from .labels import Labels
from .generator import ProgramGenerator
import torch
from torch import tensor
from torch.utils.data import Dataset as TorchDataset, DataLoader
from iterextras import unzip
from dataclasses import dataclass
from typing import List, Dict
from torch.utils.data.dataloader import default_collate
import torch.nn.functional as F


@dataclass
class Dataset:
    train_dataset: TorchDataset
    val_dataset: TorchDataset
    vocab_size: int
    choices: Dict[str, torch.Tensor]
    choice_indices: Dict[str, int]

    def loader(self, dataset, batch_size=100):
        return DataLoader(dataset,
                          batch_size=batch_size,
                          collate_fn=self._collate)

    # Compacts a list of sequences length [n1, n2, .. nk] into a tensor [k x max(n)]
    def _collate(self, batch):
        seq_keys = ['program', 'trace']
        collated = default_collate([{k: v
                                     for k, v in item.items() if k not in seq_keys}
                                    for item in batch])
        for k in seq_keys:
            seqs = [item[k] for item in batch]
            seq_lens = tensor([s.size(0) for s in seqs])
            max_len = max(seq_lens)
            collated[k] = torch.stack(
                [F.pad(seq, [0, max_len - seq.size(0)]) for seq in seqs])
            collated[k + '_len'] = seq_lens
        return collated


def build_synthetic_dataset(N_train, N_val, tokenizer, grammar):
    generator = ProgramGenerator(grammar=grammar)
    programs, choices, choice_options = unzip([generator.generate() for _ in range(N_train + N_val)])

    tokens, token_to_index, token_indices = tokenizer.tokenize_all(programs)
    vocab_size = len(token_to_index)

    all_choices = {}
    for opts in choice_options:
        all_choices = {**opts, **all_choices}

    choice_indices = {s: i for i, s in enumerate(all_choices.keys())}

    train_dataset = ProgramDataset(token_indices[:N_train], choices[:N_train], choice_indices)
    val_dataset = ProgramDataset(token_indices[N_train:], choices[N_train:], choice_indices)

    return Dataset(train_dataset=train_dataset,
                   val_dataset=val_dataset,
                   vocab_size=vocab_size,
                   choices=all_choices,
                   choice_indices=choice_indices)


class ProgramDataset(TorchDataset):
    def __init__(self, token_indices, choices, choice_index_map):
        self.token_indices = token_indices
        self.traces = [
            tensor([choice_index_map[name] for (name, choice) in cs])
            for cs in choices
        ]
        self.choices = [
            torch.zeros(len(choice_index_map), dtype=torch.long).scatter(
                dim=0, index=tensor([choice_index_map[name] for name, _ in cs]),
                src=tensor([choice for _, choice in cs]))
            for cs in choices
        ]

    def __len__(self):
        return len(self.token_indices)

    def __getitem__(self, idx):
        return {
            'program': self.token_indices[idx],
            'trace': self.traces[idx],
            'choices': self.choices[idx]
        }
