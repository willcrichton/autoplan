from torch.distributions.categorical import Categorical
import torch
from iterextras import unzip
from copy import copy
from .models import GrammarInference
import torch.nn.functional as F
from enum import IntEnum
from collections import OrderedDict, defaultdict

GLOBAL_GENERATOR = None

def get_generator():
    return GLOBAL_GENERATOR

def set_generator(gen):
    global GLOBAL_GENERATOR
    GLOBAL_GENERATOR = gen

class ProgramGenerator:
    def __init__(self, grammar, adaptive):
        self.grammar = grammar
        self.production_choices = {}
        self.choices_counter = defaultdict(int) # Initializes the choices over a production cycle, not a program
        self.adaptive = adaptive

    def apply_penalties(self, values, weights):
        counter = 1 # To avoid division by 0
        for index in range(len(values)):
            counter += self.choices_counter[values[index]] 
            weights[index] = weights[index] * 1 / counter
        return weights

    def choice(self, name, options):
        if name not in self.choices:
            assert options is not None
            values, weights = unzip(options.items())
        
            if self.adaptive:
                weights = self.apply_penalties(values, weights)
                
            probs = torch.tensor(weights, dtype=torch.float) / sum(weights)
            dist = Categorical(probs) # Chooses a sample
            index = dist.sample().item() # Returns a sample
            value = values[index] # Returns the actual string
            
            self.choices[name] = (index, value)
            self.choice_options[name] = list(zip(probs.tolist(), values))
            self.production_choices.update(self.choice_options)
            self.choices_counter[value] += 1 # Updates the counter of the choices globally
        return self.choices[name][1]

    def generate(self):
        set_generator(self)

        if not self.adaptive:
            self.choice_options = {} 
        else:
            self.choice_options = self.production_choices 
        self.choices = OrderedDict() # Specific program choices are always reset

        return (self.grammar.render(),
                [('START', 0)] + [(k, v[0]) for k, v in self.choices.items()],
                {'START': [(1., None)], **self.choice_options})
