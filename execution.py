import logging
import sys
import types


from context import Context


class ExecutionError(Exception):
    def __init__(self, model, message):
        super().__init__(message)
        self.model = model


def debug(m, s="info"):
    # hard to do this properly because need access to program...
    #line, col = m._tx_parser.pos_to_linecol(m._tx_position)
    line = 1
    col = 1
    #logging.debug('line %d col %d - %s - %s', line, col, m.__class__.__name__, s)


def attach_model(model, e):
    if not hasattr(e, 'model'):
        e.model = model


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
            except Exception as e:
                attach_model(line.sentence or line.statement, e)
                raise

        try:
            c.result()  # validate each paragraph has at most one result
        except Exception as e:
            attach_model(line.paragraph, e)
            raise

    logging.debug('function result %s', c.result())
    return c.result()


def sentence_eval(self, c):
    debug(self)
    s_c = Context(c)
    for instruction in self.instructions:
        if instruction == '.':
            logging.debug('before func: %s', s_c)
            val = s_c.pop_type(types.FunctionType)(s_c)
            if val is not None:
                s_c.push_type(val)
            logging.debug('after func: %s', s_c)
        else:
            s_c.push_type(instruction.eval(c))

    return s_c.result()


def function_eval(self, definition_context):
    arg_dict = self.args.eval(definition_context)

    def runnable(s_c):
        exec_context = definition_context.new_function_context(s_c, arg_dict)
        return self.block.eval(exec_context)

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
