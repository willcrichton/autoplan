from pyro.distributions import Distribution
import pyro.distributions as dist
from torch import tensor
from iterextras import unzip


class Categorical(Distribution):
    def __init__(self, option_map):
        values, weights = unzip(option_map.items())
        self.values = values
        total = sum(weights)
        self.dist = dist.Categorical(tensor([w / total for w in weights]))

    def log_prob(self, x):
        return self.dist.log_prob(self.values.index(x))

    def sample(self):
        return self.values[self.dist.sample()]
