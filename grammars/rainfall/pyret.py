from autoplan.grammar import Rule
from .labels import GeneralRainfallLabels

Labels = GeneralRainfallLabels

'''
TODO: 
- Merge SumHelper and CounterHelper into one function 
and use params for head vs 1, sum vs count

- Add 'direct' syntax to all CleanFirstHelpers (only 'match' now), file 141
'''

class SingleLoopHelper(Rule):
    def render(self):
        check_div_by_zero = self.params['check_div_by_zero']
        where_check_div_by_zero = self.params['where_check_div_by_zero']
        record_or_params = self.choice('record_or_params', {'record': 1, 'params': 1})
        sentinel_recurse = self.choice('sentinel_recurse', {True: 1, False: 1})
        gt_zero = self.choice('gt_zero', {True: 1, False: 1})
        
        template = '''
{%- if record_or_params == 'record' -%} {# File 108 #}
    fun helper(nums :: List<Number>) -> {sum : Number, length : Number}:
        cases(List<Number>) nums:
        | empty => {sum: 0, length: 0}
        | link(head, tail) =>
            if head == -999:
                {sum: 0, length: 0}
            else if head < 0:
                vals = helper(tail)
                {sum : vals.sum, length : vals.length}
            else:
                vals = helper(tail)
                {sum: vals.sum + head, length: vals.length + 1}
            end
        end
    end
{%- else -%}
    fun helper(nums :: List<Number>, sum :: Number, length :: Number) -> Number:
        cases(List<Number>) nums:
        | empty =>
            {%- if check_div_by_zero-%}
                {%- if where_check_div_by_zero == 'helper' -%}
                    if length == 0:
                        {{ failure }} \n
                    else:
                        sum / length
                    end
                {% endif -%}
            {%- else -%}
            sum / length
            {% endif -%}
        | link(head, tail) =>
            if head == -999:
                {%- if sentinel_recurse -%}
                helper([], sum, length)
                {%- else -%}
                sum / length
                {% endif -%}
                
            {%- if gt_zero -%}
                else if head > 0:
                    helper(tail, sum + head, length + 1)
                else:
                    helper(tail, sum, length)
                end
            {% else -%}
                else if head < 0:
                    helper(tail, sum, length)
                else:
                    helper(tail, sum + head, length + 1)
                end
            {% endif -%}
        end
    end
{%- endif -%}
'''
    
        return self.format(
            template, gt_zero=gt_zero,
            record_or_params=record_or_params,
            sentinel_recurse=sentinel_recurse)


class SingleLoop(Rule):
    def render(self):
        check_div_by_zero = self.choice('check_div_by_zero', {True: 1, False: 1})
        where_check_div_by_zero = self.choice('where_check_div_by_zero', {'main' : 1, 'helper': 1})
        helper = SingleLoopHelper(check_div_by_zero=check_div_by_zero,
                            where_check_div_by_zero=where_check_div_by_zero).render()
        helper_in_body = self.choice('helper_in_body', {True: 1, False: 1})
        error_strategy = self.choice('error_strategy', {'exception': 1, 'zero': 1})
        return_logic_structure = self.choice('return_logic_structure', {'direct': 1, 'match': 1})
        
        template = '''
{%- set failure -%}
    {%- if error_strategy == 'exception' -%}
        raise(error)
    {%- else -%}
        0
    {%- endif -%}
{%- endset -%}

{%- set return_logic -%}
    {%- if check_div_by_zero-%}
        {%- if where_check_div_by_zero == 'main' -%}
            {%- if return_logic_structure == 'direct'-%}
            vals = helper(nums, 0, 0)
            if vals.length == 0:
                {{ failure }} \n
            else:
                vals.sum / vals.length
            {%- else -%}
            cases(List) nums:
            | empty => {{ failure }} \n
            | link(head, tail) => 0 
                if head == -999: 
                    {{ failure }} \n
                else: 
                    helper(nums, 0, 0)
                end
            {%- endif -%}
        {%- else -%}
        helper(nums, 0, 0)
        {%- endif -%}
    {%- else -%}
    vals.sum / vals.length
    {%- endif -%}
{%- endset -%}

{%- if helper_in_body -%}
    fun rainfall(nums :: List<Number>) -> Number:
        {{ helper }}
        {{ return_logic }}
    end
{%- else -%}
    fun rainfall(nums :: List<Number>) -> Number:
        {# rainfall_body, file 129 #}
        {{ return_logic }}
    end

    {{ helper }}
{%- endif -%}
'''

        return self.format(template, 
            helper=helper,
            check_div_by_zero=check_div_by_zero,
            where_check_div_by_zero=where_check_div_by_zero,
            return_logic_structure=return_logic_structure)


