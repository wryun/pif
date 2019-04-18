from textx.metamodel import metamodel_from_str
import operator
from functools import reduce

import expression
import logging


DEBUG=True

if DEBUG:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)


GRAMMAR = """
Program: Block;
Block: paragraphs*=Paragraph;
Paragraph: /(?m)\n*/ sentences+=Sentence /(?m)\n*/;
Sentence: assignment=Assignment? instructions+=Instruction /(?m)\n/;
Instruction: Pushable | '.';
Assignment: var=ID '=';
Pushable: function=Function | var=ID | rawval=RawVal | expr=Expression;
Expression: '((' e=Expression0 '))';
RawVal: FLOAT | STRING;
Function: '{' args=Types block=Block '}';
Types: '(' varsWithType*=VarWithType ')';
VarWithType: name=ID type=ID;
""" + expression.GRAMMAR
#Type: Types | ID;


class Types:
    def __init__(self, parent, varsWithType=None):
        self.varsWithType = varsWithType

    def eval(self, c):
        return {entry.name: c.lookup(entry.type) for entry in self.varsWithType}


class Pushable:
    def __init__(self, parent, var, rawval, expr, function):
        self.var = var
        self.rawval = rawval
        self.expr = expr
        self.function = function

    def eval(self, c):
        if self.var:
            return c.lookup(self.var)
        elif self.expr:
            return self.expr.e.eval(c)
        elif self.function:
            self.function.add_context(c)
            return self.function
        else:
            return self.rawval


class Function:
    def __init__(self, parent=None, args=None, block=None, builtin=None, arg_dict=None):
        self.parent = parent
        self.args = args
        self.block = block
        self.builtin = builtin
        self.arg_dict = arg_dict

    def add_context(self, c):
        self.c = c
        self.arg_dict = self.args.eval(c)

    def eval(self, s_c):
        if self.block:
            print(s_c.vals)
            c = self.c.copy()
            for (n, t) in self.arg_dict.items():
                c.push_name(n, s_c.pop_oneof([t, n]))
            return self.block.eval(c)
        elif self.builtin:
            args = [s_c.pop_oneof([t, n]) for (n, t) in self.arg_dict.items()]
            return self.builtin(*args)


class Block:
    def __init__(self, parent=None, paragraphs=None):
        self.paragraphs = paragraphs

    def eval(self, c):
        for paragraph in self.paragraphs:
            logging.debug('new paragraph')
            for sentence in paragraph.sentences:
                logging.debug('new sentence')
                s_c = Context(c)
                for instruction in sentence.instructions:
                    if instruction == '.':
                        val = s_c.pop(Function).eval(s_c)
                        if val is not None:
                            s_c.push(val)
                    else:
                        s_c.push(instruction.eval(c))
                if sentence.assignment:
                    assert len(s_c.vals) == 1
                    if sentence.assignment.var != '_':
                        c.push_name(sentence.assignment.var, list(s_c.vals.values())[0])
                elif len(s_c.vals) > 0:
                    assert len(s_c.vals) == 1
                    c.push(list(s_c.vals.values())[0])


model = metamodel_from_str(
  GRAMMAR,
  classes=[Pushable, Block, Function, Types] + expression.grammar_classes,
  ws=' '
)


import sys
import code


# rules:
#  looking up to call a function should only look in current function context
#  looking up a name as a name lookup should look everywhere (traverse indefinitely)
#  any shadowing is illegal
#  AND you cannot mutate variables outside your current function context
class Context:
    def __init__(self, parent=None, vals=None):
        self.parent = parent
        self.vals = vals or {}

    def lookup(self, n):
        if n in self.vals:
            return self.vals[n]
        elif self.parent is None:
            raise KeyError(n)
        else:
            return self.parent.lookup(n)

    def pop(self, n):
        val = self.lookup(n)
        del self.vals[n]
        return val

    def pop_oneof(self, possibles):
        print(possibles)
        print(self.vals)
        for n in possibles:
            try:
                val = self.lookup(n)
            except KeyError:
                continue
            del self.vals[n]
            return val

        raise KeyError(str(possibles))

    def push(self, val):
        self.push_name(type(val), val)

    def push_name(self, n, val):
        try:
            self.lookup(n)
        except KeyError:
            logging.debug(f'{n} = {val}')
            self.vals[n] = val
        else:
            raise Exception(f'existing name {n}')

    def copy(self):
        return Context(self.parent, self.vals.copy())


def main(fname, *args):
    def p(s):
        print(s)
    c = Context()
    c.push_name('print_s', Function(builtin=print, arg_dict=dict(s=str)))
    c.push_name('print_f', Function(builtin=print, arg_dict=dict(f=float)))
    c.push_name('string', str)
    c.push_name('number', float)

    program = model.model_from_file(fname, debug=DEBUG)
    program.eval(c)

    #code.interact(local={**globals(), **locals()})


if __name__ == '__main__':
    main(*sys.argv[1:])
