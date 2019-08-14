from autoplan.grammar import Rule
from .labels import GeneralRainfallLabels

Labels = GeneralRainfallLabels

class CleanFirst(Rule):
    def render(self):
        recursion = self.choice('recursion', {'' : 1, 'rec' : 1})
        uses_annotation = self.choice('uses_annotation', {True: 1, False: 1})
        _type = self.choice('_type', {'int': 1, 'float': 1})
        helper_in_body = self.choice('helper_in_body', {True: 1, False: 1})
        raises_failwith = self.choice('raises_failwith', {True: 1, False: 1})
        fail_message = self.choice('fail_message', {'\"No rain was collected\"' : 1})

        template = '''
{%- set params -%}
    {%- if uses_annotation -%}
        (list_name : {{_type}} list) : {{_type}} =
    {%- else -%}
        list_name = 
    {%- endif -%}
{%- endset -%}

{%- set failure -%}
    {%- if raises_failwith -%}
        failwith {{fail_message}}
    {%- else -%}
        0{{dot}}
    {%- endif -%}
{%- endset -%}

{%- set helper_body -%}
let {{recursion}} helper_name (list_name : {{_type}} list) : {{_type}} list =
    match list_name with
    | [] -> []
    | head :: tail when head = -999 -> []
    | head :: tail when head < 0{{dot}} -> helper_name tail
    | head :: tail when head >= 0{{dot}} -> head :: addition_helper_name tail 
{% endset -%}

{%- set rainfall_body -%} 
    if (List.length (helper_name list_name) = 0{{dot}}) then {{failure}} else
    (List.fold_right (+) helper_name list_name 0{{dot}}) /{{dot}} List.length (helper_name list_name)
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

        return self.format(template, 
            recursion=recursion,
            uses_annotation=uses_annotation,
            _type=_type, helper_in_body=helper_in_body,
            raises_failwith=raises_failwith,
            fail_message=fail_message,
            dot='' if _type == 'int' else '.')

class CleanInSC(Rule):
    def render(self):
        recursion = self.choice('recursion', {'' : 1, 'rec' : 1})
        uses_annotation = self.choice('uses_annotation', {True : 1, False: 1})
        _type = self.choice('_type', {'int': 1, 'float': 1})
        fail_message = self.choice('fail_message', {'\"invalid input (ocaml needed this wildcard for some reason)\"' : 1, '\"The list does not have final value -999\"' : 1, '\"No data of interest\"' : 1, '\"Please input a list with at least one non-negative value before the first instance of -999.\"' : 1, '\"cannot divide by zero!!\"' : 1})
        separate_sentinel_check = self.choice('separate_sentinel_check', {True: 1, False : 1})
        check_div_by_zero = self.choice('check_div_by_zero', {True: 1, False: 1})
        check_counter_val = self.choice('check_counter_val', {True: 1, False: 1})
        helpers_in_body = self.choice('helpers_in_body', {True: 1, False: 1})
        anonymous_helpers = self.choice('anonymous_helpers', {True: 1, False: 1})
        raises_failwith = self.choice('raises_failwith', {True : 1, False : 1})

        template = '''
{%- set params -%}
    {%- if uses_annotation -%}
        (list_name : {{_type}} list) : {{_type}} =
    {%- else -%}
        list_name = 
    {%- endif -%}
{%- endset -%}

{%- set failure -%}
    {%- if raises_failwith -%}
        failwith {{fail_message}}
    {%- else -%}
        0{{dot}}
    {%- endif -%}
{%- endset -%}

{%- set rainfall_body -%}
    {%- if not check_div_by_zero -%}
        (addition_helper_name list_name) /{{dot}} (counter_helper_name list_name)
    {%- else -%}
        {%- if check_counter_val -%}
        if counter_helper_name = 0{{dot}} then {{failure}} else 
        (addition_helper_name list_name) /{{dot}} (counter_helper_name list_name)
        {%- else -%}
        (addition_helper_name list_name) /{{dot}} (if (0{{dot}} <= (counter_helper_name list_name)) 
            then (counter_helper_name list_name)  
            else {{failure}})
        {%- endif -%}
    {%- endif -%}
{%- endset -%}

