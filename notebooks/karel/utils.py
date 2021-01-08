import javalang
from javalang import tree
import textwrap
import os
from pickle_cache import PickleCache
from dataclasses import dataclass, replace
from iterextras import par_for
import copy
from enum import Enum
from typing import Dict, Union, Optional, List, Any
from unionfind import UnionFind
from torch.distributions import Categorical
from torch import tensor as t

pcache = PickleCache('.pcache')

DATA_DIR = '../../data/cs106a/CheckerboardKarel_anonymized'
STUDENTS = os.listdir(DATA_DIR)

@dataclass
class Program:
    source: str
    ast: tree.CompilationUnit
        
def load_student_programs(student):
    files = sorted(os.listdir(f'{DATA_DIR}/{student}'))
    programs = []
    for f in files:
        try:
            source = open(f'{DATA_DIR}/{student}/{f}').read()
            ast = javalang.parse.parse(source)
            programs.append(Program(ast=ast, source=source))
        except (UnicodeDecodeError, javalang.parser.JavaSyntaxError, javalang.tokenizer.LexerError):
            pass
    return programs

def get_solutions():
    def load():
        solutions = {}    
        progs = par_for(load_student_programs, STUDENTS, process=True)
        return {k: v for k, v in zip(STUDENTS, progs)}

    return pcache.get('solutions', load)

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
        
def stmts_to_string(ss):
    return '\n'.join([stmt_to_string(s) for s in ss])

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


class Action(Enum): 
    move = 1
    turnRight = 2
    turnLeft = 3
    turnAround = 4
    putBeeper = 5
    pickBeeper = 6
    paintCorner = 7
    stop = 8
    
    def __repr__(self):
        return str(self).split('.')[-1] + '()'
    
class Predicate(Enum):
    frontIsClear = 1
    rightIsClear = 2
    leftIsClear = 3
    frontIsBlocked = 4
    leftIsBlocked = 5
    rightIsBlocked = 6
    beepersPresent = 7
    noBeepersPresent = 8
    beepersInBag = 9
    noBeepersInBag = 10
    facingNorth = 11
    facingEast = 12
    facingSouth = 13
    facingWest = 14
    notFacingNorth = 15
    notFacingEast = 16
    notFacingSouth = 17
    notFacingWest = 18
    cornerColorIs = 19
    
    def __repr__(self):
        return str(self).split('.')[-1] + '()'
    

class Op:
    pass

@dataclass
class Sampled:
    parts: List[Any]
      
    def __repr__(self):
        return ';\n'.join([repr(p) for p in self.parts])    

@dataclass
class IfNode(Op):
    cond: Predicate
    then: str
    else_: Optional[str]
        
    def substitute(self, subs):
        return replace(self,
            then=subs.get(self.then, self.then), 
            else_=subs.get(self.else_, self.else_) if self.else_ is not None else None)
 
    def refs(self):
        return [self.then] + ([self.else_] if self.else_ is not None else [])
    
    def sample(self, grammar):
        return replace(
            self, 
            then=grammar.productions[self.then].sample(grammar),
            else_=grammar.productions[self.else_].sample(grammar) if self.else_ is not None else None)
        
    def __repr__(self):
        return (f'if ({repr(self.cond)}) {{ {repr(self.then)} }}' + 
            (f' else {{ {repr(self.else_)} }}' if self.else_ is not None else ''))
        
@dataclass
class WhileNode(Op):
    cond: Predicate
    body: str
        
    def substitute(self, subs):
        return replace(self, body=subs.get(self.body, self.body))
    
    def refs(self):
        return [self.body]
    
    def sample(self, grammar):
        return replace(self, body=grammar.productions[self.body].sample(grammar))
    
    def __repr__(self):
        return f'while ({repr(self.cond)}) {{ {repr(self.body)} }}'
    
