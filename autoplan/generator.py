GLOBAL_GENERATOR = None


def get_generator():
    return GLOBAL_GENERATOR


class Generator:
    def __init__(self, grammar):
        self.grammar = grammar

    def has_global(self, key):
        return key in self.global_state

    def get_global(self, key):
        return self.global_state[key]

    def set_global(self, key, value):
        self.global_state[key] = value

    def set_label(self, label):
        self.label = label

    def generate(self):
        global GLOBAL_GENERATOR
        GLOBAL_GENERATOR = self

        self.global_state = {}
        self.label = None

        return self.grammar.render(), self.label
