import collections
import threading

nfa_link = collections.namedtuple('nfa_link', ('prev', 'node'))
nfa_match = collections.namedtuple('nfa_match', ('text', 'ch', 'line', 'named', 'name'), defaults=(None,))

_local = threading.local()

def human_id(self):
    if id(self) not in human_id.ids:
        human_id.ids[id(self)] = human_id.count
        human_id.count += 1
    return human_id.ids[id(self)]

human_id.count = 0
human_id.ids = {}

def once(_def=None):
    def once_dec(fn):
        def once_wrap(self, *pargs, **kargs):
            if not hasattr(_local, fn.__name__):
                setattr(_local, fn.__name__, None)

            check = getattr(_local, fn.__name__)
            if check is None:
                check = set([self])
                setattr(_local, fn.__name__, check)
                try:
                    return fn(self, *pargs, **kargs)
                finally:
                    setattr(_local, fn.__name__, None)

            if self in check:
                return list(_def) if isinstance(_def, list) else _def
            check.add(self)
            return fn(self, *pargs, **kargs)
        once_wrap.__name__ = fn.__name__
        return once_wrap
    return once_dec

class nfa:
    _local = threading.local()

    def __init__(self):
        self.next = []
        self._terminal = True
        self.env = None

    def clone(self):
        partials = {}
        self._partial_clone(partials)
        return self._finish_clone(partials, set())

    def clone_empty(self):
        return nfa()

    def copy_non_ref_to(self, target):
        target._terminal = self._terminal

    def _partial_clone(self, partials):
        if id(self) in partials:
            return
        partial = self.clone_empty()
        partials[id(self)] = partial
        self.copy_non_ref_to(partial)
        for node in self.next:
            node._partial_clone(partials)
        return

    def _finish_clone(self, partials, complete):
        if id(self) in complete:
            return
        complete.add(id(self))
        partial = partials[id(self)]
        for node in self.next:
            partial_node = partials[id(node)]
            partial.next.append(partial_node)
            node._finish_clone(partials, complete)
        return partial


    def set_env(self, env):
        pass

    def is_terminal(self, stack):
        return self._terminal

    def can_terminate_empty(self, stack, env=None):
        return self._can_terminate_empty_inner(stack, set(), env)

    def _can_terminate_empty_inner(self, stack, tested, env):
        if (self, stack) in tested:
            return False
        if type(self) == ref_nfa and self in stack:
            return False
        if env is not None and env != self.env:
            self.env = env
            self.set_env(env)
        tested.add((self, stack))
        return self._can_terminate_empty(stack, tested, env)

    def _can_terminate_empty(self, stack, tested, env):
        if self.is_terminal(stack):
            return True
        for node in self.next:
            if node._can_terminate_empty_inner(stack, tested, env):
                return True
        return False

    @once([])
    def terminal_nodes(self):
        return self._terminal_nodes()

    def _terminal_nodes(self):
        ret = []
        for node in self.next:
            ret.extend(node.terminal_nodes())
        if self._terminal:
            ret.append(self)
        return ret

    @once()
    def extend(self, extend_with):
        if type(extend_with) != list and type(extend_with) != tuple:
            extend_with = [extend_with]
        self._extend(extend_with)

    def _extend(self, extension):
        for node in self.next:
            node.extend(extension)
        if self._terminal:
            self.next.extend(extension)
            self._terminal = False

    @once()
    def loop_connect(self, targ):
        if type(targ) != list and type(targ) != tuple:
            targ = [targ]
        self._loop_connect(targ)

    def _loop_connect(self, targ):
        for node in self.next:
            node.loop_connect(targ)
        if self._terminal:
            self.next.extend(targ)

    @once()
    def branch(self, targ):
        container = nfa()
        container.extend(targ)
        self._branch(targ)
        return container

    def _branch(self, targ):
        for node in self.next:
            node.branch(targ)
        if self._terminal:
            self.next.append(targ)

    def test(self, in_ch, stack, stack_actions, tested, *, env=None):
        if (self, stack) in tested:
            return []
        tested.add((self, stack))

        if type(self) == ref_nfa:
            for action in stack_actions:
                if type(action) == stack_push:
                    if (action.node == self):
                        return []

        if env is not None and env != self.env:
            self.env = env
            self.set_env(env)

        results, tested_true = self._test(in_ch, stack, stack_actions, tested)
        results = list(results)
        if tested_true and self.is_terminal(stack):
            results.append(nfa_result(nfa.END_NFA, stack_actions))
        return results

    def _test(self, in_ch, stack, stack_actions, tested):
        results = []
        for node in self.next:
            results.extend(node.test(in_ch, stack, stack_actions, tested, env=self.env)), True
        return results, self != nfa.END_NFA

    def parse(self, text, env=None):
        parser = nfa_parser(self, env=env)
        return parser.parse(text)

    def __repr__(self):
        if self == nfa.END_NFA:
            return "nfa(END)"
        else:
            return f"nfa({self._terminal}, {self.next})"

