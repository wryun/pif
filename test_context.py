"""
Test Context class... but attempt to exercise by running programs (i.e. functional not unit).
"""
from unittest import TestCase, skip

from textx.exceptions import TextXSyntaxError
from execution import ExecutionError
from pif import run_program, make_metamodel


mm = make_metamodel()


def run(prog_str):
    return run_program(mm, prog_str)


class LookupByType(TestCase):
    def test_in_sentence(self):
        run('''
        eat_s "x" .
        ''')

    def test_missing_in_sentence(self):
        with self.assertRaisesRegex(ExecutionError, r'no such type.*in current context'):
            run('''
            eat_s .
            ''')

    def test_in_paragraph(self):
        run('''
        "x"
        eat_s .
        ''')

    def test_missing_in_paragraph(self):
        with self.assertRaisesRegex(ExecutionError, r'no such type.*in current context'):
            run('''
            1.0
            eat_s .
            ''')

    def test_in_block(self):
        run('''
        "x"

        eat_s .
        ''')

    def test_missing_in_block(self):
        with self.assertRaisesRegex(ExecutionError, r'no such type.*in current context'):
            run('''
            1.0

            eat_s .
            ''')

    def test_in_function_top_level(self):
        """Can't pull vars out of top level in function context. Because it seems scary."""
        with self.assertRaisesRegex(ExecutionError, r'no such type.*in current context'):
            run('''
            "x"
            func () eat_s. end .
            ''')

    def test_in_function_sub_level(self):
        """Can pull vars out of previous level if all in functions, because helps with quick functions"""
        run('''
        func ()
            "x"
            fs2 = func ()
                eat_s.
            end
            fs2.
        end.
        ''')

    def test_in_function_copy(self):
        """Can even reuse (because closure, each gets its own copy of the context)"""
        run('''
        func ()
            "x"
            fs2 = func ()
                eat_s.
            end
            fs2.
            fs2.
            fs2.
        end.
        ''')