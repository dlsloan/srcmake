import collections

nfa_link = collections.namedtuple('nfa_link', ('prev', 'node'))
nfa_match = collections.namedtuple('nfa_match', ('text', 'ch', 'line'))

class nfa:
    def __init__(self, condition=None):
        self.condition = condition
        self.next = []
        self.exits = [self]

    def extend(self, nfa_inst):
        for i in range(len(self.exits)):
            if self.exits[i] == self:
                self.exits[i].next.append(nfa_inst)
            else:
                self.exits[i].extend(nfa_inst)
            self.exits[i] = nfa_inst

    def parse(self, src):
        steps = []
        pos_track = []
        last_nfas = [self]
        ch_pos = 0
        line_pos = 0
        for ch in src:
            pos_track.append((ch_pos, line_pos))
            tested = set()
            connections = []
            if len(steps):
                prev = (link.node for link in steps[-1])
            else:
                prev = [self]
            for node in prev:
                for nfa_inst in node.next:
                    connections.extend(nfa_inst.test(ch, tested, node))
            if not len(connections):
                raise ParsingError(*pos_track[-1], partial=nfa_match(src[:len(steps)], 0, 0))
            steps.append(connections)
            if ch == b'\n'[0]:
                line_pos += 1
                ch_pos = 0
            else:
                ch_pos += 1
        step = None
        for node in steps[-1]:
            if len(node.node.next) == 0:
                step = node
                break
        if step is None:
            raise ParsingError(ch_pos, line_pos, partial=nfa_match(src[:len(steps)], 0, 0))
        return nfa_match(src, 0, 0)

    def test(self, ch, tested, prev):
        if self in tested:
            return []
        tested.add(self)
        if self.condition is None:
            new_connections = []
            for nfa_inst in self.next:
                new_connections.extend(nfa_inst.test(ch, tested, prev))
            return new_connections
        elif self.condition(ch):
            return [nfa_link(prev, self)]
        else:
            return []

class ParsingError(Exception):
    def __init__(self, ch, line, partial, msg=None):
        super().__init__(msg)
        self.ch = ch
        self.line = line
        self.partial = partial
