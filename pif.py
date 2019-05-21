from textx.exceptions import TextXSyntaxError
from textx.metamodel import metamodel_from_file

import argparse
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


def run_program(mm, prog_str, context=None, parse_debug=False):
    if not context:
        context = make_context()

    return mm.model_from_str(prog_str, debug=parse_debug).eval(context)


def setup_readline():
    import readline
    import atexit

    histfile = os.path.join(os.path.expanduser("~"), ".pif_history")

    try:
        readline.read_history_file(histfile)
        h_len = readline.get_current_history_length()
    except FileNotFoundError:
        open(histfile, 'wb').close()
        h_len = 0

    def save():
        readline.set_history_length(10000)
        readline.append_history_file(readline.get_current_history_length() - h_len, histfile)
    atexit.register(save)


def run_repl(mm, parse_debug=False):
    setup_readline()

    c = make_context()
    while True:
        try:
            line = input(']] ')
        except EOFError:
            print()
            return 0
        try:
            print('<-', run_program(mm, line + '\n', context=c, parse_debug=parse_debug))
        except TextXSyntaxError as e:
            logging.error(e)
            continue
        except execution.ExecutionError as e:
            logging.error(e)
            continue


def run_files(mm, file_names, parse_debug=False):
    try:
        for fname in file_names:
            with open(fname) as f:
                prog_str = f.read()
            result = run_program(mm, prog_str, parse_debug=parse_debug)
            if result is not None:
                logging.error('leftover value %s', result)
                return 4
    # User facing errors, do not provide stack trace.
    except TextXSyntaxError as e:
        (logging.exception if args.verbosity > 2 else logging.error)(e)
        return 2
    except execution.ExecutionError as e:
        (logging.exception if args.verbosity > 2 else logging.error)(e)
        return 3


def main(args):
    parse_debug = args.verbosity > 3
    logging.basicConfig(level={
        0: logging.ERROR, 1: logging.WARNING, 2: logging.INFO, 3: logging.DEBUG
    }.get(args.verbosity, logging.DEBUG))

    mm = make_metamodel()

    if not args.files:
        code = run_repl(mm, parse_debug=parse_debug)
    else:
        code = run_files(mm, args.files, parse_debug=parse_debug)

    sys.exit(code)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Parameter Inference Footling (PIF)')
    parser.add_argument('files', nargs='*', help='files to execute (leave empty for REPL)')
    parser.add_argument('-v', '--verbosity', type=int, choices=[0, 1, 2, 3, 4], default=1)
    main(parser.parse_args())
