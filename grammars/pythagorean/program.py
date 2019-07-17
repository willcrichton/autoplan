from autoplan.grammar import Rule
from autoplan.distributions import Categorical
from autoplan.labels import Labels


class PythagoreanLabels(Labels):
    UsesMathPow = 0
    UsesInlineCalculation = 1


class InputPrompt(Rule):
    def render(self):
        return self.choice('input_prompt', {
            '': 55,  # empty string to keep simplest prompt unchanged
            'Enter ': 22,
            'enter value ': 11,
            'Enter value for ': 11,
        })


class OutputPrompt(Rule):
    def render(self):
        var = self.params['var']
        return self.choice('output_prompt', {
            f'{var}=': 55,
            f'{var}:': 22,
            'The answer is': 11,
            'The hypotenuse is': 11
        })


class Exponential(Rule):
    def render(self):
        uses_method = self.choice('uses_method', {True: 5, False: 10})
        var = self.params['var']
        if uses_method:
            self.set_label(PythagoreanLabels.UsesMathPow)
            return f'Math.pow({var}, 2)'
        else:
            self.set_label(PythagoreanLabels.UsesInlineCalculation)
            return f'{var} * {var}'


class MainPrompt(Rule):
    def render(self):
        return self.choice('main_prompt', {
            'Enter values to compute the Pythagorean Theorem.': 70,
            'This program finds the hypotenuse, C, of a triangle with sides A and B.': 15,
            'This program runs the Pythagorean Theorem. Choose values a and b.': 15,
        })


class Solution(Rule):
    def render(self):
        naming_scheme = self.choice('naming_scheme', {'a': 1, 'x': 1})
        num_type = self.choice('num_type', {'int': 1, 'double': 1})
        print_function = self.choice('print_function', {'println': 1, 'print': 1})

        template = '''
        {print_function}("{main_prompt}");
        {num_type} {first_var} = {read_function}("{input_prompt}{first_var}:");
        {num_type} {second_var} = {read_function}("{input_prompt}{second_var}:");
        {num_type} {third_var} = Math.sqrt({exp_first} + {exp_second});
        {print_function}("{output_prompt}" + {third_var});
        '''

        first_var = 'x' if naming_scheme == 'x' else 'a'
        second_var = 'y' if naming_scheme == 'x' else 'b'
        third_var = 'z' if naming_scheme == 'x' else 'c'
        return self.format(template,
                           num_type=num_type,
                           first_var=first_var,
                           second_var=second_var,
                           third_var=third_var,
                           read_function='readInt' if num_type == 'int' else 'readDouble',
                           main_prompt=MainPrompt().render(),
                           input_prompt=InputPrompt().render(),
                           exp_first=Exponential(var=first_var).render(),
                           exp_second=Exponential(var=second_var).render(),
                           print_function=print_function,
                           output_prompt=OutputPrompt(var=third_var).render())


class Program(Rule):
    def render(self):
        template = '''
            public class PythagoreanTheorem extends ConsoleProgram {{
                public void run() {{
                    {Solution}
                }}
            }}
        '''
        return self.format(template, Solution=Solution().render())
