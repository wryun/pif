from unittest import TestCase, skip

from textx.exceptions import TextXSyntaxError
from execution import ExecutionError
from pif import run_program, make_metamodel


mm = make_metamodel()


def run(prog_str):
    return run_program(mm, prog_str)


class SyntaxError(TestCase):
    def test_basic_position(self):
        with self.assertRaises(TextXSyntaxError) as cm:
            run('do nothing end\n')
        self.assertIn('position (1, 1)', str(cm.exception))


class ExecError(TestCase):
    def test_basic_position(self):
        with self.assertRaises(ExecutionError) as cm:
            run('nothing\n')
        self.assertIn('position (1, 1)', str(cm.exception))


class DotOperator(TestCase):
    def test_normal(self):
        self.assertIsNone(run('''
            "foo" eat_s .
        '''))
        self.assertIsNone(run('''
            eat_s "foo" .
        '''))
        self.assertIsNone(run('''
            eat_f ((1 + 1)) .
        '''))

    def test_tightbind(self):
        self.assertIsNone(run('''
            "foo" eat_s.
        '''))
        with self.assertRaises(ExecutionError) as cm:
            run('''
                eat_s "foo".
            ''')


class Function(TestCase):
    def test_basic(self):
        self.assertEqual([1.0, 1.0, 2.0, 3.0, 5.0], run('''
            fib = func (n number)
              a = 0
              b = 1
              while ((n > 1)) do
                n = ((n - 1))
                c = ((a + b))
                a = b
                b = c
              end
              b
            end

            List[fib 1 ., fib 2 ., fib 3 ., fib 4 ., fib 5 .]
        '''))

    def test_empty(self):
        self.assertIsNone(run('''
            fib = func () end
            fib .
        '''))

    def test_recursive(self):
        self.assertEqual([1.0, 1.0, 2.0, 3.0, 5.0], run('''
            fib = func (n number)
              if ((n <= 2)) do
                1
              else
                a = fib ((n - 1)) .
                b = fib ((n - 2)) .
                ((a + b))
              end
            end

            List[fib 1 ., fib 2 ., fib 3 ., fib 4 ., fib 5 .]
        '''))


class List(TestCase):
    def test_define(self):
        self.assertEqual([2.0, 2.0, 3.0], run('''
            List[((1 + 1)), 2, 3]
        '''))


class Dict(TestCase):
    def test_define(self):
        self.assertEqual({1.0: 2.0, 3.0: 4.0}, run('''
            Dict[1=2, 3=4]
        '''))


class Expression(TestCase):
    def test_basic(self):
        self.assertEqual(11.0, run('''
            (( 5 + 2 * 3 ))
        '''))


class For(TestCase):
    def test_basic(self):
        self.assertEqual(6.0, run('''
            sum = 0
            for i in List[1, 2, 3] do
                sum = ((sum + i))
            end
            sum
        '''))

    def test_no_var(self):
        self.assertEqual(6.0, run('''
            sum = 0
            for List[1, 2, 3] do
                sum = ((sum + number))
            end
            sum
        '''))


class If(TestCase):
    def test_basic_success(self):
        self.assertEqual(3, run('''
            if 1 do 3 end
        '''))

    def test_basic_failure(self):
        self.assertEqual(5, run('''
            if 0 do 3 else 5 end
        '''))

    def test_empty_failure(self):
        self.assertIsNone(run('''
            if 0 do 3 end
        '''))


class Comment(TestCase):
    def test_comment(self):
        self.assertEqual('a', run('''
            # comment before
            1 # comment on the line
            'a' # same paragraph continued
            # don't stop the paragraph...
            eat_f.
        '''))