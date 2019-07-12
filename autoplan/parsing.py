from enum import IntEnum
from torch.distributions.categorical import Categorical
import torch
import torch.nn.functional as F

from .models import NeuralParser


class InferenceStrategy(IntEnum):
    Sample = 1
    MAP = 2

    def compute_index(self, probs):
        if self.value == InferenceStrategy.Sample.value:
            return Categorical(probs).sample()
        elif self.value == InferenceStrategy.MAP.value:
            return torch.topk(probs, 1)[1][0].item()


class Parser:
    def __init__(self, grammar, dataset, device, strategy=InferenceStrategy.MAP):
        self.dataset = dataset
        self.grammar = grammar
        self.model = NeuralParser(dataset, device)
        self.device = device
        self.prev_choice = 'START'
        self.strategy = strategy

    def choice(self, name, options):
        if name not in self.choices:
            with torch.no_grad():
                preds, h = self.model.step(self.prev_choice, name, self.program_emb, self.h, self.choices)
                self.h = h

            probs = F.softmax(preds[0][0], dim=0).cpu()
            index = self.strategy.compute_index(probs)
            self.choices[name] = (index, self.dataset.choices[name][index][1])

        return self.choices[name][1]

    def infer(self, input_sequence, seq_lengths):
        global GLOBAL_GENERATOR
        GLOBAL_GENERATOR = self

        self.choices = OrderedDict(START=(0, None))

        self.program_emb = self.model.encoder(
            input_sequence.to(self.device),
            seq_lengths.to(self.device))
        self.h = self.model.init_hidden(input_sequence.size(0))

        self.grammar.render()
        return self.choices