class SumHelper(Rule):
    def render(self):
        uses_annotation = self.params['uses_annotation']
        recurse_strategy = self.params['recurse_strategy']

        template = ''' 
{%- set recurse -%}
    {%- if recurse_strategy == 'addition' -%}
        head + sum_helper(tail)
    {%- else -%}
        link(head, sum_helper(tail))
    {%- endif -%}
{%- endset -%}

fun sum_helper(nums :: List{{ annotation }}) -> Number:
    cases(List{{ annotation }}) nums:
    | empty => 0
    | link(head, tail) => 
        if head == -999:
            0
        else:
            {{recurse}} \n
        end
    end
end \n'''
        return self.format(template, 
            recurse_strategy=recurse_strategy,
            uses_annotation=uses_annotation,
            annotation = '<Number>' if uses_annotation else '')


class CounterHelper(Rule):
    def render(self):
        uses_annotation = self.params['uses_annotation']
        recurse_strategy = self.params['recurse_strategy']

        template = '''
{%- set recurse -%}
    {%- if recurse_strategy == 'addition' -%}
        1 + counter_helper(tail) 
    {%- else -%}
        link(1, counter_helper(tail))
    {%- endif -%}
{%- endset -%}

fun counter_helper(nums :: List{{ annotation }}) -> Number:
    cases(List{{ annotation }}) nums:
    | empty => 0
    | link(head, tail) =>
        if head == -999:
            0
        else:
            {{recurse}} \n
        end
    end
end
'''
        return self.format(template, 
            recurse_strategy=recurse_strategy,
            uses_annotation=uses_annotation,
            annotation = '<Number>' if uses_annotation else '')

class CleanOnly(Rule):
    def render(self):
        uses_annotation = self.params['uses_annotation']
        error_strategy = self.params['error_strategy']
        return_empty = self.params['return_empty']
        recurse_strategy = self.params['recurse_strategy']

        template = '''
{%- set failure -%}
    {%- if error_strategy == 'exception' -%}
        raise(error)
    {%- elif error_strategy == 'zero' -%}
        0
    {%- elif return_empty -%}
        empty
    {%- else -%}
        []
    {%- endif -%}
{%- endset -%}

{%- set recurse -%}
    {%- if recurse_strategy == 'addition' -%}
        head + clean_helper(tail) 
    {%- else -%}
        link(head, clean_helper(tail))
    {%- endif -%}
{%- endset -%}

fun clean_helper(nums :: List{{ annotation }}) -> List{{ annotation }}:
    cases(List{{ annotation }}) nums:
    | empty => {{ failure }} \n
    | link(head, tail) =>
        if head == -999:
            {{ failure }} \n
        else if head < 0:
            clean_helper(tail)
        else:
            {{ recurse }} \n
        end
    end
end \n'''

        return self.format(template,
            error_strategy=error_strategy,
            return_empty=return_empty, 
            recurse_strategy=recurse_strategy,
            annotation= '<Number>' if uses_annotation else '')


class CleanSumCounter(Rule):
    def render(self):
        helper_logic = self.params['helper_logic']
        error_strategy = self.params['error_strategy']
        return_empty = self.params['return_empty']
        recurse_strategy = self.params['recurse_strategy']
        clean_function = CleanOnly(**self.params).render()
        sum_function = SumHelper(**self.params).render()
        counter_function = CounterHelper(**self.params).render()

        template = '''
{{ clean_function }} \n

{{ sum_function }} \n

{%- if helper_logic == 'clean_sum_counter' -%}
{{ counter_function }}
{%- endif -%}
'''
        return self.format(template,
            clean_function=clean_function,
            sum_function=sum_function,
            counter_function=counter_function,
            error_strategy=error_strategy,
            return_empty=return_empty, 
            recurse_strategy=recurse_strategy)


# File 155
class SentinelOnly(Rule):
    def render(self):
        error_strategy = self.params['error_strategy']
        return_empty = self.params['return_empty']
        recurse_strategy = self.params['recurse_strategy']

        template = '''
{%- set failure -%}
    {%- if error_strategy == 'exception' -%}
        raise(error)
    {%- elif return_empty -%}
        empty
    {%- else -%}
        []
    {%- endif -%}
{%- endset -%}

{%- set recurse -%}
    {%- if recurse_strategy == 'addition' -%}
        head + sentinel_only_helper(tail, x) 
    {%- else -%}
        link(head, sentinel_only_helper(tail, x))
    {%- endif -%}
{%- endset -%}

fun sentinel_only_helper(lst :: List{{ annotation }}, x :: Any) -> List{{ annotation }}:
    cases (List{{ annotation }}) lst:
    | empty => {{failure}} \n
    | link(head, tail) =>
        if head == x:
            {{failure}} \n
        else:
            {{recurse}} \n
        end
    end
end
'''
        return self.format(template,
            error_strategy=error_strategy,
            return_empty=return_empty, 
            recurse_strategy=recurse_strategy,
            annotation = '<Number>' if uses_annotation else '')


