def parse(src):
    el = None
    while len(src):
        el, src = parse_partial(src, el)
    return el.simplify()

def parse_partial(src, prev):
    if src[0:1] == b'[':
        el, src = char_class.parse(src)
    elif src[0:1] == b'.':
        el = char_class([], invert=True)
        src = src[1:]
    elif len(src) > 1 and src[0:1] == b'\\' and src[1:2] in char_class.short_hands:
        src = src[1:]
        el = char_class.short_hands[src[0:1]].clone()
        src = src[1:]
    elif src[0:1] == b'|':
        el = either(prev, None)
        src = src[1:]
        prev = None
    elif src[0:1] == b'(':
        el, src = group.parse(src)
    elif len(src) > 2 and src[0:2] == b'{:':
        el, src = named.parse(src)
    elif len(src) > 2 and src[0:2] == b'{!':
        el, src = terminal.parse(src)
    elif src[0:1] in rep.short_hands or src[0:1] == b'{':
        el, src = rep.parse(src, prev)
        prev = None
    else:
        el, src = const.parse(src)

    if prev is not None:
        el = prev.merge(el)

    return el, src

class expr:
    def merge(self, next_el):
        return seq(self, next_el)

    def simplify(self):
        return self

class seq(expr):
    def __init__(self, *sequence):
        self.sequence = []
        for el in sequence:
            if type(el) == seq:
                self.sequence.extend(el.sequence)
            else:
                self.sequence.append(el)

    def __eq__(self, other):
        if type(self) != type(other) or len(self.sequence) != len(other.sequence):
            return False
        for i in range(len(self.sequence)):
            if self.sequence[i] != other.sequence[i]:
                return False
        return True

    def __repr__(self):
        return 'seq(' + ', '.join(repr(i) for i in self.sequence) + ')'

    def merge(self, next_el):
        assert len(self.sequence)
        el = self.sequence[-1].merge(next_el)
        if el != seq(self.sequence[-1], next_el):
            self.sequence[-1] = el
            return self
        self.sequence.append(next_el)
        return self

    def simplify(self):
        i = 0
        while i < len(self.sequence)-1:
            if hasattr(self.sequence[i], 'combine'):
                try:
                    el = self.sequence[i].combine(self.sequence[i+1])
                    self.sequence = self.sequence[:i] + [el] + self.sequence[i+2:]
                except InvalidCombinationError:
                    i += 1
            else:
                i += 1
        return self if len(self.sequence) > 1 else self.sequence[0]

    def rep_propogate(self, fn):
        if hasattr(self.sequence[-1], 'rep_propogate'):
            self.sequence[-1].rep_propogate(fn)
        else:
            self.sequence[-1] = fn(self.sequence[-1])

class const(expr):
    @classmethod
    def parse(cls, src):
        if src[0:1] == b'\\':
            src = src[1:]
            if src[0:1] in escape_map:
                return const(escape_map[src[0:1]]), src[1:]
        assert len(src)
        return const(src[0:1]), src[1:]

    def __init__(self, src):
        self.val = src

    def __eq__(self, other):
        return type(self) == type(other) and self.val == other.val

    def __repr__(self):
        return 'const("' + ''.join(as_ch(bytes([c])) for c in self.val) + '")'

    def combine(self, next_el):
        if type(next_el) == type(self):
            return const(self.val + next_el.val)
        else:
            raise InvalidCombinationError()

def char_range(start, stop):
    return list(bytes([i]) for i in range(ord(start), ord(stop)+1))

def as_ch(byte):
    e = {
        b'\\': "\\\\",
        b'\n': "\\n",
        b'\r': "\\r",
        b'\b': "\\b",
        b'\t': "\\t",
        b'"': "\\\"",
        b'\0': "\\0",
    }
    if byte in e:
        return e[byte]
    try:
        return byte.decode()
    except:
        return f"\\x{byte[0]:02x}"

class char_class(expr):
    @classmethod
    def parse(cls, src):
        invert = False
        elements = []
        assert src[0:1] == b'['
        src = src[1:]
        if src[0:1] == b'^':
            invert = True
            src = src[1:]
        if src[0:1] == b']' or src[0:1] == b'-':
            elements.append(src[0:1])
            src = src[1:]
        while len(src) and src[0:1] != b']':
            if src[0:1] == b'-' and src[1:2] != b']':
                elements.extend(char_range(elements[-1], src[1:2]))
                src = src[2:]
            elif src[0:1] == b'\\':
                src = src[1:]
                if src[0:1] in cls.short_hands:
                    elements.extend(ch for ch in cls.short_hands[src[0:1]].set)
                elif src[0:1] in escape_map:
                    elements.append(escape_map[src[0:1]])
                else:
                    elements.append(src[0:1])
                src = src[1:]
            else:
                elements.append(src[0:1])
                src = src[1:]
        assert src[0:1] == b']'
        src = src[1:]
        return char_class(elements, invert=invert), src

    def __init__(self, elements, *, invert=False):
        if invert:
            elmts = set(elements)
            self.set = set()
            for i in range(256):
                if bytes([i]) not in elmts:
                    self.set.add(bytes([i]))
        else:
            self.set = set(elements)

    def __eq__(self, other):
        return type(self) == type(other) and self.set == other.set

    def __repr__(self):
        return 'char_class("' + ''.join(as_ch(el) for el in self.set) + '")'

    def clone(self):
        return char_class(self.set)