{%- set addition_helper -%}
let {{recursion}} addition_helper_name {{params}}
    match list_name with
    | [] -> {{failure}}
    {% if separate_sentinel_check -%}
    | -999 :: tail -> {{failure}}
    | head :: tail -> if head < 0{{dot}} then addition_helper_name tail
        else head +{{dot}} addition_helper_name tail 
    {% else -%}
    | head :: tail -> if head = -999{{dot}} then {{failure}}
        else head +{{dot}} counter_helper_name tail
    {% endif -%}
{%- endset -%}

{%- set counter_helper -%}
let {{recursion}} counter_helper_name {{params}}
    match list_name with
    | [] -> {{failure}}
    {%- if separate_sentinel_check -%}
    | -999 :: tail -> {{failure}}
    | head :: tail -> if head < 0{{dot}} then counter_helper_name tail
        else 1 +{{dot}} counter_helper_name tail 
    {%- else -%}
    | head :: tail -> if head = -999{{dot}} then {{failure}}
        else 1 +{{dot}} counter_helper_name tail
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
    in {{rainfall_body}}

    {% elif anonymous_helpers -%} {# File 73.ml #}
    (try ((List.fold_right 
    (fun var var -> (if (var = (-999)) then {{failure}} else if (var < 0) then var else (var + var))) list_name 0) /{{dot}} (List.fold_right 
        (fun var var -> (if (var = (-999)) then {{failure}} else if (var < 0) then var else (1 + var))) list_name 0)) with division_by_zero_helper_name 
        -> {{failure}})
    {% endif -%}

    {% if not anonymous_helpers and not helpers_in_body -%}
    {{rainfall_body}}
    {% endif -%}
'''

        return self.format(template, 
            recursion=recursion,
            uses_annotation=uses_annotation,
            _type=_type,
            check_div_by_zero=check_div_by_zero,
            helpers_in_body=helpers_in_body,
            anonymous_helpers=anonymous_helpers,
            raises_failwith=raises_failwith,
            fail_message=fail_message, 
            separate_sentinel_check=separate_sentinel_check,
            dot='' if _type == 'int' else '.')

class SingleLoopHelper(Rule):
    def render(self):
        _type = self.params['_type']
        recursion = self.choice('recursion', {'' : 1, 'rec' : 1})
        fail_message = self.choice('fail_message', {'\"No data input.\"' : 1, '\"No rainfall\"' : 1})
        uses_annotation = self.choice('uses_annotation', {True: 1, False: 1})
        # if_statement = self.choice('if_statement', {'if' : 1, 'when' : 1}) 
        check_div_by_zero = self.choice('check_div_by_zero', {True: 1, False: 1})
        gt_zero = self.choice('gt_zero', {True : 1, False : 1}) # Else student uses '= 0'
        raises_failwith = self.choice('raises_failwith', {True : 1, False : 1})
        separate_sentinel_check = self.choice('separate_sentinel_check', {True: 1, False : 1})
        recurse_empty_list = self.choice('recurse_empty_list', {True: 1, False : 1})
        check_positive_head = self.choice('check_positive_head', {True: 1, False : 1})

        template = '''
{%- set average -%}
    {%- if _type == 'int' -%} 
        addition_var / counter_var
    {%- else -%} 
        addition_var /. counter_var
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
            if counter_var > 0{{dot}} then {{average}} else {{failure}}
        {%- else -%} 
            if counter_var = 0{{dot}} then {{failure}} else {{average}}
        {%- endif -%}
    {%- else -%} 
        {{average}}
    {%- endif -%}
{%- endset -%}

{%- set end_recursion -%}
    {%- if recurse_empty_list -%}
        -> helper_name [] addition_var counter_var
    {%- else -%}
        when head = -999 -> {{return_average}}
    {%- endif -%}
{%- endset -%}

{%- set include_head -%}
    helper_name tail (head + addition_var) (counter_var + 1)
{%- endset -%}

{%- set exclude_head -%}
    helper_name tail addition_var counter_var
{%- endset -%}

{%- set recurse -%}
    {%- if check_positive_head -%}
        if head >= 0{{dot}} then {{include_head}} else {{exclude_head}}
    {%- else -%}
        {{include_head}}
    {%- endif -%}
{%- endset -%}

{%- set params -%}
    {%- if uses_annotation -%}
        (list_name : {{_type}} list) (addition_var : {{_type}}) (counter_var : {{_type}})  : {{_type}} =
    {%- else -%} {# 'vars_and_type' #}
        list_name addition_var counter_var =  
    {% endif %} 
{%- endset -%}

let {{recursion}} helper_name {{params}}
    match list_name with
    | [] -> {{return_average}}
    | head :: tail {{end_recursion}}
    | head :: tail -> {{recurse}}

{# TODO: Consider adding more options in the helper body, 
using separate_sentinel_check. #}
'''

        return self.format(template, 
            _type=_type,
            fail_message=fail_message,
            raises_failwith=raises_failwith,
            check_div_by_zero=check_div_by_zero,
            gt_zero=gt_zero,
            separate_sentinel_check=separate_sentinel_check,
            recurse_empty_list=recurse_empty_list,
            check_positive_head=check_positive_head,
            uses_annotation=uses_annotation,
            dot='' if _type == 'int' else '.')


class SingleLoop(Rule):
    def render(self):
        recursion = self.choice('recursion', {'' : 1, 'rec' : 1})
        uses_annotation = self.choice('uses_annotation', {True : 1, False: 1})
        rainfall_body_specs = self.choice('rainfall_body_specs', {'direct_pass': 1, 'recurse': 1})
        recursion_strategy = self.choice('recursion_strategy', {'match' : 1, 'let' : 1})
        _type = self.choice('_type', {'int': 1, 'float': 1})
        check_empty_list = self.choice('check_empty_list', {'[]' : 1, '(0, 0)' : 1})
        fail_message = self.choice('fail_message', {'\"No rainfall\"' : 1, '\"Could not compute average rainfall; passed 0 data.\"' : 1, '\"Empty list.\"' : 1, '\"no rainfall value could be calculated\"' : 1, '\"error: no average\"' : 1})
        helper_in_body = self.choice('helper_in_body', {True: 1, False: 1})
        raises_failwith = self.choice('raises_failwith', {True : 1, False : 1})
    
        template = '''
{%- set failure -%}
    {%- if raises_failwith -%}
        failwith {{fail_message}}
    {%- else -%}
        0{{dot}}
    {%- endif -%}
{%- endset -%}

{%- set params -%}
    {%- if uses_annotation -%}
        (list_name : {{_type}} list) : {{_type}} =
    {%- else -%}
        list_name = 
    {%- endif -%}
{%- endset -%}

{%- set rainfall_body -%}
    {%- if rainfall_body_specs == 'direct_pass' -%}
        helper_name list_name 0{{dot}} 0{{dot}}
    {%- elif recursion_strategy == 'match' -%} {# recurse #}
        match list_name with
        | {{check_empty_list}} -> {{failure}}
        | _ -> helper_name list_name 0{{dot}} 0{{dot}}
    {%- elif recursion_strategy == 'let' -%}
        let (addition_var, counter_var) = helper_name list_name 0{{dot}} 0{{dot}} in 
        if counter_var = 0{{dot}} then {{failure}}
        else (addition_var /{{dot}} counter_var)
    {%- else -%}
        match list_name with
        | {{check_empty_list}} -> {{failure}}
        | (addition_var, counter_var) -> addition_var /{{dot}} counter_var
    {%- endif -%}
{%- endset -%}

{%- if not helper_in_body -%}
    {{helper_body}}
{%- endif %}

let {{recursion}} rainfall {{params}}
    {% if helper_in_body -%}
        {{helper_body}} 
        in {{rainfall_body}}
    {% else -%} 
        {{rainfall_body}}
    {% endif -%}
'''

        return self.format(template,
            recursion=recursion,
            helper_in_body=helper_in_body,
            _type=_type,
            recursion_strategy=recursion_strategy,
            fail_message=fail_message,
            check_empty_list=check_empty_list,
            raises_failwith=raises_failwith,
            uses_annotation=uses_annotation,
            rainfall_body_specs=rainfall_body_specs, 
            helper_body=SingleLoopHelper(_type=_type).render(),
            dot='' if _type == 'int' else '.')

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
