from autoplan.grammar import Rule
from .labels import GeneralRainfallLabels

Labels = GeneralRainfallLabels

class CleanFirst(Rule):
    def render(self):
        recursion = self.choice('recursion', {'' : 1, 'rec' : 1})
        parameter_specs = self.choice('parameter_specs', {'list_name_only' : 1, 'list_name_and_type' : 1})
        _type = self.choice('_type', {'int': 1, 'float': 1})
        helper_in_body = self.choice('helper_in_body', {True: 1, False: 1})

        template = '''
{%- set params -%}
    {%- if parameter_specs == 'list_name_only' -%}
        list_name = 
    {%- else -%}
        (list_name : {{_type}} list) : {{_type}} =
    {%- endif -%}
{%- endset -%}

{%- set helper_body -%}
let {{recursion}} helper_name (list_name : {{_type}} list) : {{_type}} list =
    match list_name with
    | [] -> []
    | head :: tail -> if head = -999 then []
    | head :: tail -> if head < 0 then helper_name tail
        else when head >= 0 then head :: {{addition_helper_name}} tail;;
{%- endset -%}

{%- set rainfall_body -%} {# ADD: failwith "No rain was collected" #}
    if (List.length (helper_name list_name) = 0) then 0 else
    (List.fold_right (+) helper_name list_name 0) / List.length (helper_name list_name);;
{%- endset -%}

{%- if not helper_in_body -%}
    {{helper_body}}
{%- endif -%}

let {{recursion}} rainfall {{params}}
    {%- if helper_in_body -%} {# helper body + rainfall body #}
    {{helper_body}} in 
    {{rainfall_body}}
    {% else -%} {# rainfall body for out of body helpers #}
    {{rainfall_body}}
    {% endif -%}     
'''
        params = '''
        '''
        helper_body = '''
        '''
        rainfall_body = '''
        '''

        return self.format(template, 
            recursion=recursion,
            parameter_specs=parameter_specs,
            _type=type, helper_in_body=helper_in_body,
            params=params)

