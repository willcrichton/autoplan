from .generator import get_generator


class Rule:
    def __init__(self, **kwargs):
        self.params = kwargs

    def choice(self, name, options=None):
        return get_generator().choice(name, options)

    def format(self, template, **templateVars):
        startTemp = '<START_BRACKET>'
        endTemp = '<END_BRACKET>'
        template = template.replace('{{', startTemp)
        template = template.replace('}}', endTemp)

        result = template.format(**templateVars)

        # Output programs
        result = result.replace(startTemp, '{')
        result = result.replace(endTemp, '}')
        return result

    def set_label(self, label):
        get_generator().set_label(label)

    def render(self):
        raise NotImplementedError
