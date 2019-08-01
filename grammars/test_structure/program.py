from autoplan.grammar import Rule
from autoplan.labels import Labels

class TestStructureLabels(Labels):
	SingleLoop = 0
	AddFirst = 1

class SingleLoop(Rule):
	def render(self):
		counter = self.choice('counter', {'c' : 1, 'counter' : 1})
		naming_scheme = self.choice('naming_scheme', {'a': 1, 'x': 1})
		num_type = self.choice('num_type', {'int': 1, 'double': 1})
		print_function = self.choice('print_function', {'println': 1, 'print': 1})
		add_first = self.choice('add_first', {True: 1, False: 1})

		template = '''
		public class TestStructureLabels extends ConsoleProgram {
			public void run() {
				{{num_type}} {{counter}} = 0;
				for ({{num_type}} {{var}} = 0; {{num_type}} < 10; {{num_type}}++) {
					{%- if add_first -%}
						{{var}}++;
						{{counter}} += {{var}};
					{%- else -%}
						{{counter}} += {{var}};
						{{var}}++;
					{%- endif -%}
				{{print_function}}({{var}});
				}  
			}
		}'''

		self.set_label(TestStructureLabels.SingleLoop)
		return self.format(
			template,
			num_type=num_type,
			var=naming_scheme,
			counter=counter,
			print_function=print_function)


class AddFirst(Rule):
	def render(self):
		counter = self.choice('counter', {'c' : 1, 'counter' : 1})
		naming_scheme = self.choice('naming_scheme', {'a': 1, 'x': 1})
		num_type = self.choice('num_type', {'int': 1, 'double': 1})
		print_function = self.choice('print_function', {'println': 1, 'print': 1})

		template = '''
		public class TestStructureLabels extends ConsoleProgram {
    		public void run() {
    			{{num_type}} {{counter}} = 0;
        		for ({{num_type}} {{var}} = 0; {{num_type}} < 10; {{num_type}}++) {
					{{counter}} += {{var}};
				}
				for ({{num_type}} {{var}} = 0; {{num_type}} < 10; {{num_type}}++) {
					{{var}}++;
					{{print_function}}({{var}});
				}  
    		}
		}
		'''

		self.set_label(TestStructureLabels.AddFirst)
		return self.format(
			template,
			num_type=num_type,
			var=naming_scheme,
			counter=counter,
			print_function=print_function)


class Program(Rule):
	def render(self):
		strategy = self.choice('strategy', {
			TestStructureLabels.SingleLoop: 1,
			TestStructureLabels.AddFirst: 1
		})

		if strategy == TestStructureLabels.SingleLoop:
			return SingleLoop().render()
		elif strategy == TestStructureLabels.AddFirst:
			return AddFirst().render()

