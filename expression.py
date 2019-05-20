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
        val = c.get_name(self.id)
        if isinstance(val, float) or isinstance(val, int):
            return val
        elif val == float or val == int:
            return c.pop_type(val)
        else:
            raise Exception('expressions can only have numbers')
    elif self.expr:
        return self.expr.eval(c)
    elif self.num is not None:
        return self.num
    else:
        raise Exception('internal error - failed switch statement')
