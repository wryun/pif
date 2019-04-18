import operator
from functools import reduce


GRAMMAR = """
Expression0: expr=Expression1 (ops=Expression0Operators exprs=Expression1)*;
Expression0Operators: '+' | '-';
Expression1: expr=Value (ops=Expression1Operators exprs=Value)*;
Expression1Operators: '*' | '/';
Value: id=ID | num=FLOAT | ('(' expr=Expression0 ')');
"""


OPS = {
  '+': operator.add,
  '-': operator.sub,
  '*': operator.mul,
  '/': operator.truediv,
}


class Expression:
    def __init__(self, parent, expr, ops, exprs):
        self.expr = expr
        self.ops = ops
        self.exprs = exprs

    def eval(self, c):
        return reduce(lambda total, elem: OPS[elem[0]](total, elem[1].eval(c)),
                      zip(self.ops, self.exprs), self.expr.eval(c))


class Value:
    def __init__(self, parent, id, num, expr):
        self.id = id
        self.num = num
        self.expr = expr

    def eval(self, c):
        if self.id:
            return c.lookup(self.id)
        elif self.expr:
            return self.expr.eval(c)
        elif self.num:
            return self.num
        else:
            raise 'hell'


grammar_classes = [type(f'Expression{i}', (Expression,), {}) for i in range(2)] + [Value]