nfa.END_NFA = nfa()


class value_nfa(nfa):
    def __init__(self, condition):
        super().__init__()
        self.condition = condition

    def _test(self, in_ch, stack, stack_actions, tested):
        if self.condition(in_ch):
            return (nfa_result(node, stack_actions) for node in self.next), True
        else:
            return [], False

    def _can_terminate_empty(self, stack, tested, env):
        return False

    def _partial_clone(self, partials):
        partial = super()._partial_clone(partials)
        if partial is not None:
            partial.condition = self.condition
        return partial

    def clone_empty(self):
        return value_nfa(None)

    def copy_non_ref_to(self, target):
        super().copy_non_ref_to(target)
        target.condition = self.condition

    def __repr__(self):
        return f"vnfa({human_id(self)})"


class ref_nfa(nfa):
    def __init__(self, name):
        super().__init__()
        self.name = name
        self.ref = None

    def set_env(self, env):
        self.ref = env.get_inner(self.name)

    def _test(self, in_ch, stack, stack_actions, tested):
        return self.ref.test(in_ch, stack + (self,), stack_actions + (stack_push(self),), tested, env=self.env), False

    def _can_terminate_empty(self, stack, tested, env):
        return self.ref._can_terminate_empty_inner(stack + (self, ), tested, env)

    def clone_empty(self):
        return ref_nfa(None)

    def copy_non_ref_to(self, target):
        super().copy_non_ref_to(target)
        target.name = self.name

    def __repr__(self):
        return f"rnfa({self._terminal}, {self.name}, {self.next})"


class err_mark_nfa(nfa):
    def __init__(self, inner, err_message):
        super().__init__()
        self.ref = inner
        self.err_message = err_message

    def _test(self, in_ch, stack, stack_actions, tested):
        return self.ref.test(in_ch, stack + (self,), stack_actions + (stack_push(self),), tested, env=self.env), False

    def _can_terminate_empty(self, stack, tested, env):
        return self.ref._can_terminate_empty_inner(stack + (self, ), tested, env)

    def clone_empty(self):
        return err_mark_nfa(None, None)

    def copy_non_ref_to(self, target):
        super().copy_non_ref_to(target)
        target.err_message = self.err_message

    def _partial_clone(self, partials):
        if id(self) in partials:
            return
        super()._partial_clone(partials)
        self.ref._partial_clone(partials)

    def _finish_clone(self, partials, complete):
        if id(self) in complete:
            return
        partial = super()._finish_clone(partials, complete)
        partial.ref = partials[id(self.ref)]
        self.ref._finish_clone(partials, complete)
        return partial

    def __repr__(self):
        return f"errnfa({self._terminal}, {self.ref}, {self.err_message}, {self.next})"

class pop_nfa(nfa):
    def __init__(self):
        super().__init__()

    def _test(self, in_ch, stack, stack_actions, tested):
        upper = stack[-1]
        results = []
        for node in upper.next:
            results.extend(node.test(in_ch, stack[:-1], stack_actions + (stack_pop(stack[-1]),), tested, env=self.env))
        return results, True

    def is_terminal(self, stack):
        return stack[-1].is_terminal(stack[:-1])

    def _can_terminate_empty(self, stack, tested, env):
        ref_node = stack[-1]
        stack = stack[:-1]
        if ref_node.is_terminal(stack):
            return True
        for node in ref_node.next:
            if node._can_terminate_empty_inner(stack, tested, env):
                return True
        return False

    def clone_empty(self):
        return pop_nfa()

    def __repr__(self):
        return f"pnfa()"


doc_pos = collections.namedtuple('doc_pos', ('ch', 'line', 'index'))


class stack_push:
    def __init__(self, node):
        self.node = node


class stack_pop:
    def __init__(self, node):
        self.node = node


