class rregex:
    _escape_sequences = {
        'd': (ch_range('0', '9'), False),
        'D': (ch_range('0', '9'), True),
        's': ([' ', '\t', '\n', '\r'], False),
        'S': ([' ', '\t', '\n', '\r'], True),
        'w': (ch_range('0', '9') + ch_range('a', 'z') + ch_range('A', 'Z') + ['_'], False),
        'W': (ch_range('0', '9') + ch_range('a', 'z') + ch_range('A', 'Z') + ['_'], True),

        'n': (['\n'], False),
        'r': (['\r'], False),
        't': (['\t'], False),
    }
    def __init__(self, src):
        self.elements = []
        if src is None:
            return
        while len(src):
            src = self.parse(src)

    def parse(self, src):
            if src[0:1] == '(:':
                return self.parse_named(src[2:])
            elif src[0:2] == '(?:':
                return self.parse_group(src[3:])
            elif src[0] == '(':
                return self.parse_group(src[1:])
            elif src[0] == '[':
                return parse_char_class(src[1:])
            elif src[0] == '\\':
                return self.parse_escaped(src[1:]))
            elif src[0] == '|':
                self.elements.append(rregex.Or)
                return src[1:]
            elif src[0] == '?':
                self.elements[-1] = _rre_count(self.elements[-1], 0, 1)
            elif src[0] == '*':
                self.elements[-1] = _rre_count(self.elements[-1], 0)
            elif src[0] == '+':
                self.elements[-1] = _rre_count(self.elements[-1], 1)
            elif src[0] == '.':
                self.elements.append(rregex.Any)
                return src[1:]
            else:
                return self.parse_const(src)

    def parse_named(self, src):
        end = src.index(')')
        self.elements.append(_rre_named(src[:end]))
        return src[end+1:]

    def parse_group(self, src):
        group = rregex(None)
        while len(src) and src[0] != ')':
            src = group.parse(src)
        assert src[0] == ')'
        self.elements.append(group)
        return src[1:]

    def parse_char_class(self, src):
        chars = []
        invert = False
        if src[0] == '^':
            invert = True
            src = src[1:]
        if src[0] == ']' or src[0] == '-':
            chars.append(src[0])
            src = src[1:]

        while len(src) and src[0] != ']':
            if src[0] == '\\':
                chars.extend(self.convert_escape(src[1]))
                src = src[2:]
            elif src[0] == '-' and src[1] != ']':
                chars.extend(ch_range(chars[-1], src[1]))
                src = src[2:]
            else
                chars.extent(src[0])
                src = src[1:]
        assert src[0] == ']'
        self.elements.append(_rre_char_class(chars, invert))
        return src[1:]

    def parse_escaped(self, src):
        if src[0] in _escape_sequences:
            self.elements.append(_rre_char_class(*_escape_sequences[src[0]]).simplify())
        else:
            self.elements.append(_rre_const(src[0]))

        return src[1:]

    def parse_const(self, src):
        self.elements.append(_rre_const(src[0]))
        return src[1:]

class rre_named:
    def __init__(self, name):
        assert re.match("[a-zA-Z_][a-zA-Z0-9_.-]*", name)
        self.name = name

class rre_count:
    def __init__(self, inner, min, max=None):
        self.inner = inner
        self.min = min
        self.max = max

class rre_char_class:
    def __init__(self, chars, invert=False):
        chars = set(chars)
        if self.invert:
            self.chars = set()
            for i in range(256):
                if chr(i) not in chars:
                    self.chars.add(chr(i))
        else:
            self.chars = chars

    def simplify(self):
        if len(self.chars) == 1:
            for ch in self.chars:
                return rre_const(ch)
        return self

class rre_const:
    def __init__(self, val):
        self.val = val