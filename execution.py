import logging
import sys
import types


from context import Context


def msg_with_position(parser, model, message):
    # super annoying interface here...
    line, col = parser.pos_to_linecol(model._tx_position)
    return f'position ({line}, {col}) - {model.__class__.__name__} - {message}'


class ExecutionError(Exception):
    def __init__(self, parser, model, message):
        super().__init__(msg_with_position(parser, model, message))


def debug(parser, model, message="info"):
    logging.debug(msg_with_position(parser, model, message))


def block_eval(self, parser, c):
    for paragraph in self.paragraphs:
        debug(parser, paragraph)
        for line in paragraph.lines:
            debug(parser, line)
            try:
                res = (line.sentence or line.statement).eval(parser, c)
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
                raise ExecutionError(parser, line.sentence or line.statement, e) from e

        try:
            c.result()  # validate each paragraph has at most one result
            # TODO this doesn't actually do this?
            # Should check number of results instead? (or start a new context?)
        except ExecutionError:
            raise
        except Exception as e:
            raise ExecutionError(parser, line.paragraph, e) from e

    logging.debug('function result %s', c.result())
    return c.result()


def sentence_eval(self, parser, c):
    debug(parser, self)
    s_c = Context(c)
    for instruction in self.instructions:
        if instruction == '.':
            logging.debug('before func: %s', s_c)
            val = s_c.pop_type(types.FunctionType)(s_c)
            if val is not None:
                s_c.push_type(val)
            logging.debug('after func: %s', s_c)
        else:
            s_c.push_type(instruction.eval(parser, c))

    return s_c.result()


def function_eval(self, parser, definition_context):
    arg_dict = self.args.eval(parser, definition_context)

    def runnable(s_c):
        exec_context = definition_context.new_function_context(s_c, arg_dict)
        return self.block.eval(parser, exec_context)

    return runnable


def if_eval(self, parser, c):
    zipped = zip([self.condition] + (self.elif_conditions or []),
                 [self.block] + (self.elif_blocks or []))
    for (cond, block) in zipped:
        res = cond.eval(parser, c)
        debug(parser, self, 'evaluating condition')
        if res is None:
            raise ExecutionError(parser, self, 'if condition must have result')
        elif res:
            debug(parser, self, 'block eval')
            return block.eval(parser, c)

    if self.else_block:
        return self.else_block.eval(parser, c)

    return None


def pushable_eval(self, parser, c):
    if self.var:
        return c.get_name(self.var)
    elif self.expr:
        return self.expr.e.eval(parser, c)
    elif self.function:
        logging.debug(c)
        return self.function.eval(parser, c)
    elif hasattr(self.rawval, 'sentences'):
        return [s.eval(parser, c) for s in self.rawval.sentences]
    elif hasattr(self.rawval, 'keys'):
        return {k.eval(parser, c): v.eval(parser, c) for (k, v) in zip(self.rawval.keys, self.rawval.values)}
    else:
        return self.rawval


def while_eval(self, parser, c):
    last_eval = None
    while True:
        res = self.condition.eval(parser, c)
        if res is None:
            raise ExecutionError(parser, self, 'while condition must have result')
        elif res:
            last_eval = self.block.eval(parser, c)
        else:
            break
    return last_eval


def types_eval(self, parser, c):
    return {entry.name: c.get_name(entry.type) for entry in self.varsWithType}


def for_eval(self, parser, c):
    last_eval = None
    for elem in self.sentence.eval(parser, c):
        if not self.var:
            c.push_type(elem)
        elif self.var and self.var != '_':
            c.push_name(self.var, elem)
        last_eval = self.block.eval(parser, c)
    return last_eval
