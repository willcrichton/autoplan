from autoplan.grammar import Rule
from .labels import GeneralRainfallLabels

Labels = GeneralRainfallLabels

class SingleLoopHelper(Rule):
    def render(self):
        record_or_params = self.choice('record_or_params', {'record': 1, 'params': 1})
        sentinel_recurse = self.choice('sentinel_recurse', {True: 1, False: 1})
        gt_zero = self.choice('gt_zero', {True: 1, False: 1})
        template = '''
{% if record_or_params == 'record' %}
  fun helper(nums :: List<Number>) -> {sum : Number, length : Number}:
    cases(List<Number>) nums:
      | empty => {sum: 0, length: 0}
      | link(f, r) =>
        if f == -999:
          {sum: 0, length: 0}
        else if f < 0:
          helper(r)
        else:
          v = helper(r)
          {sum: v.sum + f, length: v.length + 1}
        end
    end
  end
{% else %}
  fun helper(nums :: List<Number>, sum :: Number, count :: Number) -> Number:
    cases(List<Number>) nums:
      | empty =>
         if count == 0:
           0
         else:
           sum / count
         end
      | link(f, r) =>
        if f == -999:
          {% if sentinel_recurse %}
          helper([], sum, count)
          {% else %}
          sum / count
          {% endif %}
        else if f < 0:
          helper(r, sum, count)
        else:
          helper(r, sum + f, count + 1)
        end
    end
  end
{% endif %}
        '''
        return self.format(
            template,
            record_or_params=record_or_params,
            sentinel_recurse=sentinel_recurse)


class SingleLoop(Rule):
    def render(self):
        helper = SingleLoopHelper().render()
        helper_in_body = self.choice('helper_in_body', {True: 1, False: 1})
        error_strategy = self.choice('error_strategy', {'exception': 1, 'zero': 1})
        template = '''
{% set return_logic %}
  vals = helper(nums)
  if vals.length == 0:
    {% if error_strategy == 'exception' %}
    raise("error")
    {% else %}
    0
    {% endif %}
  else:
    vals.sum / vals.length
{% endset %}
{% if helper_in_body %}
fun rainfall(nums :: List<Number>) -> Number:
  {{ helper }}
  {{ return_logic }}
end
{% else %}
fun rainfall(nums :: List<Number>) -> Number:
  {{ return_logic }}
end
{{ helper }}
{% endif %}
        '''
        return_logic = '''
        '''

        if helper_in_body:
            template = '''
        '''
        else:
            template = '''
        '''

        return self.format(template, return_logic=return_logic, helper=helper)


class SumList(Rule):
    def render(self):
        sum_strategy = self.choice('average_strategy', {
            'for_fold': 1,
            'foldr': 1
        })

        if sum_strategy == 'for_fold':
            return '''
            for fold(total from 0, elem from nums): elem + total end
            '''
        else:
            return 'nums.foldr(_+_,0)'


class CleanFirstHelper(Rule):
    def render(self):
        template = '''
fun helper(nums :: List<Number>) -> List<Number>:
  cases(List) nums:
  | empty => []
  | link(f, r) =>
    if f == -999: []
    else if f < 0: helper(r)
    else: link(f, helper(r))
        '''
        return template


class CleanFirst(Rule):
    def render(self):
        helper_in_body = self.choice('helper_in_body', {True: 1, False: 1})
        inline_average = self.choice('inline_average', {True: 1, False: 1})
        checks_length = self.choice('checks_length', {True: 1, False: 1})

        template = '''
{% set return_logic %}
  nums = helper(nums)
  {% if inline_average %}
  {{ list_sum }} / nums.length()
  {% else %}
  sum = {{ list_sum }}
  sum / nums.length()
  {% endif %}
{% endset %}

{% set body %}
  {% if checks_length %}
  case(List) nums:
  | empty => 0
  | link(_,_) =>
     {{ return_logic }}
  {% else %}
  {{ return_logic }}
  {% endif %}
{% endset %}

{% if helper_in_body %}
fun rainfall(nums :: List<Number>) -> Number:
  {{ helper }}
  {{ body }}
end
{% else %}
fun rainfall(nums :: List<Number>) -> Number:
  {{ body }}
end

{{ helper }}
{% endif %}
        '''

        return self.format(
            template,
            list_sum=SumList().render(),
            inline_average=inline_average,
            helper=CleanFirstHelper().render(),
            helper_in_body=helper_in_body)


class SCHelper(Rule):
    def render(self):
        sc_helper_style = self.choice('sc_helper_style', {'case': 1, 'if': 1})

        template = '''
{% set rec_expr %}
  {% if sum %} f + {% else %} 1 + {% endif %} helper(r)
{% endset %}

fun helper(nums :: List<Number>) -> Number:
  {% if sc_helper_style == 'case' %}
  cases(List) nums:
    | empty => 0
    | link(f, r) =>
      if f == -999:
        0
      else if f < 0:
        helper(r)
      else:
        {{ rec_expr }}
      end
  {% else %}
  if is-empty(nums):
    0
  else if nums.first == -999:
    0
  else if nums.first < 0:
    helper(nums.rest)
  else:
    {{ rec_expr }}
  end
  {% endif %}
'''
        return self.format(
            template,
            sc_helper_style=sc_helper_style,
            sum=self.params['sum'])


class CleanInSC(Rule):
    def render(self):
        helper_in_body = self.choice('helper_in_body', {True: 1, False: 1})

        template = '''
{% set return_logic %}
  c = count(nums)
  s = sum(nums)
  if c > 0:
    s / c
  else:
    0
  end
{% endset %}
{% if helper_in_body %}
fun rainfall(nums :: List<Number>) -> Number:
  {{ sum_helper }}
  {{ count_helper }}
  {{ return_logic }}
end
{% else %}
fun rainfall(nums :: List<Number>) -> Number:
  {{ return_logic }}
end

{{ sum_helper }}
{{ count_helper }}
{% endif %}
        '''

        return self.format(
            template,
            helper_in_body=helper_in_body,
            sum_helper=SCHelper(sum=True).render(),
            count_helper=SCHelper(sum=False).render())

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
