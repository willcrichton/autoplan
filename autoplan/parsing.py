from enum import IntEnum
from torch.distributions.categorical import Categorical
import torch
from torch import tensor
import torch.nn.functional as F
from .generator import set_generator
from .models import NeuralParser
from collections import OrderedDict


class InferenceStrategy(IntEnum):
    Sample = 1
    MAP = 2

    def compute_index(self, probs):
        if self.value == InferenceStrategy.Sample.value:
            return Categorical(probs).sample()
        elif self.value == InferenceStrategy.MAP.value:
            return torch.topk(probs, 1)[1][0].item()


class ProgramParser:
    def __init__(self, grammar, dataset, model_path, device, strategy=InferenceStrategy.MAP):
        self.dataset = dataset
        self.grammar = grammar
        self.model = NeuralParser(dataset, device)
        self.model.load(model_path)
        self.model.eval()
        self.device = device
        self.prev_choice = tensor([self.dataset.choice_indices['START']]).to(self.device)
        self.strategy = strategy
        self.choice_tensor = torch.zeros(len(self.dataset.choice_indices)).long().to(self.device)

    def choice(self, name, options):
        if name not in self.choices:
            with torch.no_grad():
                cur_choice = tensor([self.dataset.choice_indices[name]]).to(self.device)
                preds, h = self.model.step(
                    prev_choice=self.prev_choice,
                    cur_choice=cur_choice,
                    program_emb=self.program_emb,
                    h=self.h,
                    choices=self.choice_tensor.unsqueeze(0))
                self.h = h
                self.prev_choice = cur_choice

            probs = F.softmax(preds[0], dim=0).cpu()
            index = self.strategy.compute_index(probs)
            self.choices[name] = (index, self.dataset.choices[name][index][1])
            self.choice_tensor[cur_choice.item()] = index

        return self.choices[name][1]

    def infer(self, program, program_len):
        set_generator(self)

        self.choices = OrderedDict(START=(0, None))

        self.program_emb = self.model.encoder(
            program.to(self.device),
            program_len.to(self.device))
        self.h = self.model.init_hidden(program.size(0))

        self.grammar.render()

        return self.choices
