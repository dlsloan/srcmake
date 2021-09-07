import collections

nfa_link = collections.namedtuple('nfa_link', ('prev', 'node'))
nfa_match = collections.namedtuple('nfa_match', ('text', 'ch', 'line'))

class nfa:
    def __init__(self, condition=None):
        self.condition = condition
        self.next = []
        self.terminal = True

    def _terminal_nodes(self, touched):
        if self in touched:
            return []
        touched.add(self)
        ret = []
        for node in self.next:
            ret.extend(node._terminal_nodes(touched))
        if self.terminal:
            ret.append(self)
        return ret

    def terminal_nodes(self):
        return self._terminal_nodes(set())

    def _extend(self, extension, touched):
        if self in touched:
            return
        touched.add(self)
        for node in self.next:
            node._extend(extension, touched)
        if self.terminal:
            self.next.extend(extension)
            self.terminal = False

    def extend(self, extend_with):
        if type(extend_with) == type(self):
            extend_with = [extend_with]
        self._extend(extend_with, set())

    def _loop_connect(self, targ, touched):
        if self in touched:
            return
        touched.add(self)
        for node in self.next:
            node._loop_connect(targ, touched)
        if self.terminal:
            self.next.extend(targ)

    def loop_connect(self, targ):
        if type(targ) == type(self):
            targ = [targ]
        self._loop_connect(targ, set())

    def _branch(self, targ, touched):
        if self in touched:
            return
        touched.add(self)
        for node in self.next:
            node._branch(targ, touched)
        if self.terminal:
            self.next.append(targ)

    def branch(self, targ):
        container = nfa()
        container.extend(targ)
        self._branch(targ, set())
        return container

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
        to_check = steps[-1] if len(steps) else [nfa_link(None, self)]
        for node in to_check:
            if node.node.terminal:
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
            for node in self.next:
                new_connections.extend(node.test(ch, tested, prev))
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
