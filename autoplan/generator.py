from torch.distributions.categorical import Categorical
import torch
from iterextras import unzip
from copy import copy
from .models import GrammarInference
import torch.nn.functional as F
from enum import IntEnum
from collections import OrderedDict

GLOBAL_GENERATOR = None


def get_generator():
    return GLOBAL_GENERATOR


class Generator:
    def __init__(self, grammar):
        self.grammar = grammar

    def choice(self, name, options):
        if name not in self.choices:
            assert options is not None
            values, weights = unzip(options.items())
            probs = torch.tensor(weights, dtype=torch.float) / sum(weights)
            dist = Categorical(probs)
            index = dist.sample().item()
            value = values[index]
            self.choices[name] = (index, value)
            self.choice_options[name] = list(zip(probs.tolist(), values))
        return self.choices[name][1]

    def generate(self):
        global GLOBAL_GENERATOR
        GLOBAL_GENERATOR = self

        self.choices = OrderedDict()
        self.choice_options = {}

        return self.grammar.render(), [(k, v[0]) for k, v in self.choices.items()], copy(self.choice_options)


class InferenceStrategy(IntEnum):
    Sample = 1
    MAP = 2

    def compute_index(self, probs):
        if self.value == InferenceStrategy.Sample.value:
            return Categorical(probs).sample()
        elif self.value == InferenceStrategy.MAP.value:
            return torch.topk(probs, 1)[1][0].item()

class Inference:
    def __init__(self, grammar, dataset, device, strategy=InferenceStrategy.MAP):
        self.dataset = dataset
        self.grammar = grammar
        self.model = GrammarInference(dataset, device)
        self.device = device
        self.prev_choice = None
        self.strategy = strategy

    def choice(self, name, options):
        if name not in self.choices:
            with torch.no_grad():
                if self.prev_choice is None:
                    preds = self.model.inference[name](self.h)
                else:
                    preds, h = self.model.step(self.prev_choice, name, self.program_emb, self.h, self.choices)
                    self.h = h

            probs = F.softmax(preds[0][0], dim=0).cpu()
            index = self.strategy.compute_index(probs)
            self.choices[name] = (index, self.dataset.choices[name][index][1])

        return self.choices[name][1]

    def infer(self, input_sequence, seq_lengths):
        global GLOBAL_GENERATOR
        GLOBAL_GENERATOR = self

        self.choices = OrderedDict()

        self.program_emb = self.model.encoder(
            input_sequence.to(self.device),
            seq_lengths.to(self.device))
        self.h = self.model.init_hidden(input_sequence.size(0))

        self.grammar.render()
        return self.choices
