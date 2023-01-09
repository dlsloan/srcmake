import threading

from singletonrefs import SingletonRefs
from collections import namedtuple

nfaRef = namedtuple('nfaRef', ['ref'])

class nfaRef:
    def __init__(self, ref):
        assert ref is not None and isinstance(ref, nfa)
        self._ref = ref

    @property
    def ref(self):
        return self._ref


class MetaNFA(type):
    @property
    def final(cls):
        return cls._final


class nfa(object, metaclass=MetaNFA):
    def __init__(self, condition=None, links=None):
        if links is None:
            links = tuple()
        if __debug__:
            assert condition is None or callable(condition)
            assert isinstance(links, tuple)
            for ln in links:
                assert isinstance(ln, nfa) or isinstance(ln, nfaRef)

        self._condition = condition
        self._links = links

    @property
    def condition(self):
        return self._condition
    @property
    def links(self):
        return self._links
    @property
    def final(self):
        return id(self) == id(nfa.final)

    def test_condition(self, s):
        # Final is terminal and sould never be tested
        assert self != nfa.final
        if self.condition is None:
            if isinstance(s, str):
                retval = ('', s)
            else:
                retval = (b'', s)
        else:
            retval = self.condition(s)
        # Debug checks
        if __debug__ and retval[0] is None:
            assert retval[1] == s
        elif __debug__:
            assert retval[0] + retval[1] == s
        return retval

    def add_links(self, *links):
        vnfa = _vnfa.clone_var(self)
        vnfa.add_links(*links)
        return vnfa.as_invar()

    def extend(self, targ):
        vnfa = _vnfa.clone_var(self)
        vnfa.extend(targ)
        return vnfa.as_invar()

    def clone(self, *, refs=None):
        if self.final:
            return self
        if refs is None:
            refs = {}
        assert isinstance(refs, dict)
        if id(self) in refs:
            return refs[self]
        nfa_ret = nfa(self.condition)
        refs[self] = nfa_ret
        nfa_ret._links = tuple(ln.clone() if isinstance(ln, nfa) else ln for ln in self.links)
        return nfa_ret

    def as_var(self):
        return _vnfa.clone_var(self)

    def __repr__(self):
        return f"nfa({id(self)})"

nfa._final = nfa()


class _vnfa:
    @classmethod
    def clone_var(cls, nfa_rep, *, refs=None):
        if refs is None:
            refs = {}
        assert nfa_rep is not None and isinstance(nfa_rep, nfa)
        assert isinstance(refs, dict)

        if nfa_rep.final or isinstance(nfa_rep, nfaRef):
            return nfa_rep
        if id(nfa_rep) in refs:
            return refs[id(nfa_rep)]
        return _vnfa(nfa_rep=nfa_rep, refs=refs)

    def __init__(self, condition=None, links=None, *, nfa_rep=None, refs=None):
        if nfa_rep is not None:
            assert refs is not None
            refs[id(nfa_rep)] = self
            self._refs = refs
            self.condition = nfa_rep.condition
            self.links = list(_vnfa.clone_var(ln, refs=refs) for ln in nfa_rep.links)

    def _links_to_var(self, links):
        for ln in links:
            if isinstance(ln, nfa):
                yield _vnfa.clone_var(ln, refs=self._refs)
            elif isinstance(ln, _vnfa):
                ln.set_refs(self._refs)
                yield ln
            elif isinstance(ln, nfaRef):
                yield ln
            else:
                assert False

    def add_links(self, *links):
        self.links.extend(self._links_to_var(links))

    def extend(self, targ):
        if isinstance(targ, nfa):
            targ = _vnfa.clone_var(targ, refs=self._refs)
        assert isinstance(targ, _vnfa)
        touched = set()
        self._replace_final(targ, touched)

    def _replace_final(self, targ, touched):
        if id(self) in touched:
            return
        touched.add(id(self))
        for i in range(len(self.links)):
            ln = self.links[i]
            if isinstance(ln, nfaRef):
                continue
            elif ln.final:
                self.links[i] = targ
            else:
                assert isinstance(ln, _vnfa)
                ln._replace_final(targ, touched)

    def _links_to_invar(self, refs):
        for ln in self.links:
            if isinstance(ln, nfaRef):
                if id(ln.ref) in self._refs:
                    yield nfaRef(self._refs[id(ln.ref)].as_invar(refs=refs))
                else:
                    yield ln
            elif isinstance(ln, nfa) and ln.final:
                yield ln
            else:
                assert isinstance(ln, _vnfa)
                yield ln.as_invar(refs=refs)

    def as_invar(self, *, refs=None):
        if refs is None:
            refs = {}
        assert isinstance(refs, dict)

        if id(self) in refs:
            return refs[id(self)]
        nfa_val = nfa(self.condition)
        refs[id(self)] = nfa_val
        nfa_val._links = tuple(self._links_to_invar(refs))
        return nfa_val
