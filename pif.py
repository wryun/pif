from textx.metamodel import metamodel_from_str
import operator
import os
from functools import reduce

import expression
import logging


DEBUG=os.environ.get('PIF_DEBUG') == '1'

if DEBUG:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)


GRAMMAR = """
Program: Block;
Block: paragraphs*=Paragraph;
Paragraph: /(?m)\n*/ lines+=Line /(?m)\n*/;
Line: assignment=Assignment? ( expr=Sentence | expr=If | expr=While | expr=For ) /(?m)\n/;
Sentence: instructions+=Instruction;
If: 'if' condition=Sentence 'do' block=Block ('elif' elif_conditions=Sentence 'do' elif_blocks=Block)* ('else' else_block=Block)? 'end';
While: 'while' condition=Sentence 'do' block=Block 'end';
For: 'for' (var=MyID 'in')? sentence=Sentence 'do' block=Block 'end';
Instruction: Pushable | '.';
Assignment: var=MyID '=';
Pushable: function=Function | var=MyID | rawval=RawVal | expr=Expression;
Expression: '((' e=Expression0 '))';
RawVal: FLOAT | STRING | List | Dict;
List: 'List[' (sentences=Sentence /(?m),?\n*/)* ']';
Dict: 'Dict[' (keys=Sentence '=' values=Sentence /(?m),?\n*/)* ']';
Function: 'func' args=Types block=Block 'end';
Types: '(' varsWithType*=VarWithType ')';
VarWithType: name=MyID type=MyID;
Keyword: 'end' | 'func' | 'if' | 'while' | 'for' | 'do' | 'else' | 'elif' | 'List' | 'Dict';
MyID: !Keyword ID;
""" + expression.GRAMMAR
#Type: Types | ID;


model = metamodel_from_str(
  GRAMMAR,
  classes=expression.grammar_classes,
  ws=' '
)

def function_eval(self, s_c):
    return self.block.eval(self.c.new_function_context(s_c, self.arg_dict))


def if_eval(self, c):
    zipped = zip([self.condition] + (self.elif_conditions or []),
                 [self.block] + (self.elif_blocks or []))
    for (cond, block) in zipped:
        res = cond.eval(c)
        debug(self, 'evaluating condition')
        if res is None:
            raise Exception('must have a result')
        elif res:
            debug(self, 'block eval')
            return block.eval(c)

    if self.else_block:
        return self.else_block.eval(c)

    return None


def pushable_eval(self, c):
    if self.var:
        return c.get_name(self.var)
    elif self.expr:
        return self.expr.e.eval(c)
    elif self.function:
        logging.debug(c)
        self.function.c = c
        self.function.arg_dict = self.function.args.eval(c)
        return self.function
    elif hasattr(self.rawval, 'sentences'):
        return [s.eval(c) for s in self.rawval.sentences]
    elif hasattr(self.rawval, 'keys'):
        return {k.eval(c): v.eval(c) for (k, v) in zip(self.rawval.keys, self.rawval.values)}
    else:
        return self.rawval


def while_eval(self, c):
    last_eval = None
    while True:
        res = self.condition.eval(c)
        if res is None:
            raise Exception('must have a result')
        elif res:
            last_eval = self.block.eval(c)
        else:
            break
    return last_eval


def types_eval(self, c):
    return {entry.name: c.get_name(entry.type) for entry in self.varsWithType}


def for_eval(self, c):
    last_eval = None
    for elem in self.sentence.eval(c):
        if not self.var:
            c.push_type(elem)
        elif self.var and self.var != '_':
            c.push_name(self.var, elem)
        last_eval = self.block.eval(c)
    return last_eval


def block_eval(self, c):
    for paragraph in self.paragraphs:
        debug(paragraph)
        for line in paragraph.lines:
            debug(line)
            try:
                res = line.expr.eval(c)
                if res is None:
                    assert not line.assignment
                elif isinstance(line.expr, Sentence) and not line.assignment:
                    # i.e. only push from a sentence by default
                    # swallow things from ifs/whiles/fors to avoid noise
                    c.push_type(res)
                elif line.assignment and line.assignment.var != '_':
                    c.push_name(line.assignment.var, res)
            except Exception as e:
                error(line.expr, e)

        try:
            c.result()  # validate each paragraph has at most one result
        except Exception as e:
            error(paragraph, e)

    logging.debug('function result %s', c.result())
    return c.result()


def sentence_eval(self, c):
    debug(self)
    s_c = Context(c)
    for instruction in self.instructions:
        if instruction == '.':
            logging.debug('before func: %s', s_c)
            val = s_c.pop_type(Function).eval(s_c)
            if val is not None:
                s_c.push_type(val)
            logging.debug('after func: %s', s_c)
        else:
            s_c.push_type(instruction.eval(c))

    return s_c.result()


for cls_name, cls in model.namespaces[None].items():
    eval_name = f'{cls_name.lower()}_eval'
    if eval_name in vars():
        cls.eval = vars()[eval_name]
    globals()[cls_name] = cls


def make_builtin(fn, args_dict):
    r = Function()
    # TODO should have same lookup rules as normal Function.
    # also, this is wacky.
    r.eval = lambda s_c: fn(*(s_c.pop_type(t) for (_, t) in args_dict.items()))
    return r


def debug(m, s="info"):
    line, col = program._tx_parser.pos_to_linecol(m._tx_position)
    logging.debug('line %d col %d - %s - %s', line, col, m.__class__.__name__, s)


