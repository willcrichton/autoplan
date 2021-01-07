from javalang import tree
import textwrap


class Visitor:
    def visit(self, node):
        visitor = getattr(self, f'visit_{node.__class__.__name__}', self.generic_visit)
        visitor(node)

    def generic_visit(self, node):
        for field in node.attrs:
            value = getattr(node, field)
            if isinstance(value, list) and len(value) > 0 and isinstance(value[0], tree.Node):
                for subnode in value:
                    self.visit(subnode)
            elif isinstance(value, tree.Node):
                self.visit(value)


class Transformer:
    def visit(self, node):
        visitor = getattr(self, f'visit_{node.__class__.__name__}', self.generic_visit)
        return visitor(node)
    
    def generic_visit(self, node):
        for field in node.attrs:
            old_value = getattr(node, field)
            if isinstance(old_value, list) and len(old_value) > 0 and isinstance(old_value[0], tree.Node):
                new_values = []
                for value in old_value:
                    if isinstance(value, tree.Node):
                        value = self.visit(value)
                        if value is None:
                            continue
                        elif not isinstance(value, tree.Node):
                            new_values.extend(value)
                            continue
                    new_values.append(value)
                old_value[:] = new_values
            elif isinstance(old_value, tree.Node):
                new_node = self.visit(old_value)
                if new_node is None:
                    delattr(node, field)
                else:
                    setattr(node, field, new_node)
        return node
    

def expr_to_string(e):
    if isinstance(e, tree.MethodInvocation):
        return f'{e.member}()'
    elif isinstance(e, tree.BinaryOperation):
        return f'{expr_to_string(e.operandl)} {e.operator} {expr_to_string(e.operandr)}'
    else:
        raise Exception(f'Unknown expression {type(e)})')

    
def stmt_to_string(s, indent=0):
    if isinstance(s, list):
        return '\n'.join([stmt_to_string(s2) for s2 in s])
    elif isinstance(s, tree.BlockStatement):
        return f"{{\n{textwrap.indent(stmt_to_string(s.statements), '    ')}\n}}"
    elif isinstance(s, tree.StatementExpression):
        return f'{expr_to_string(s.expression)};'
    elif isinstance(s, tree.IfStatement):
        cond = expr_to_string(s.condition)
        then = stmt_to_string(s.then_statement)
        if s.else_statement is None:
            return f'if ({cond}) {then}'
        else:
            else_ = stmt_to_string(s.else_statement)
            return f'if ({cond}) {then} else {else_}'
    elif isinstance(s, tree.WhileStatement):
        return f'while ({expr_to_string(s.condition)}) {stmt_to_string(s.body)}'
    elif isinstance(s, tree.BreakStatement):
        return 'break;'
    else:
        raise Exception(f'Unknown type {type(s)}')
        

def fun_to_string(f):
    body = stmt_to_string(tree.BlockStatement(statements=f.body))
    return f'void {f.name}() {body}'
        

def get_methods(soln):
    cdecl = next(c[0] for c in soln.ast.children 
                 if isinstance(c, list) and isinstance(c[0], tree.ClassDeclaration))
    return {method.name: method for method in cdecl.methods}


class Inline(Transformer):
    def __init__(self, methods):
        self.methods = methods
        
    def visit_StatementExpression(self, s):
        if isinstance(s.expression, tree.MethodInvocation):
            fname = s.expression.member
            if fname in self.methods:
                fdef = copy.deepcopy(self.methods[fname])
                return self.visit(fdef).body
        return s

    
class TreeSize(Visitor):
    def __init__(self):
        self.size = 0

    def generic_visit(self, node):
        self.size += 1
        super().generic_visit(node)


def tree_size(node):
    visitor = TreeSize()
    visitor.visit(node)
    return visitor.size
