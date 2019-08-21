from autoplan.grammar import Rule
from .labels import GeneralRainfallLabels

Labels = GeneralRainfallLabels

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
              {{ failure }}
            else:
              sum / length
            end
          {% endif -%}
        {%- else -%}
        sum / length
        {%- endif -%}

      | link(head, tail) =>
        if head == -999:
          {%- if sentinel_recurse -%}
          helper([], sum, length)
          {%- else -%}
          sum / length
          {%- endif -%}
        
        {%- if gt_zero -%}
          else if head > 0:
            helper(tail, sum + head, length + 1)
          else:
            helper(tail, sum, length)
          end
        {%- else -%}
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
    raise("error")
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
        {{ failure }}
      else:
        vals.sum / vals.length
      {%- else -%}
      cases(List) nums:
      | empty => {{ failure }}
      | link(head, tail) => 0 
        if head == -999:
          {{ failure }}
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

{%- set rainfall_body -%}
  {# File 129 #}
{%- endset -%}

{%- if helper_in_body -%}
  fun rainfall(nums :: List<Number>) -> Number:
    {{ helper }}
    {{ return_logic }}
  end
{%- else -%}
  fun rainfall(nums :: List<Number>) -> Number:
    {{ rainfall_body }}
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
   
# class SumList(Rule):
#   def render(self):
#     sum_strategy = self.choice('average_strategy', {
#       'for_fold': 1,
#       'foldr': 1
#     })

#   if sum_strategy == 'for_fold':
#     return '''
#     for fold(total from 0, elem from nums): elem + total end
#     '''
#   else:
#     return 'nums.foldr(_+_,0)'


# class CleanFirstHelper(Rule):
#   def render(self):
#     template = '''
# fun helper(nums :: List<Number>) -> List<Number>:
#   cases(List) nums:
#   | empty => []
#   | link(f, r) =>
#     if f == -999: []
#     else if f < 0: helper(r)
#     else: link(f, helper(r))
# '''

#   return template


# class CleanFirst(Rule):
#   def render(self):
#     helper_in_body = self.choice('helper_in_body', {True: 1, False: 1})
#     inline_average = self.choice('inline_average', {True: 1, False: 1})
#     checks_length = self.choice('checks_length', {True: 1, False: 1})

#     template = '''
# {%- set return_logic -%}
#   nums = helper(nums)
#   {%- if inline_average -%}
#   {{ list_sum }} / nums.length()
#   {%- else -%}
#   sum = {{ list_sum }}
#   sum / nums.length()
#   {%- endif -%}
# {%- endset -%}

# {%- set body -%}
#   {%- if checks_length -%}
#   case(List) nums:
#   | empty => 0
#   | link(_,_) =>
#      {{ return_logic }}
#   {%- else -%}
#   {{ return_logic }}
#   {%- endif -%}
# {%- endset -%}

# {%- if helper_in_body -%}
# fun rainfall(nums :: List<Number>) -> Number:
#   {{ helper }}
#   {{ body }}
# end
# {%- else -%}
# fun rainfall(nums :: List<Number>) -> Number:
#   {{ body }}
# end

# {{ helper }}
# {%- endif -%}
# '''

#   return self.format(
#     template,
#     list_sum=SumList().render(),
#     inline_average=inline_average,
#     helper=CleanFirstHelper().render(),
#     helper_in_body=helper_in_body)


# class SCHelper(Rule):
#     def render(self):
#         sc_helper_style = self.choice('sc_helper_style', {'case': 1, 'if': 1})

#         template = '''
# {%- set rec_expr -%}
#   {%- if sum -%} f + {%- else -%} 1 + {%- endif -%} helper(r)
# {%- endset -%}

# fun helper(nums :: List<Number>) -> Number:
#   {%- if sc_helper_style == 'case' -%}
#   cases(List) nums:
#     | empty => 0
#     | link(f, r) =>
#       if f == -999:
#         0
#       else if f < 0:
#         helper(r)
#       else:
#         {{ rec_expr }}
#       end
#   {%- else -%}
#   if is-empty(nums):
#     0
#   else if nums.first == -999:
#     0
#   else if nums.first < 0:
#     helper(nums.rest)
#   else:
#     {{ rec_expr }}
#   end
#   {%- endif -%}
# '''
#         return self.format(
#             template,
#             sc_helper_style=sc_helper_style,
#             sum=self.params['sum'])


# class CleanInSC(Rule):
#     def render(self):
#         helper_in_body = self.choice('helper_in_body', {True: 1, False: 1})

#         template = '''
# {%- set return_logic -%}
#   c = count(nums)
#   s = sum(nums)
#   if c > 0:
#     s / c
#   else:
#     0
#   end
# {%- endset -%}
# {%- if helper_in_body -%}
# fun rainfall(nums :: List<Number>) -> Number:
#   {{ sum_helper }}
#   {{ count_helper }}
#   {{ return_logic }}
# end
# {%- else -%}
# fun rainfall(nums :: List<Number>) -> Number:
#   {{ return_logic }}
# end

# {{ sum_helper }}
# {{ count_helper }}
# {%- endif -%}
#         '''

#         return self.format(
#             template,
#             helper_in_body=helper_in_body,
#             sum_helper=SCHelper(sum=True).render(),
#             count_helper=SCHelper(sum=False).render())

class Program(Rule):
    def render(self):
        strategy = self.choice('strategy', {
            Labels.SingleLoop: 1,
            # Labels.CleanFirst: 1,
            # Labels.CleanInSC: 1,
        })

        self.set_label(int(strategy))

        if strategy == Labels.SingleLoop:
            return SingleLoop().render()
        # elif strategy == Labels.CleanFirst:
        #     return CleanFirst().render()
        # elif strategy == Labels.CleanInSC:
        #     return CleanInSC().render()
