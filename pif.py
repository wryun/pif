from textx.exceptions import TextXSyntaxError
from textx.metamodel import metamodel_from_file

import codecs
import logging
import os
import sys


from context import Context
import expression
import execution


def make_metamodel():
    mm = metamodel_from_file('grammar.tx', ws=' ')

    classes = mm.namespaces['grammar']

    # magically attach things from modules to automatically
    # constructed classes.
    for cls_name, cls in classes.items():
        eval_name = f'{cls_name.lower().rstrip("0123456789")}_eval'
        for module_vars in map(vars, (expression, execution)):
            if eval_name in module_vars:
                cls.eval = module_vars[eval_name]

    return mm


def make_builtin(fn, args_dict):
    # TODO should have same lookup rules as normal Function.
    # also, this is wacky.
    # Can probably fix it more nicely when I figure out how to do proper
    # type lookups/comparisons.
    # Doing this now because of type equality.
    return lambda s_c: fn(*(s_c.pop_type(t) for (_, t) in args_dict.items()))


def make_context():
    c = Context()
    c.push_name('print_s', make_builtin(print, dict(s=str)))
    c.push_name('print_f', make_builtin(print, dict(f=float)))
    c.push_name('print_l', make_builtin(print, dict(l=list)))
    c.push_name('print_d', make_builtin(print, dict(d=dict)))
    c.push_name('string', str)
    c.push_name('number', float)
    return c


if __name__ == '__main__':
    DEBUG=os.environ.get('PIF_DEBUG') == '1'
    PARSE_DEBUG=os.environ.get('PIF_PARSE_DEBUG') == '1'

    if DEBUG:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    file_name = sys.argv[1]

    with codecs.open(file_name, 'r', 'utf-8') as f:
        prog_str = f.read()

    try:
        program = make_metamodel().model_from_str(prog_str, debug=PARSE_DEBUG)
        result = program.eval(program._tx_parser, make_context())
        if result is not None:
            logging.error('leftover value %s', result)
            sys.exit(4)
    # User facing errors, do not provide stack trace.
    except TextXSyntaxError as e:
        (logging.exception if DEBUG else logging.error)(e)
        sys.exit(2)
    except execution.ExecutionError as e:
        (logging.exception if DEBUG else logging.error)(e)
        sys.exit(3)
