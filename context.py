import logging

from exectypes import get_type, Type


class TypeContext:
    def __init__(self):
        self.d = {}
        self.custom = set()

    def remove(self, t):
        if isinstance(t, Type):
            self.custom.remove(t)
        del self.d[t]

    def get(self, t):
        if t in self.d:
            return self.d[t]
        
        if not isinstance(t, Type):
            return None
        
        candidates = [candidate for candidate in self.custom if t.obeys(candidate)]
        if not candidates:
            return None
        elif len(candidates) > 1:
            raise KeyError(f'unresolvable ambiguous type {t} - candidates: {candidates}')
        else:
            return self.d[candidates[0]]
    
    def push(self, v):
        t = get_type(v)
        self.d[t] = v
        if isinstance(t, Type):
            self.custom.add(t)

    def copy(self):
        tc = TypeContext()
        tc.d = self.d.copy()
        tc.custom = set(self.custom)
        return tc


# rules:
#  looking up to call a function should only look in current function context
#  looking up a name as a name lookup should look everywhere (traverse indefinitely)
#  any shadowing of names is illegal; shadowing of types is legal if not in current context
#  AND you cannot mutate variables outside your current function context
class Context:
    def __init__(self, parent=None, n_v=None, t_v=None, args=None, args_dupe_types=None):
        self.parent = parent
        self.n_v = n_v or {}
        self.t_v = t_v or TypeContext()
        self.args = args or {}
        self.args_dupe_types = args_dupe_types or set()

    def lookup_by_type(self, t, recurse=0):
        # If we've hit the top level and it wasn't an initial
        # lookup at the top level, report it's not there
        # (too dangerous to slurp things out of top level context)
        # NB first level recursion is just getting out of the SentenceContext,
        # which is uninteresting. Clean up this logic.
        if recurse > 1 and self.parent is None:
            raise KeyError(f'no such type "{t}" in current context')
        elif t in self.args_dupe_types:
            raise KeyError(f'attempting to automatically fill ambiguous type {t} (multiple names for that type in function sig)')
        else:
            res = self.t_v.get(t)
            if res:
                return self, res

        if recurse > 1 or self.parent is None:
            # looks similar to above, huh? Not quite.
            raise KeyError(f'no such type "{t}" in current context')
        else:
            return self.parent.lookup_by_type(t, recurse=recurse + 1)

    def lookup_by_name(self, n):
        if n in self.n_v:
            return self, self.n_v[n]
        elif self.parent is None:
            raise KeyError(f'no such name "{n}" in current context')
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
        self.t_v.remove(t)

    def delete_type(self, n):
        if n in self.args:
            t = self.args[n]
            del self.args[t]
            del self.args[n]
            self.t_v.remove(t)

    def pop_type(self, t):
        c, val = self.lookup_by_type(t)
        c.delete_name(t)
        return val

    def push_type(self, val):
        """Types (only) are allowed to shadow"""
        t = get_type(val)
        logging.debug(f'{t} = {val}')
        v = self.t_v.get(t)
        if v is not None:
            if t in self.args:
                del self.args[self.args[t]]
                del self.args[t]
            else:
                raise Exception(f'{val} can\'t replace {t}={v}')
        self.t_v.push(val)

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
        if len(self.t_v.d) == 0:
            return None
        if len(self.t_v.d) == 1:
            # TODO right way
            # TODO Check only unnamed values once destructuring
            return list(self.t_v.d.values())[0]
        else:
            raise Exception(f'multiple values: {self.t_v.d.values()}')

    def copy(self):
        return Context(self.parent, self.n_v.copy(), self.t_v.copy(), self.args.copy(), self.args_dupe_types.copy())

    def new_function_context(self, s_c, args):
        """
        functions on eval take a copy of the paragraph level context available at definition time
        (in self.c)

        (note this is lexical-ish scoping)
        """
        dupes = _find_dupes(args.values())
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
        res = f'  {pformat(self.n_v)}\n  --{pformat(self.t_v.d)}'
        if self.parent:
            return res + '\n' + str(self.parent)
        else:
            return res


def _find_dupes(it):
    seen = set()
    dupes = set()
    for elem in it:
        if elem not in seen:
            seen.add(elem)
        else:
            dupes.add(elem)
    return dupes