def error(m, s="info"):
    import sys
    line, col = program._tx_parser.pos_to_linecol(m._tx_position)
    logging.exception('line %d col %d - %s - %s', line, col, m.__class__.__name__, s)
    sys.exit(1)


import sys
import code


def find_dupes(it):
    seen = set()
    dupes = set()
    for elem in it:
        if elem not in seen:
            seen.add(elem)
        else:
            dupes.add(elem)
    return dupes


# rules:
#  looking up to call a function should only look in current function context
#  looking up a name as a name lookup should look everywhere (traverse indefinitely)
#  any shadowing of names is illegal; shadowing of types is legal if not in current context
#  AND you cannot mutate variables outside your current function context
class Context:
    def __init__(self, parent=None, n_v=None, t_v=None, args=None, args_dupe_types=None):
        self.parent = parent
        self.n_v = n_v or {}
        self.t_v = n_v or {}
        self.args = args or {}
        self.args_dupe_types = args_dupe_types or set()

    def lookup_by_type(self, t, recurse=0):
        # If we've hit the top level and it wasn't an initial
        # lookup at the top level, report it's not there
        # (too dangerous to slurp things out of top level context)
        # NB first level recursion is just getting out of the SentenceContext,
        # which is uninteresting. Clean up this logic.
        if recurse > 1 and self.parent is None:
            raise KeyError(t)
        elif t in self.args_dupe_types:
            raise KeyError(f'attempting to automatically fill ambiguous type {t} (multiple names for that type in function sig)')
        elif t in self.t_v:
            return self, self.t_v[t]
        elif self.parent is None or recurse > 1:
            # we only allow one level of recursion in other places to avoid
            # deeply nested context copies + weirdness.
            raise KeyError(t)
        else:
            return self.parent.lookup_by_type(t, recurse=recurse + 1)

    def lookup_by_name(self, n):
        if n in self.n_v:
            return self, self.n_v[n]
        elif self.parent is None:
            raise KeyError(n)
        else:
            return self.parent.lookup_by_name(n)

    def get_name(self, n):
        c, val = self.lookup_by_name(n)
        c.delete_type(n)
        return val

    def delete_name(self, t):
        if t in self.args:
            n = self.args[t]
            del self.args[n]
            del self.args[t]
            del self.n_v[n]
        del self.t_v[t]

    def delete_type(self, n):
        if n in self.args:
            t = self.args[n]
            del self.args[t]
            del self.args[n]
            del self.t_v[t]

    def pop_type(self, t):
        c, val = self.lookup_by_type(t)
        c.delete_name(t)
        return val

    def push_type(self, val):
        """Types (only) are allowed to shadow"""
        t = type(val)
        logging.debug(f'{t} = {val}')
        if t in self.t_v:
            if t in self.args:
                del self.args[self.args[t]]
                del self.args[t]
            else:
                raise Exception(f'{val} can\'t replace {t}={self.t_v[t]}')
        self.t_v[t] = val

    def push_name(self, n, val):
        # Can _replace_
        if n in self.n_v:
            self.n_v[n] = val
            logging.debug(f'{n} = {val}')
            return

        # Cannot shadow or mutate in higher context.
        try:
            self.lookup_by_name(n)
        except KeyError:
            logging.debug(f'{n} = {val}')
            self.n_v[n] = val
        else:
            raise Exception(f'existing name {n}')

    def result(self):
        if len(self.t_v) == 0:
            return None
        if len(self.t_v) == 1:
            # TODO right way
            # TODO Check only unnamed values once destructuring
            return list(self.t_v.values())[0]
        else:
            raise Exception(f'multiple values: {self.t_v.values()}')

    def copy(self):
        return Context(self.parent, self.n_v.copy(), self.t_v.copy(), self.args.copy(), self.args_dupe_types.copy())

    def new_function_context(self, s_c, args):
        """
        functions on eval take a copy of the paragraph level context available at definition time
        (in self.c)

        (note this is lexical-ish scoping)
        """
        dupes = find_dupes(args.values())
        new_c = Context(self.copy(), args_dupe_types=dupes)
        for (n, t) in args.items():
            # Can only take names from sentence context
            # (i.e. destructured struct)
            if n in s_c.n_v:
                v = s_c.n_v[n]
                if type(v) is not t:
                    raise Exception(f'named var {n} incompatible with type {t} (got {type(t)})')
            elif t in self.args_dupe_types:
                raise Exception(f'unable to get {n} - dupe function types unsupported TODO')
            else:
                v = s_c.pop_type(t)
            new_c.push_name(n, v)
            if t not in new_c.args_dupe_types:
                new_c.push_type(v)
                new_c.args[t] = n
                new_c.args[n] = t
        return new_c

    def __str__(self):
        from pprint import pformat
        res = f'  {pformat(self.n_v)}\n  --{pformat(self.t_v)}'
        if self.parent:
            return res + '\n' + str(self.parent)
        else:
            return res


def main(fname, *args):
    global program
    def p(s):
        print(s)
    c = Context()
    c.push_name('print_s', make_builtin(print, dict(s=str)))
    c.push_name('print_f', make_builtin(print, dict(f=float)))
    c.push_name('print_l', make_builtin(print, dict(l=list)))
    c.push_name('print_d', make_builtin(print, dict(d=dict)))
    c.push_name('string', str)
    c.push_name('number', float)

    program = model.model_from_file(fname) #, debug=DEBUG)
    program.eval(c)

    code.interact(local={**globals(), **locals()})


if __name__ == '__main__':
    main('example1.pif')
    #main(*sys.argv[1:])
