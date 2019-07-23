from autoplan.grammar import Rule
from .labels import GeneralRainfallLabels

Labels = GeneralRainfallLabels

class SingleLoopHelper(Rule):
    def render(self):
        addition = self.choice('addition', {'accumulator' : 1, 'acc' : 1, 'sum' : 1, 'total' : 1, 'n' : 1, 'avg' : 1})
        counter = self.choice('counter', {'count' : 1, 'f' : 1, 'counter' : 1, 'num_processed' : 1, 'index' : 1, 'num' : 1, 'num_elements' : 1})
        return_type = self.choice('return_type', {'int': 1, 'float': 1})
        recursion = self.choice('recursion', {'' : 1, 'rec' : 1})
        list_name = self.choice('list_name', 
            {'alon2': 1, 
            'lon': 1})
        empty_list = self.choice('empty_list', {'[]' : 1, '[] | -999 :: _' : 1})
        div_by_zero = self.choice('div_by_zero', {True: 1, False: 1})
        gt_zero = self.choice('gt_zero', {True : 1, False : 1}) # Else student uses = 0
        raises_failwith = self.choice('raises_failwith', {True : 1}, False : 1)
        fail_message = self.choice('fail_message', {'No data input.' : 1, 'No rainfall' : 1})

        template = '''
{% set average %}
    {% if return_type == 'int' %} 
        {{addition}} / {{counter}}
    {% else %} 
        {{addition}} /. {{counter}}
    {% endif %}
{% endset %}

{% set failure %}
    {% if raises_failwith %}
        failwith {{fail_message}}
    {% else %}
        {% if return_type == 'int' %} 
            0
        {% else %} 
            0.
        {% endif %}
    {% endif %}
{% endset %}

let {{recursion}} {{helper_name}} ({{list_name}} : {{list_type}} list) ({{addition}} : {{list_type}}) ({{counter}} : {{list_type}}) : {{return_type}} =
    match {{list_name}} with
    | {{empty_list}} -> 
    {% if div_by_zero %} 
        {% if gt_zero %}
            if {{counter}} > 0 then {{average}} else {{failure}}
        {% else %} 
            if {{counter}} = 0 then {{failure}} else {{average}}
        {% endif}
    {% else %} 
        {{ average }}
    {% endif %}
    | TODO: Method Body


'''

        average = '''
        '''

        return self.format(template, 
            helper_name=self.params['helper_name'], 
            list_type=self.params['list_type'], 
            average=average)


class DecomposedSingleLoop(Rule):
    def render(self):
        helper_in_body = self.choice('helper_in_body', {True: 1, False: 1})
        helper_name = self.choice('helper_name', 
            {'_rainfall': 1, 
            'rainfall_helper': 1, 
            'rainfall_help': 1})
        list_name = self.choice('list_name', 
            {'alof': 1, 
            'alon': 1,
            'aloi': 1,
            'rain_list': 1})
        list_type = self.choice('list_type', {'int': 1, 'float': 1})
        return_type = self.choice('return_type', {'int': 1, 'float': 1})
        recursion = self.choice('recursion', {'' : 1, 'rec' : 1})
    
        template = '''
{% if not helper_in_body %}
    {{helper_body}}

let {{recursion}} rainfall ({{list_name}} : {{list_type}} list) : {{return_type}} =
    {% if helper_in_body %}
        {{helper_body}} in 
    {% else %}
        {{helper_name}} {{list_name}} 0 0);;
'''

    return self.format(template, 
        helper_body=SingleLoopHelper(helper_name=helper_name, 
            list_type=list_type, 
            return_type=return_type).render())


class InlineSingleLoop(Rule):
    def render(self):

    template = '''
let {{recursion}} rainfall ({{list_name}} : {{list_type}} list) : {{return_type}} =
    TODO: (Check students 114 and 116)
'''
    return self.format(template)


class SingleLoop(Rule):
    def render(self):
        inline = self.choice('inline', {True : 1, False : 1})

        if inline:
            return InlineSingleLoop().render()
        else:
            return DecomposedSingleLoop().render()


class Program(Rule):
    def render(self):
        strategy = self.choice('strategy', {
            Labels.SingleLoop: 1,
            Labels.CleanFirst: 1,
            Labels.CleanInSC: 1,
        })

        self.set_label(int(strategy))

        if strategy == Labels.SingleLoop:
            return SingleLoop().render()
        elif strategy == Labels.CleanFirst:
            return CleanFirst().render()
        elif strategy == Labels.CleanInSC:
            return CleanInSC().render()