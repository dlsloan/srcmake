
from singletonrefs import SingletonRefs
from collections import namedtuple

nfaRef = namedtuple('nfaRef', ['ref'])
nfaRef.clone = lambda nr: nr


class MetaNFA(type):
    @property
    def final(cls):
        return cls._final



class nfa(object, metaclass=MetaNFA):
    def __init__(self, condition=None, *, _volitile=False):
        self._condition = condition
        self._links = tuple()
        self._i_volatile = _volitile


    @property
    def _volatile(self):
        return self._i_volatile
    @_volatile.setter
    def _volatile(self, value):
        assert self._i_volatile
        assert value == False
        self._i_volatile = False


    @property
    def condition(self):
        return self._condition
    @condition.setter
    def condition(self, value):
        assert self._i_volatile 
        self._condition = value


    @property
    def links(self):
        return self._links
    @links.setter
    def links(self, value):
        assert self._volatile
        return self._links


    @property
    def final(self):
        return self == nfa.final


    def test_condition(self, s):
        # Final is terminal and sould never be tested
        assert self != nfa.final

        if self.condition is None:
            retval = ('', s)
        else:
            retval = self.condition(s)

        if __debug__ and retval[0] is None:
            assert retval[1] == s
        elif __debug__:
            assert retval[0] + retval[1] == s

        return retval


    def add_links(self, *links):
        with SingletonRefs(f"{__file__}:nfs.modify") as refs:
            return self._add_links(refs, *links)


    def _add_links(self, refs, *links):
        if __debug__ and 'debug_modify_op' in refs:
            for ln in links:
                assert ln not in refs.values()
        other = self.clone()
        other._links = tuple(self._clone_ln_gen(refs, other, *links))
        return other


    def clone(self):
        with SingletonRefs(f"{__file__}:nfs.modify") as refs:
            return self._clone(refs)


    def _clone_ln(self, ln, refs, other):
        if isinstance(ln, nfaRef):
            if 'linkRefObjs' not in refs:
                refs['linkRefObjs'] = set()
            refs['linkRefObjs'].add(other)
            has_self = self in ln.ref
        else:
            has_self = self in ln
        return ln.clone() if has_self else ln

    def _clone_ln_gen(self, refs, other, *extend):
        for ln in self.links:
            yield self._clone_ln(ln, refs, other)
        for ln in extend:
            yield self._clone_ln(ln, refs, other)


    def _clone_ln_complete_gen(self, refs):
        for ln in self._links:
            if isinstance(ln, nfaRef):
                if id(ln.ref) in refs:
                    yield nfaRef(refs[id(ln.ref)])
                    continue
            yield ln

    
    def _clone_complete(self, refs):
        if 'linkRefObjs' in refs:
            for other in refs['linkRefObjs']:
                other._links = tuple(other._clone_ln_complete_gen(refs))


    def _clone(self, refs):
        refs.set_on_complete(f"{__file__}:nfa.clone_complete", self._clone_complete)
        if id(self) in refs:
            return refs[id(self)]
        other = nfa(condition=self._condition)
        refs[id(self)] = other
        other._links = tuple(self._clone_ln_gen(refs, other))
        return other


    def modify(self):
        with SingletonRefs(f"{__file__}:nfs.modify") as refs:
            if __debug__:
                refs['debug_modify_op'] = True
            mod = self._clone(refs)
            return refs.extend_scope(mod)

    def __repr__(self):
        return f"nfa({id(self)})"

    def __contains__(self, node):
        if id(node) == id(self):
            return True
        with SingletonRefs(f"{__file__}:nfs.check") as refs:
            if id(self) in refs:
                return False
            refs[id(self)] = False
            for ln in self.links:
                if isinstance(ln, nfaRef):
                    if node in ln.ref:
                        return True
                else:
                    if node in ln:
                        return True
            return False

nfa._final = nfa()