class CleanFirstHelper(Rule):
  def render(self):
    helper_logic = self.params['helper_logic']
    uses_annotation = self.params['uses_annotation']
    error_strategy = self.choice('error_strategy', {'exception': 1, 'zero': 1})
    recurse_strategy = self.choice('recurse_strategy', {'addition': 1, 'link' : 1})
    return_empty = self.choice('return_empty', {True: 1, False: 1})

    if helper_logic == 'clean_only':
        return CleanOnly(**self.params, 
            error_strategy=error_strategy,
            return_empty=return_empty,
            recurse_strategy=recurse_strategy).render()
    elif helper_logic == 'clean_sum_counter' or 'clean_sum':
        return CleanSumCounter(**self.params, 
            error_strategy=error_strategy,
            return_empty=return_empty,
            recurse_strategy=recurse_strategy).render()
    else:
        return SentinelOnly(**self.params, 
            error_strategy=error_strategy,
            return_empty=return_empty,
            recurse_strategy=recurse_strategy).render()

# Clean First always checks division by zero in main 
class CleanFirst(Rule):
    def render(self):
        helper_logic = self.choice('helper_logic', {'clean_only': 1, 'clean_sum': 1, 'clean_sum_counter': 1, 'sentinel_only': 1})
        uses_annotation = self.choice('uses_annotation', {True: 1, False: 1})
        helper_in_body = self.choice('helper_in_body', {True: 1, False: 1})
        check_div_by_zero = self.choice('check_div_by_zero', {True: 1, False: 1})
        checks_length = self.choice('checks_length', {True: 1, False: 1})
        return_logic_structure = self.choice('return_logic_structure', {'direct': 1, 'match': 1, 'else': 1})
        rare_solution = self.choice('rare_solution', {True: 1, False: 1})

        template = '''
{%- set return_logic -%}
    {%- if helper_logic == 'clean_only' -%}
        {%- if return_logic_structure == 'direct'-%}
            positive_nums = clean_helper(nums)
            {% if check_div_by_zero %}
            if positive_nums == []: 
                0
            else: 
                length = positive_nums.length()
                for fold(average from 0, elem from positive_nums):
                    average + (elem / length)
                end
            end 
            {%- else %}
            length = positive_nums.length()
            for fold(average from 0, elem from positive_nums):
                average + (elem / length)
            end
            {% endif -%}
        {%- elif return_logic_structure == 'match' -%} 
            positive_nums = clean_helper(nums)
            {% if anonymous_functions %}
            cases(List{{annotation}}) positive_nums:
            | empty => 0
            | link(head, tail) =>
                sum = positive_nums.foldr(fun(x, y): x + y;,0)
                average = sum / positive_nums.length()
                average
            end 
            {%- else %}
            cases (List{{annotation}}) clean_helper(nums):
            | empty => 0
            | link(head, tail) =>
                fold(head + tail, 0, clean_helper(nums))/clean_helper(nums).length()
            end
            {% endif -%}  
        {%- else %} {# rare solutions #}
            positive_nums = clean_helper(nums)
            sum = for fold(s from 0, n from positive_nums):
                if n < 0:
                    s
                else:
                    s + n
                end
            end
            sum/positive_nums.length()
        {%- endif -%}
    {%- elif helper_logic == 'clean_sum' -%}
        positive_nums = clean_helper(nums)
        {% if return_logic_structure == 'direct'-%}
        length = positive_nums.length()
        sum = sum_helper(positive_nums)
            {% if check_div_by_zero %}
            if length == 0:
                0
            else:
                average = sum / length
            end 
            {%- else %} 
            average = sum / length
            {% endif -%}
        {%- else %} {# Change to elif and include rare node above as needed #}
        cases(List{{annotation}}) positive_nums:
        | empty => 0
        | link(head, tail) => 
            sum_helper(positive_nums) / positive_nums.length()
        end
        {% endif -%}
    {%- elif helper_logic == 'clean_sum_counter' -%}
        {%- if return_logic_structure == 'direct'-%}
        {# nums was overwritten, now it's name of the cleaned up list #}
        length = counter_helper(nums)
            {%- if check_div_by_zero %}
            if length == 0:
                0
            else:
                sum_helper(nums)/length
            end
            {%- else %}
            sum_helper(nums)/length
            {% endif -%}
        {%- else %} {# Change to elif and include rare node above as needed #}
        cases (List<Number>) nums:
        | empty => 0
        | link(head, tail) =>
            positive_nums = clean_helper(nums)
            length = counter_helper(nums)
            positive_nums / length
        end
        {% endif -%}
    {%- else %} {# Student only cleaned to detect the sentinel, file 155 #}
    cases (List<Number>) nums:
    | empty => 0
    | link(head, tail) =>
        positive_nums = (sentinel_only_helper(nums, -999)).filter(fun(x): x >= 0;)
        total = fold(fun(sum, elem): sum + elem;, 0, positive_nums)
        total / positive_nums.length()
    end
    {% endif -%}
{%- endset -%}

{%- if helper_in_body -%}
    fun rainfall(nums :: List<Number>) -> Number:
        {{ helper }}
        {{ return_logic }}
    end
{%- else -%}
    fun rainfall(nums :: List<Number>) -> Number:
        {# rainfall_body #}
        {{ return_logic }}
    end

    {{ helper }}
{%- endif -%}
'''

        return self.format(
            template,
            helper_logic=helper_logic,
            uses_annotation=uses_annotation,
            helper=CleanFirstHelper(**self.params, 
                helper_logic=helper_logic, uses_annotation=uses_annotation).render(),
            rare_solution=rare_solution,
            checks_length=checks_length,
            helper_in_body=helper_in_body,
            check_div_by_zero=check_div_by_zero,
            return_logic_structure=return_logic_structure, 
            annotation= '<Number>' if uses_annotation else '')

