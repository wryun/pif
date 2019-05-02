from textx.metamodel import metamodel_from_file

import logging
import os
import sys

from context import Context


def make_metamodel():
    mm = metamodel_from_file('grammar.tx', ws=' ')

    # modules with our evals
    import expression
    import execution

    classes = mm.namespaces['grammar']

    # magically attach things from modules to automatically
    # constructed classes.
    for cls_name, cls in classes.items():
        eval_name = f'{cls_name.lower().rstrip("0123456789")}_eval'
        for module_vars in map(vars, (expression, execution)):
            if eval_name in module_vars:
                cls.eval = module_vars[eval_name]

    return mm, classes


def make_builtin(fn, args_dict):
    # TODO should have same lookup rules as normal Function.
    # also, this is wacky.
    # Can probably fix it more nicely when I figure out how to do proper
    # type lookups/comparisons.
    # Doing this now because of type equality.
    return lambda s_c: fn(*(s_c.pop_type(t) for (_, t) in args_dict.items()))


def main(fname, *args):
    mm, classes = make_metamodel()
    c = Context()
    c.push_name('print_s', make_builtin(print, dict(s=str)))
    c.push_name('print_f', make_builtin(print, dict(f=float)))
    c.push_name('print_l', make_builtin(print, dict(l=list)))
    c.push_name('print_d', make_builtin(print, dict(d=dict)))
    c.push_name('string', str)
    c.push_name('number', float)

    program = mm.model_from_file(fname, debug=PARSE_DEBUG)
    try:
        result = program.eval(c)
        if result is not None:
            logging.error('leftover value %s', result)
            sys.exit(1)
    except Exception as e:
        if hasattr(e, 'model'):
            line, col = program._tx_parser.pos_to_linecol(e.model._tx_position)
            (logging.exception if DEBUG else logging.error)('line %d col %d - %s - %s', line, col, e.model.__class__.__name__, e)
        else:
            logging.exception('unexpected failure')
        sys.exit(1)


if __name__ == '__main__':
    DEBUG=os.environ.get('PIF_DEBUG') == '1'
    PARSE_DEBUG=os.environ.get('PIF_PARSE_DEBUG') == '1'

    if DEBUG:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    main('example1.pif')
    #main(*sys.argv[1:])
