from autoplan.grammar import Rule
from .labels import GeneralRainfallLabels

Labels = GeneralRainfallLabels

class CleanFirst(Rule):
    raise NotImplementedError

class CleanInSC(Rule):
    raise NotImplementedError

class SingleLoopHelper(Rule):
    def render(self):
        _type = self.params['_type']
        recursion = self.choice('recursion', {'' : 1, 'rec' : 1})
        list_name = self.choice('list_name', {'alon2': 1, 'lon': 1})
        fail_message = self.choice('fail_message', {'\"No data input.\"' : 1, '\"No rainfall\"' : 1})
        head = self.choice('head', {'head' : 1, 'hd' : 1}) 
        tail = self.choice('tail', {'tail' : 1, 'tl' : 1, '_' : 1})
        div_by_zero = self.choice('div_by_zero', {True: 1, False: 1})
        gt_zero = self.choice('gt_zero', {True : 1, False : 1}) # Else student uses '= 0'
        raises_failwith = self.choice('raises_failwith', {True : 1, False : 1})
        separate_sentinel_check = self.choice('separate_sentinel_check', {True: 1, False : 1})
        recurse_empty_list = self.choice('recurse_empty_list', {True: 1, False : 1})
        check_positive_head = self.choice('check_positive_head', {True: 1, False : 1})
        if_statement = self.choice('if_statement', {'if' : 1, 'when' : 1}) 
        then_statement = self.choice('then_statement', {'then' : 1, '->' : 1}) 

        template = '''
{%- set average -%}
    {%- if _type == 'int' -%} 
        {{addition}} / {{counter}}
    {%- else -%} 
        {{addition}} /. {{counter}}
    {%- endif -%}
{%- endset -%}

{%- set failure -%}
    {%- if raises_failwith -%}
        failwith {{fail_message}}
    {%- else -%}
        {%- if _type == 'int' -%} 
            0
        {%- else -%} 
            0.
        {%- endif -%}
    {%- endif -%}
{%- endset -%}

{%- set return_average -%}
    {%- if div_by_zero -%} 
        {%- if gt_zero -%}
            if {{counter}} > 0 then {{average}} else {{failure}}
        {%- else -%} 
            if {{counter}} = 0 then {{failure}} else {{average}}
        {%- endif -%}
    {%- else -%} 
        {{average}}
    {%- endif -%}
{%- endset -%}

{%- set end_recursion -%}
    {%- if recurse_empty_list -%}
        {{helper_name}} [] {{addition}} {{counter}}
    {%- else -%}
        {{if_statement}} {{head}} = -999 {{then_statement}} {{return_average}}
    {%- endif -%}
{%- endset -%}

{%- set include_head -%}
    {{helper_name}} {{tail}} ({{head}} + {{addition}}) ({{counter}} + 1)
{%- endset -%}

{%- set exclude_head -%}
    {{helper_name}} {{tail}} {{addition}} {{counter}}
{%- endset -%}

{%- set recurse -%}
    {%- if check_positive_head -%}
        {{if_statement}} {{head}} >= 0 {{then_statement}} {{include_head}} else {{exclude_head}}
    {%- else -%}
        {{include_head}}
    {%- endif -%}
{%- endset -%}

let {{recursion}} {{helper_name}} ({{list_name}} : {{_type}} list) ({{addition}} : {{_type}}) ({{counter}} : {{_type}}) : {{_type}} =
    match {{list_name}} with
    | [] -> {{return_average}}
    | {{head}} :: {{tail}} -> {{end_recursion}}
    | {{head}} :: {{tail}} -> {{recurse}}

{# TODO:
# {{EXTRA_PARAMS}} #}
'''

        return_average = '''
        '''
        average = '''
        '''
        failure = '''
        '''
        end_recursion = '''
        '''
        recurse = '''
        '''
        include_head = '''
        '''
        exclude_head = '''
        '''

        return self.format(template, 
            helper_name=self.params['helper_name'], 
            _type=self.params['_type'],
            dot=self.params['dot'],
            average=average, 
            failure=self.params['failure'], 
            addition=self.params['addition'], 
            counter=self.params['counter'],
            fail_message=fail_message,
            raises_failwith=raises_failwith,
            return_average=return_average,
            end_recursion=end_recursion,
            include_head=include_head,
            exclude_head=exclude_head,
            list_name=list_name,
            head=head,
            tail=tail,
            div_by_zero=div_by_zero,
            gt_zero=gt_zero,
            separate_sentinel_check=separate_sentinel_check,
            recurse_empty_list=recurse_empty_list,
            check_positive_head=check_positive_head,
            if_statement=if_statement,
            then_statement=then_statement)


