import pyro
from .generator import get_generator


class Rule:
    def __init__(self, **kwargs):
        self.params = kwargs

    def sample(self, name, dist):
        return pyro.sample(name, dist)

    def global_sample(self, name, dist):
        generator = get_generator()
        if not generator.has_global(name):
            generator.set_global(name, pyro.sample(name, dist))
        return generator.get_global(name)

    def set_label(self, label):
        get_generator().set_label(label)

    def render(self):
        raise NotImplementedError

    def format(self, template, **templateVars):
        startTemp = '<START_BRACKET>'
        endTemp = '<END_BRACKET>'
        template = template.replace('{{', startTemp)
        template = template.replace('}}', endTemp)

        result = template.format(**templateVars)

        result = result.replace(startTemp, '{{')
        result = result.replace(endTemp, '}}')
        return result
