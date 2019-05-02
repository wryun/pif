import operator
from functools import reduce


OPS = {
  '+': operator.add,
  '-': operator.sub,
  '*': operator.mul,
  '/': operator.truediv,
  '==': operator.eq,
  '<=': operator.le,
  '>=': operator.ge,
  '!=': operator.ne,
  '>': operator.gt,
  '<': operator.lt,
}


def expression_eval(self, c):
    return reduce(lambda total, elem: OPS[elem[0]](total, elem[1].eval(c)),
                  zip(self.ops, self.exprs), self.expr.eval(c))


def value_eval(self, c):
    if self.id:
        return c.lookup_by_name(self.id)[1]
    elif self.expr:
        return self.expr.eval(c)
    elif self.num is not None:
        return self.num
    else:
        raise 'hell'