class CleanInSC(Rule):
    def render(self):
        recursion = self.choice('recursion', {'' : 1, 'rec' : 1})
        parameter_specs = self.choice('parameter_specs', {'list_name_only' : 1, 'list_name_and_type' : 1})
        _type = self.choice('_type', {'int': 1, 'float': 1})
        fail_message = self.choice('fail_message', {'\"invalid input (ocaml needed this wildcard for some reason)\"' : 1, '\"The list does not have final value -999\"' : 1, '\"No data of interest\"' : 1, '\"Please input a list with at least one non-negative value before the first instance of -999.\"' : 1})
        separate_sentinel_check = self.choice('separate_sentinel_check', {True: 1, False : 1})
        check_div_by_zero = self.choice('check_div_by_zero', {True: 1, False: 1})
        helpers_in_body = self.choice('helpers_in_body', {True: 1, False: 1})
        anonymous_helpers = self.choice('anonymous_helpers', {True: 1, False: 1})
        raises_failwith = self.choice('raises_failwith', {True : 1, False : 1})

        template = '''
{%- set dot -%}
    {%- if _type == 'int' -%} {# empty string #}
    {%- else -%}
        .
    {%- endif -%}
{%- endset -%}

{%- set params -%}
    {%- if parameter_specs == 'list_name_only' -%}
        list_name = 
    {%- else -%}
        (list_name : {{_type}} list) : {{_type}} =
    {%- endif -%}
{%- endset -%}

{%- set rainfall_body -%}
    {%- if not check_div_by_zero -%}
        (addition_helper_name list_name) /{{dot}} (counter_helper_name list_name);;
    {%- else -%}
        if counter_helper_name = 0{{dot}} then 0{{dot}} else 
        (addition_helper_name list_name) /{{dot}} (counter_helper_name list_name);;
        
        {# TODO: Consider adding this optional syntax: 
        (rainfall_sum_helper alon) / (if ( 0 <= (rainfall_length_helper alon)) 
            then (rainfall_length_helper alon)  
            else failwith "cannot divide by zero!");;
        #}
    {%- endif -%}
{%- endset -%}

{%- set failure -%}
    {%- if raises_failwith -%}
        failwith {{fail_message}}
    {%- else -%}
        0{{dot}}
    {%- endif -%}
{%- endset -%}

{%- set addition_helper -%}
let {{recursion}} addition_helper_name {{params}}
    match list_name with
    | [] -> {{failure}}
    {% if separate_sentinel_check -%}
    | -999 :: tail -> {{failure}}
    | head :: tail -> if head < 0 then addition_helper_name tail
        else when head >= 0 then head +{{dot}} addition_helper_name tail;;
    {% else -%}
    | head :: tail -> if head = -999{{dot}} then {{failure}}
        else head +{{dot}} counter_helper_name tail;;
    {% endif -%}
{%- endset -%}

{%- set counter_helper -%}
let {{recursion}} counter_helper_name {{params}}
    match list_name with
    | [] -> {{failure}}
    {%- if separate_sentinel_check -%}
    | -999 :: tail -> {{failure}}
    | head :: tail -> if head < 0 then counter_helper_name tail
        else when head >= 0 then 1 +{{dot}} counter_helper_name tail;;
    {%- else -%}
    | head :: tail -> if head = -999{{dot}} then {{failure}}
        else 1 +{{dot}} counter_helper_name tail;;
    {%- endif -%}
{%- endset -%}

{% if not anonymous_helpers and not helpers_in_body -%}
{{addition_helper}}
{{counter_helper}} \n
{% endif -%}

let {{recursion}} rainfall {{params}}
    {% if not anonymous_helpers and helpers_in_body -%}
    {{addition_helper}}  
    in {{counter_helper}} 

    {# TODO: Consider adding these structures: 
    in match alon with
    | [] -> failwith "The list does not have final value -999" 
    | hd::tl -> if hd=(-999)
        then 0 
        else(rainfall_helper alon) / (counter alon);; #} 

    {# in sumlist (selector alon)) / (let l = (List.length (selector alon)) in
                                (if l = 0 then failwith "No data of interest"
                                 else l))));; #} 

    {% elif anonymous_helpers -%} 
    // anonymous_helpers // {# TODO: anonymous helpers in body, file: 73.ml #} 
    {% endif -%}

    {% if not anonymous_helpers and not helpers_in_body -%}
    {{rainfall_body}}
    {% endif -%}
'''
        dot = '''
        '''
        params = '''
        '''
        rainfall_body = '''
        '''
        failure = '''
        '''
        counter_helper = '''
        '''
        addition_helper = '''
        '''

        return self.format(template, 
            recursion=recursion,
            parameter_specs=parameter_specs,
            _type=_type,
            check_div_by_zero=check_div_by_zero,
            helpers_in_body=helpers_in_body,
            anonymous_helpers=anonymous_helpers,
            dot=dot, params=params,
            rainfall_body=rainfall_body,
            raises_failwith=raises_failwith,
            fail_message=fail_message, 
            failure=failure,
            separate_sentinel_check=separate_sentinel_check,
            counter_helper=counter_helper,
            addition_helper=addition_helper)

class SingleLoopHelper(Rule):
    def render(self):
        recursion = self.choice('recursion', {'' : 1, 'rec' : 1})
        fail_message = self.choice('fail_message', {'\"No data input.\"' : 1, '\"No rainfall\"' : 1})
        parameter_specs = self.choice('parameter_specs', {'vars_only': 1, 'vars_and_type': 1})
        if_statement = self.choice('if_statement', {'if' : 1, 'when' : 1}) 
        then_statement = self.choice('then_statement', {'then' : 1, '->' : 1}) 
        check_div_by_zero = self.choice('check_div_by_zero', {True: 1, False: 1})
        gt_zero = self.choice('gt_zero', {True : 1, False : 1}) # Else student uses '= 0'
        raises_failwith = self.choice('raises_failwith', {True : 1, False : 1})
        separate_sentinel_check = self.choice('separate_sentinel_check', {True: 1, False : 1})
        recurse_empty_list = self.choice('recurse_empty_list', {True: 1, False : 1})
        check_positive_head = self.choice('check_positive_head', {True: 1, False : 1})

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
        0{{dot}}
    {%- endif -%}
{%- endset -%}

