from .generator import get_generator
from jinja2 import Template

class Rule:
    def __init__(self, **kwargs):
        self.params = kwargs

    def choice(self, name, options=None):
        return get_generator().choice(name, options)

    def format(self, template, **templateVars):
        return Template(template).render(**templateVars)

    def set_label(self, label):
        get_generator().set_label(label)

    def render(self):
        raise NotImplementedError
