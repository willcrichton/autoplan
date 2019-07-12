from torch.distributions.categorical import Categorical
import torch
from iterextras import unzip
from copy import copy
from collections import OrderedDict

GLOBAL_GENERATOR = None


def get_generator():
    return GLOBAL_GENERATOR


class ProgramGenerator:
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

        return (self.grammar.render(),
                [('START', 0)] + [(k, v[0]) for k, v in self.choices.items()],
                {'START': [(1., None)], **self.choice_options})