{%- set return_average -%}
    {%- if check_div_by_zero -%} 
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
        helper_name [] {{addition}} {{counter}}
    {%- else -%}
        {{if_statement}} head = -999 {{then_statement}} {{return_average}}
    {%- endif -%}
{%- endset -%}

{%- set include_head -%}
    helper_name tail (head + {{addition}}) ({{counter}} + 1)
{%- endset -%}

{%- set exclude_head -%}
    helper_name tail {{addition}} {{counter}}
{%- endset -%}

{%- set recurse -%}
    {%- if check_positive_head -%}
        {{if_statement}} head >= 0 {{then_statement}} {{include_head}} else {{exclude_head}}
    {%- else -%}
        {{include_head}}
    {%- endif -%}
{%- endset -%}

{%- set params -%}
    {%- if parameter_specs == 'vars_only' -%}
        list_name {{addition}} {{counter}} = 
    {%- else -%} {# 'vars_and_type' #}
        (list_name : {{_type}} list) ({{addition}} : {{_type}}) ({{counter}} : {{_type}})  : {{_type}} =
    {% endif %} 
{%- endset -%}

let {{recursion}} helper_name {{params}}
    match list_name with
    | [] -> {{return_average}}
    | head :: tail -> {{end_recursion}}
    | head :: tail -> {{recurse}}

{# TODO: Consider adding more options in the helper body, 
using separate_sentinel_check. #}
'''

        params = '''
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
            _type=self.params['_type'],
            dot=self.params['dot'],
            addition=self.params['addition'], 
            counter=self.params['counter'],
            failure=failure, 
            average=average, 
            fail_message=fail_message,
            raises_failwith=raises_failwith,
            return_average=return_average,
            end_recursion=end_recursion,
            include_head=include_head,
            exclude_head=exclude_head,
            check_div_by_zero=check_div_by_zero,
            gt_zero=gt_zero,
            separate_sentinel_check=separate_sentinel_check,
            recurse_empty_list=recurse_empty_list,
            check_positive_head=check_positive_head,
            if_statement=if_statement,
            then_statement=then_statement,
            params=params)


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
        list_name = 
    {%- else -%}
        (list_name : {{_type}} list) : {{_type}} =
    {%- endif -%}
{%- endset -%}

{%- set rainfall_body -%}
    {%- if rainfall_body_specs == 'direct_pass' -%}
        helper_name list_name 0{{dot}} 0{{dot}};;
    {%- elif recursion_strategy == 'match' -%} {# recurse #}
        | {{check_empty_list}} -> {{failure}}
        | _ -> helper_name list_name 0{{dot}} 0{{dot}};;
    {%- elif recursion_strategy == 'let' -%}
        let ({{addition}}, {{counter}}) = helper_name list_name 0{{dot}} 0{{dot}} in 
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
        {{helper_body}} 
        in helper_name list_name 0{{dot}} 0{{dot}};;
    {% else -%} 
        {{rainfall_body}}
    {% endif -%}

{# TODO: Consider adding these possibilities in the end line of the in-body helper:

a) in (let (x, inc) = rainfall_helper alon in (if inc = 0
                                              then failwith "failed to find valid measurements" 
                                              else x /. (float inc))) ;;

b) in match sum_helper alof 0. 0. with
    | (s, c) -> (s /. c) ;; 
#}
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
            helper_body=SingleLoopHelper(_type=_type, dot=dot, 
                addition=addition, counter=counter).render())

class Program(Rule):
    def render(self):
        strategy = self.choice('strategy', {
            Labels.SingleLoop: 1,
            Labels.CleanFirst: 1,
            Labels.CleanInSC: 1
        })

        self.set_label(int(strategy))

        if strategy == Labels.SingleLoop:
            return SingleLoop().render()
        if strategy == Labels.CleanFirst:
            return CleanFirst().render()
        elif strategy == Labels.CleanInSC:
            return CleanInSC().render()