class SCHelper(Rule):
    def render(self):
        helper_logic = self.params['helper_logic']
        uses_annotation = self.params['uses_annotation']
        recurse_strategy = self.params['recurse_strategy']
        clean_function = CleanOnly(**self.params,
            error_strategy = 'zero',
            return_empty = False).render()
        sum_function = SumHelper(**self.params).render()
        counter_function = CounterHelper(**self.params).render()

        template = '''
{{ clean_function }} \n

{{ sum_function }} \n

{%- if helper_logic == 'clean_sum_counter' -%}
{{ counter_function }}
{%- endif -%}
'''

        return self.format(
            template, 
            helper_logic=helper_logic, 
            uses_annotation=uses_annotation,
            clean_function=clean_function,
            sum_function=sum_function,
            counter_function=counter_function,
            recurse_strategy=recurse_strategy)


class CleanInSC(Rule):
    def render(self):
        recurse_strategy = self.choice('recurse_strategy', {'addition': 1, 'link' : 1})
        check_div_by_zero = self.choice('check_div_by_zero', {True: 1, False: 1})
        helper_logic = self.choice('helper_logic', {'clean_only': 1, 'clean_sum_counter': 1})
        helper_in_body = self.choice('helper_in_body', {True: 1, False: 1})
        uses_annotation = self.choice('uses_annotation', {True: 1, False: 1})
        helper = SCHelper(helper_logic=helper_logic, 
            uses_annotation=uses_annotation, recurse_strategy=recurse_strategy).render()

        template = '''
{%- set return_logic -%}
    {%- if helper_logic == 'clean_sum_counter' -%}
    length = counter_helper(nums)
    sum = sum_helper(nums)
        {%- if check_div_by_zero %}
        if length > 0:
            sum / length
        else:
            0
        end
        {%- else %}
        sum / length
        {%- endif -%}
    {%- elif helper_logic == 'clean_only' -%}
        cases(List{{annotation}}) nums:
        | empty => 0
        | link(head, tail) => 
            if head == -999: 
                0
            else: 
                clean_helper(nums, 0, 0)
            end
        end 
    {%- endif -%}
{%- endset -%}

{%- if helper_in_body -%}
fun rainfall(nums :: List{{annotation}}) -> Number:
    {{ helper }}
    {{ return_logic }}
end
{%- else -%}
fun rainfall(nums :: List{{annotation}}) -> Number:
  {{ return_logic }}
end

{{ helper }}
{%- endif -%}
'''

        return self.format(template,
            check_div_by_zero=check_div_by_zero,
            helper_logic=helper_logic,
            helper_in_body=helper_in_body,
            helper=helper,
            uses_annotation=uses_annotation,
            recurse_strategy=recurse_strategy,
            annotation = '<Number>' if uses_annotation else '')

class Program(Rule):
    def render(self):
        strategy = self.choice('strategy', {
            # Labels.SingleLoop: 1,
            Labels.CleanFirst: 1,
            # Labels.CleanInSC: 1
        })

        self.set_label(int(strategy))

        if strategy == Labels.SingleLoop:
            return SingleLoop().render()
        elif strategy == Labels.CleanFirst:
            return CleanFirst().render()
        elif strategy == Labels.CleanInSC:
            return CleanInSC().render()