@dataclass
class Rule:
    parts: List[Union[str, Action, Op]]    
    prob: float
        
    def substitute(self, subs):
        def aux(r):
            if isinstance(r, str):
                return subs.get(r, r)
            elif isinstance(r, Op):
                return r.substitute(subs)
            else:
                return r
        return replace(self, parts=[aux(r) for r in self.parts])
    
    def refs(self):
        def aux(r):
            if isinstance(r, str):
                return [r]
            elif isinstance(r, Op):
                return r.refs()
            else:
                return []
        return [ref for r in self.parts for ref in aux(r)]
    
    def sample(self, grammar):
        def aux(r):
            if isinstance(r, str):
                return grammar.productions[r].sample(grammar)
            elif isinstance(r, Op):
                return r.sample(grammar)
            else:
                return r
        return Sampled(parts=[aux(r) for r in self.parts])
            
@dataclass
class Production:
    rules: List[Rule]
        
    def substitute(self, subs):
        return replace(self, rules=[r.substitute(subs) for r in self.rules])
    
    def refs(self):
        return [ref for r in self.rules for ref in r.refs()]
    
    def sample(self, grammar):
        dist = Categorical(t([r.prob for r in self.rules]))
        return self.rules[dist.sample().item()].sample(grammar)

@dataclass
class Grammar:
    productions: Dict[str, Production]
        
    def sample(self):
        return self.productions['start'].sample(self)        
        
    def expand(self, name):
        prods = {name: self.productions[name]}
        while True:
            changed = False
            to_add = {}
            for rule in prods.values():
                refs = rule.refs()
                for ref in refs:
                    if not ref in prods:
                        to_add[ref] = self.productions[ref]
                        changed = True
                   
            if changed:
                prods = {**prods, **to_add}
            else:
                break
        return prods

    def simplify(self):
        p = copy.deepcopy(self.productions)
        uf = UnionFind(list(p.keys()))
        while True:
            changed = False
            subs = {}
            to_add = {}
            to_delete = set()
            for k1, r1 in p.items():
                for k2, r2 in p.items():
                    if k1 != k2 and k1 not in subs and k2 not in subs and r1 == r2:
                        subs[k2] = k1
                        to_add[k1] = r2
                        to_delete.add(k2)
                        uf.union(k1, k2)
                        changed = True
                        
            p = {**p, **to_add}
            for k in to_delete:
                del p[k]
                
            if not changed:
                break
            else:
                p = {k2: r2.substitute(subs) for k2, r2 in p.items()}
        return Grammar(productions=p), {
            k: uf.component(k)
            for k in p.keys()
        }
    
class Unimplemented(Exception):
    pass

class GrammarGenerator:
    def __init__(self, student, methods):
        self.productions = {} 
        self.methods = methods
        self.student = student
        
    def add_production(self, production, name_hint=None):
        existing = [k for k, p in self.productions.items() if p == production]
        if len(existing) > 0:
            return existing[0]
        else:
            if name_hint:
                name = f'{self.student}_{name_hint}'
            else:
                name = f'{self.student}_rule{len(self.productions)}'
            self.productions[name] = production
            return name
        
    def generate(self, stmt, name_hint=None):
        if isinstance(stmt, tree.IfStatement):
            if stmt.else_statement is not None and not isinstance(stmt.else_statement, tree.BlockStatement):
                else_ = tree.BlockStatement(statements=[stmt.else_statement])
            else:
                else_ = stmt.else_statement
            return IfNode(
                cond=self.generate(stmt.condition),
                then=self.generate(stmt.then_statement),
                else_=self.generate(else_) if else_ is not None else None
            )
        elif isinstance(stmt, tree.WhileStatement):
            return WhileNode(
                cond=self.generate(stmt.condition),
                body=self.generate(stmt.body)
            )
        elif isinstance(stmt, tree.BlockStatement):
            return self.add_production(Production(rules=[Rule(parts=[
                self.generate(s) for s in stmt.statements
            ], prob=1.0)]), name_hint=name_hint)
        elif isinstance(stmt, tree.MethodInvocation):
            name = stmt.member
            
            if name in self.methods:                
                return self.generate(self.methods[name])            
            elif hasattr(Action, name):
                return Action[name]
            else:
                return Predicate[name]
        elif isinstance(stmt, tree.StatementExpression):
            return self.generate(stmt.expression)
        elif isinstance(stmt, tree.MethodDeclaration):
            return self.generate(tree.BlockStatement(statements=stmt.body), name_hint=stmt.name)
        else:
            raise Unimplemented(stmt)