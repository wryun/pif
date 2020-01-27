from frozendict import frozendict


def get_type(v):
    return v.type if isinstance(v, Struct) else type(v)


class Type(frozendict):
    def obeys(self, other):
        return other == {k: v for k, v in self.items() if k in other}


class Struct(frozendict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.type = Type({k: get_type(v) for k, v in self.items()})
