import logging
import sys
import types

from textx.model import get_model

from context import Context
from exectypes import Struct, Type


def msg_with_position(obj, message):
    # super annoying interface here...
    line, col = get_model(obj)._tx_parser.pos_to_linecol(obj._tx_position)
    return f'position ({line}, {col}) - {obj.__class__.__name__} - {message}'


class ExecutionError(Exception):
    def __init__(self, obj, message):
        super().__init__(msg_with_position(obj, message))


def debug(obj, message="info"):
    logging.debug(msg_with_position(obj, message))


def block_eval(self, c):
    for paragraph in self.paragraphs:
        debug(paragraph)
        for line in paragraph.lines:
            debug(line)
            try:
                res = (line.sentence or line.statement).eval(c)
                if res is None:
                    assert not line.assignment
                elif line.sentence and not line.assignment:
                    # i.e. only push from a sentence by default
                    # swallow things from ifs/whiles/fors to avoid noise
                    c.push_type(res)
                elif line.statement and line.assignment:
                    # if we had a statement line, our result will be leftover
                    # in most situations since they run their code in the same context.
                    # So we throw it out if there is an assignment.
                    c.pop_type(type(res))

                if line.assignment and line.assignment.var != '_':
                    c.push_name(line.assignment.var, res)
            except ExecutionError:
                raise
            except Exception as e:
                # nasty rewrapping... should clean up Context Exception usage.
                raise ExecutionError(line.sentence or line.statement, e) from e

        try:
            c.result()  # validate each paragraph has at most one result
            # TODO this doesn't actually do this?
            # Should check number of results instead? (or start a new context?)
            # Or do we never want to carry an earlier paragraph through
            # (probably good except for REPL? REPL should not parse a block but a Line?)
            # (REPL also confused here because it retains the borked context)
        except ExecutionError:
            raise
        except Exception as e:
            raise ExecutionError(paragraph, e) from e

    logging.debug('function result %s', c.result())
    return c.result()


def sentence_eval(self, c):
    debug(self)
    s_c = Context(c)
    for instruction in self.instructions:
        debug(self, instruction)
        if instruction.pushable and not instruction.exec:
            s_c.push_type(instruction.pushable.eval(c))

        # This implements dot operator tight-binding -
        # i.e. if you have a '.' immediately after an item,
        # we assume that _that_ is the function call. This helps
        # us disambiguate in certain circumstances (e.g. when
        # passing a function to a function).
        # Maybe a misfeature...
        if instruction.exec:
            if instruction.pushable:
                debug(self, 'pushable')
                f = instruction.pushable.eval(c)
            else:
                debug(self, 'functype')
                f = s_c.pop_type(types.FunctionType)

            logging.debug('before func %s: %s', f, s_c)
            val = f(s_c)
            if val is not None:
                s_c.push_type(val)
            logging.debug('after func: %s', s_c)

    return s_c.result()


def function_eval(self, definition_context):
    arg_dict = self.args.eval(definition_context)

    def runnable(s_c):
        exec_context = definition_context.new_function_context(s_c, arg_dict)
        return self.block.eval(exec_context) if self.block else None
        # Or exec_context.result() ?

    return runnable


def if_eval(self, c):
    zipped = zip([self.condition] + (self.elif_conditions or []),
                 [self.block] + (self.elif_blocks or []))
    for (cond, block) in zipped:
        res = cond.eval(c)
        debug(self, 'evaluating condition')
        if res is None:
            raise ExecutionError(self, 'if condition must have result')
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
        return self.function.eval(c)
    elif self.type:
        return self.type.eval(c)
    elif self.struct:
        return self.struct.eval(c)
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
            raise ExecutionError(self, 'while condition must have result')
        elif res:
            last_eval = self.block.eval(c)
        else:
            break
    return last_eval


def type_eval(self, c):
    return Type({entry.name: c.get_name(entry.type) for entry in self.varsWithType})


def struct_eval(self, c):
    s = Struct({k.var: s.eval(c) for (k, s) in zip(self.assigns, self.sentences)})
    if self.type and not s.type.obeys(c.get_name(self.type)):
        raise ExecutionError(self, f'not a valid {self.type}')
    return s


def for_eval(self, c):
    last_eval = None
    for elem in self.sentence.eval(c):
        if not self.var:
            c.push_type(elem)
        elif self.var and self.var != '_':
            c.push_name(self.var, elem)
        last_eval = self.block.eval(c)
    return last_eval
