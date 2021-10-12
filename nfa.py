from dataclasses import dataclass
from nfa_old import nfa_parser

class nfa:
    def __init__(self, condition=None, next=None):
        if next is not None:
            self.next = list(next)
        else:
            self.next = []
        self.condition = condition
        if self.condition is not None:
            self.next.append(nfa())

    def is_terminal(self):
        return len(self.next) == 0

    def parse(self, text):
        return nfa_parser(self).parse(text)

    def test_fill(self, in_ch, stack, tested_stacks):
        if stack in tested_stacks:
            return []
        tested_stacks.add(stack)
        pre_stack = stack[:-1]
        if self.condition is not None:
            if self.condition(in_ch):
                return (pre_stack + (node, ) for node in self.next)
        else:
            next_fill = []
            for node in self.next:
                next_fill.extend(node.test_fill(in_ch, pre_stack + (node, ), tested_stacks))
            return next_fill

    def clone(self, clone_state=None):
        if clone_state is None:
            clone_state = clone_refs()
        if self in clone_state:
            return clone_state[self]
        copy = nfa()
        clone_state[self] = copy
        copy.condition = self.condition
        copy.next = []
        for node in self.next:
            copy.next.append(node.clone(clone_state))

class nfa_parser:
    def __init__(self, nfa_root):
        self.nfa_root = nfa_root

    def parse(self, text):
        active_stacks = [(self.nfa_root,)]
        for in_ch in text:
            in_ch = bytes([in_ch])
            active_stacks = self.parse_ch(in_ch, active_stacks)
            if len(active_stacks) == 0:
                raise Exception()
        return text

    def parse_ch(self, in_ch, stacks):
        next_stacks = []
        tested_stacks = set()
        for stack in stacks:
            next_stacks.extend(stack[-1].test_fill(in_ch, stack, tested_stacks))
        return next_stacks