char_class.short_hands = {
    b'd': char_class(char_range(b'0', b'9')),
    b'D': char_class(char_range(b'0', b'9'), invert=True),
    b'w': char_class(char_range(b'a', b'z') + char_range(b'A', b'Z') + char_range(b'0', b'9') + [b'_']),
    b'W': char_class(char_range(b'a', b'z') + char_range(b'A', b'Z') + char_range(b'0', b'9') + [b'_'], invert=True),
    b's': char_class([b' ', b'\t', b'\r', b'\n']),
    b'S': char_class([b' ', b'\t', b'\r', b'\n'], invert=True),
}

class either(expr):
    def __init__(self, *options):
        self.options = []
        for opt in options:
            if type(opt) == type(self):
                self.options.extend(opt.options)
            else:
                self.options.append(opt)

    def __eq__(self, other):
        return type(self) == type(other) and self.options == other.options

    def merge(self, next_el):
        if self.options[-1] is not None:
            self.options[-1] = self.options[-1].merge(next_el)
        else:
            self.options[-1] = next_el
        return self

    def simplify(self):
        for i in range(len(self.options)):
            self.options[i] = self.options[i].simplify()
        return self

    def __repr__(self):
        return 'either(' + ', '.join(repr(opt) for opt in self.options) + ')'

    def rep_propogate(self, fn):
        if hasattr(self.options[-1], 'rep_propogate'):
            self.options[-1].rep_propogate(fn)
        else:
            self.options[-1] = fn(self.options[-1])

class group(expr):
    @classmethod
    def parse(cls, src):
        assert src[0:1] == b'('
        src = src[1:]
        inner = None
        while len(src) and src[0:1] != b')':
            inner, src = parse_partial(src, inner)
        assert src[0:1] == b')'
        src = src[1:]
        return group(inner), src

    def __init__(self, inner):
        self.inner = inner

    def __eq__(self, other):
        return type(self) == type(other) and self.inner == other.inner

    def __repr__(self):
        return f"group({repr(self.inner)})"

    def simplify(self):
        self.inner = self.inner.simplify()
        return self

class rep(expr):
    short_hands = {
        b'*': (0, None),
        b'+': (1, None),
        b'?': (0, 1),
    }
    
    @classmethod
    def parse_range(cls, src):
        assert src[0:1] == b'{'
        src = src[1:]
        min_val = None
        while len(src) and src[0:1].isdigit():
            if min_val is None:
                min_val = 0
            min_val = min_val * 10 + (src[0] - b'0'[0])
            src = src[1:]
        if src[0:1] == b',':
            max_val = None
            src = src[1:]
            while len(src) and src[0:1].isdigit():
                if max_val is None:
                    max_val = 0
                max_val = max_val * 10 + (src[0] - b'0'[0])
                src = src[1:]
        else:
            max_val = min_val
        assert src[0:1] == b'}'
        src = src[1:]
        return (min_val, max_val), src

    @classmethod
    def parse(cls, src, prev):
        first = src[0:1]
        if first == b'{':
            min_max, src = cls.parse_range(src)
        else:
            assert first in cls.short_hands
            min_max = cls.short_hands[first]
            src = src[1:]
        if hasattr(prev, 'rep_propogate'):
            prev.rep_propogate(lambda el: rep(el, *min_max))
            return prev, src
        else:
            return rep(prev, *min_max), src

    def __init__(self, inner, min, max):
        self.inner = inner
        self.min = min
        self.max = max

    def __eq__(self, other):
        return type(self) == type(other) and self.inner == self.inner and self.min is other.min and self.max is other.max

    def __repr__(self):
        return f"rep({repr(self.inner)}, {self.min}, {self.max})"

class named(expr):
    @classmethod
    def parse(cls, src):
        assert src[0:2] == b'{:'
        src = src[2:]
        name = b''
        while len(src) and src[0:1] != b'}':
            name += src[0:1]
            src = src[1:]
        assert src[0:1] == b'}'
        src = src[1:]
        return named(name), src

    def __init__(self, name):
        self.name = name

    def __eq__(self, other):
        return type(self) == type(other) and self.name == other.name

    def __repr__(self):
        return f"named(\"{self.name}\")"

class terminal(expr):
    @classmethod
    def parse(cls, src):
        assert src[0:2] == b'{!'
        src = src[2:]
        inner = None
        while len(src) and src[0:1] != b'}' and src[0:1] != b':':
            inner, src = parse_partial(src, inner)
        if src[0:1] == b':':
            message = b''
            src = src[1:]
            while len(src) and src[0:1] != b'}':
                message += src[0:1]
                src = src[1:]
        else:
            message = None
        assert src[0:1] == b'}'
        src = src[1:]
        return terminal(inner, message=message), src

    def __init__(self, inner, *, message=None):
        self.inner = inner
        self.message = message

    def __eq__(self, other):
        return type(self) == type(other) and self.inner == other.inner

    def __repr__(self):
        if self.message is not None:
            return f"terminal({repr(self.inner)}, message={self.message})"
        else:
            return f"terminal({repr(self.inner)})"

    def simplify(self):
        self.inner = self.inner.simplify()
        return self

class InvalidCombinationError(Exception):
    pass

escape_map = {
    b'b': b'\b',
    b't': b'\t',
    b'n': b'\n',
    b'r': b'\r',
}