class nfa_step:
    @classmethod
    def from_result(cls, res, prev_step):
        return nfa_step(res.node, index=prev_step.index + 1, prev=prev_step, stack_actions=res.stack_actions)

    def __init__(self, node, *, index, prev=None, stack_actions=None):
        self.prev = prev
        self.node = node
        self.index = index
        self.stack_actions = stack_actions if stack_actions else []
        self.stack = prev.stack if prev else tuple()
        for action in self.stack_actions:
            if type(action) == stack_push:
                self.stack += (action.node,)
            else:
                self.stack = self.stack[:-1]

    def __repr__(self):
        return f"nfa_step({self.prev} -> {self.node}, {self.stack}.{self.stack_actions})"


class nfa_result:
    def __init__(self, node, stack_actions):
        self.node = node
        self.stack_actions = stack_actions


# TODO: Checks for infinite empty recursion
class nfa_parser:
    def __init__(self, root, env=None):
        self.root = root
        self.env = env
        self.active = [nfa_step(root, index=0)]
        if self.active[0].node.can_terminate_empty(tuple(), env=env):
            self.active.append(nfa_step(nfa.END_NFA, index=0))
        self.last_active = None
        self.indexer = []
        self.ch = 0
        self.line = 0
        self.index = 0

    def parse(self, text):
        if len(text) == 0 or text[-1] != 0:
            text += b'\0'
        self.text = text
        for in_ch in text:
            self.parse_ch(in_ch)
            if not len(self.active):
                if in_ch != 0:
                    self.raiseParsingError(self.last_active)
                else:
                    self.ch = self.indexer[-1].ch
                    self.line = self.indexer[-1].line
                    self.index = self.indexer[-1].index
                    self.indexer = self.indexer[:-1]
                    self.active = self.last_active
                    break
        self.indexer.append(doc_pos(self.ch, self.line, self.index))
        self.active.append(None)
        for step in self.active:
            if step is None or step.node == nfa.END_NFA or step.node.can_terminate_empty(step.stack):
                break
        if step is None:
                self.raiseParsingError(self.active)
        return self.gen_match(step)

    def raiseParsingError(self, active):
        message = None
        step = None
        for step in active:
            if step is None:
                continue
            if type(step.node) == err_mark_nfa:
                message = step.node.err_message
                break
            for node in reversed(step.stack):
                if type(node) == err_mark_nfa:
                    message = node.err_message
                    break
            if message is not None:
                break
        if step is None:
            step = active[0]
        raise ParsingError(*self.indexer[-1], partial=self.gen_match(step), msg=message)

    def parse_ch(self, in_ch):
        self.indexer.append(doc_pos(self.ch, self.line, self.index))
        self.index += 1
        if in_ch == b'\n'[0]:
            self.ch = 0
            self.line += 1
        else:
            self.ch += 1
        next_active = []
        tested = set()
        for node_step in self.active:
            results = list(node_step.node.test(in_ch, node_step.stack, tuple(), tested, env=self.env))
            next_active.extend(nfa_step.from_result(res, node_step) for res in results)
        self.last_active = self.active
        self.active = next_active

    def gen_match(self, step):
        self.indexer.append(doc_pos(self.ch, self.line, self.index))
        root_end = step.index
        end_positions = [self.indexer[step.index]] * len(step.stack)
        roots = []
        for i in range(len(step.stack) + 1):
            roots.append([])
        # terminal pops are special (index is off by one from others)
        while len(step.stack_actions) and type(step.stack_actions[-1]) == stack_pop:
            roots.append([])
            end_positions.append(self.indexer[step.index])
            step.stack_actions = step.stack_actions[:-1]

        while step is not None:
            while len(step.stack_actions):
                action = step.stack_actions[-1]
                step.stack_actions = step.stack_actions[:-1]
                if type(action) == stack_push:
                    start_pos = self.indexer[step.index-1]
                    if type(action.node) == ref_nfa:
                        text = self.text[step.index-1:end_positions[-1].index]
                        if len(text) and text[-1] == 0:
                            text = text[:-1]
                        inner = nfa_match(text, start_pos.ch, start_pos.line, [], name=action.node.name)
                        inner.named.extend(roots[-1])
                        roots[-2].insert(0, inner)
                    roots = roots[:-1]
                    end_positions = end_positions[:-1]
                else:
                    assert type(action) == stack_pop
                    roots.append([])
                    end_positions.append(self.indexer[step.index-1])
            step = step.prev
        assert len(roots) == 1
        text = self.text[:root_end]
        if len(text) and text[-1] == 0:
            text = text[:-1]
        return nfa_match(text, 0, 0, named=roots[0])


class ParsingError(Exception):
    def __init__(self, ch, line, index, partial, msg=None):
        super().__init__(msg)
        self.ch = ch
        self.line = line
        self.index = index
        self.partial = partial
        self.message = msg
