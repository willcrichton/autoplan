from .generator import get_generator


class Rule:
    def __init__(self, **kwargs):
        self.params = kwargs

    def choice(self, name, options=None):
        generator = get_generator()
        return generator.choice(name, options)

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

    def render(self):
        raise NotImplementedError