class SingleLoop(Rule):
    def render(self):
        recursion = self.choice('recursion', {'' : 1, 'rec' : 1})
        parameter_specs = self.choice('parameter_specs', {'list_name_only' : 1, 'list_name_and_type' : 1})
        rainfall_body_specs = self.choice('rainfall_body_specs', {'direct_pass': 1, 'recurse': 1})
        recursion_strategy = self.choice('recursion_strategy', {'match' : 1, 'let' : 1})
        _type = self.choice('_type', {'int': 1, 'float': 1})
        check_empty_list = self.choice('check_empty_list', {'[]' : 1, '(0, 0)' : 1})
        addition = self.choice('addition', {'accumulator' : 1, 'acc' : 1, 'sum' : 1, 'total' : 1, 'n' : 1, 'avg' : 1, 'q_rain' : 1})
        counter = self.choice('counter', {'count' : 1, 'quantity' : 1, 'counter' : 1, 'num_processed' : 1, 'len' : 1, 'num' : 1, 'num_elements' : 1, 'size' : 1})
        fail_message = self.choice('fail_message', {'\"No rainfall\"' : 1, '\"Could not compute average rainfall; passed 0 data.\"' : 1, '\"Empty list.\"' : 1, '\"no rainfall value could be calculated\"' : 1, '\"error: no average\"' : 1})
        helper_name = self.choice('helper_name', {'_rainfall': 1, 'rainfall_helper': 1, 'rainfall_help': 1, 'sum_helper' : 1, 'rfhelp' : 1, 'avg_rain' : 1, 'r_help' : 1})
        list_name = self.choice('list_name', {'alof': 1, 'alon': 1, 'aloi': 1, 'rain_list': 1})
        helper_in_body = self.choice('helper_in_body', {True: 1, False: 1})
        raises_failwith = self.choice('raises_failwith', {True : 1, False : 1})
    
        template = '''
{%- set dot -%}
    {%- if _type == 'int' -%} {# empty string #}
    {%- else -%}
        .
    {%- endif -%}
{%- endset -%}

{%- set failure -%}
    {%- if raises_failwith -%}
        failwith {{fail_message}}
    {%- else -%}
        0{{dot}}
    {%- endif -%}
{%- endset -%}

{%- set params -%}
    {%- if parameter_specs == 'list_name_only' -%}
        {{list_name}} = 
    {%- else -%}
        ({{list_name}} : {{_type}} list) : {{_type}} =
    {%- endif -%}
{%- endset -%}

{%- set rainfall_body -%}
    {%- if rainfall_body_specs == 'direct_pass' -%}
        {{helper_name}} {{list_name}} 0{{dot}} 0{{dot}};;
    {%- elif recursion_strategy == 'match' -%} {# recurse #}
        | {{check_empty_list}} -> {{failure}}
        | _ -> {{helper_name}} {{list_name}} 0{{dot}} 0{{dot}};;
    {%- elif recursion_strategy == 'let' -%}
        let ({{addition}}, {{counter}}) = {{helper_name}} {{list_name}} 0{{dot}} 0{{dot}} in 
        if {{counter}} = 0{{dot}} then failwith {{fail_message}}
        else ({{addition}} /{{dot}} {{counter}});;
    {%- else -%}
        | {{check_empty_list}} -> {{failure}}
        | ({{addition}}, {{counter}}) -> {{addition}} /{{dot}} {{counter}}
    {%- endif -%}
{%- endset -%}

{%- if not helper_in_body -%}
    {{helper_body}};;
{%- endif %}

let {{recursion}} rainfall {{params}}
    {% if helper_in_body -%}
        {{helper_body}} in 
        {{helper_name}} {{list_name}} 0{{dot}} 0{{dot}};;
    {% else -%} 
        {{rainfall_body}}
    {% endif -%}
'''

        dot = '''
        '''
        failure = '''
        '''
        params = '''
        '''
        rainfall_body = '''
        '''

        return self.format(template,
            recursion=recursion,
            params=params,
            helper_in_body=helper_in_body,
            helper_name=helper_name,
            list_name=list_name,
            dot=dot,
            _type=_type,
            failure=failure,
            rainfall_body=rainfall_body,
            recursion_strategy=recursion_strategy,
            addition=addition,
            counter=counter,
            fail_message=fail_message,
            check_empty_list=check_empty_list,
            raises_failwith=raises_failwith,
            parameter_specs=parameter_specs,
            rainfall_body_specs=rainfall_body_specs, 
            helper_body=SingleLoopHelper(helper_name=helper_name, _type=_type, dot=dot,
                                        failure=failure, addition=addition, counter=counter).render())

class Program(Rule):
    def render(self):
        strategy = self.choice('strategy', {
            Labels.SingleLoop: 1
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