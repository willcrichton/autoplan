from autoplan.grammar import Rule
from autoplan.labels import Labels

class SimpleLabels(Labels):
    Ignore = 1

class Program(Rule):
    def render(self):
        naming_scheme = self.choice('naming_scheme', {'a': 1, 'x': 1})
        num_type = self.choice('num_type', {'int': 1, 'double': 1})
        print_function = self.choice('print_function', {'println': 1, 'print': 1})
        for i in range(5):
            self.choice(f'str_choice{i}', {'a': 1, 'b': 1})

        template = '''
            public class PythagoreanTheorem extends ConsoleProgram {{
                public void run() {{
                     {num_type} {var} = {read_function}("Foobar:");
                     {print_function}({var});
                }}
            }}
        '''

        self.set_label(SimpleLabels.Ignore)

        return self.format(
            template,
            num_type=num_type,
            var=naming_scheme,
            print_function=print_function,
            read_function='readInt' if num_type == 'int' else 'readDouble')
