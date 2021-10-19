import threading

from singletonrefs import SingletonRefs
from collections import namedtuple

nfaRef = namedtuple('nfaRef', ['ref'])
nfaRef.resolve = lambda nr: nfaRef(nr.ref.resolve())


class MetaNFA(type):
    @property
    def final(cls):
        return cls._final


class nfa(object, metaclass=MetaNFA):
    def __init__(self, condition=None, *, _volatile=False):
        self._condition = condition
        self._links = tuple()

    @property
    def condition(self):
        with nfaModEnv(False) as env:
            return env.ref_resolve(self)._condition
    @condition.setter
    def condition(self, value):
        with nfaModEnv(False) as env:
            assert env.is_volatile
            env.ref_resolve(self)._condition = value

    @property
    def links(self):
        with nfaModEnv(False) as env:
            return env.ref_resolve(self)._links
    @links.setter
    def links(self, value):
        with nfaModEnv(False) as env:
            assert env.is_volatile
            env.ref_resolve(self)._links = value

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
        # Debug checks
        if __debug__ and retval[0] is None:
            assert retval[1] == s
        elif __debug__:
            assert retval[0] + retval[1] == s
        return retval

    def add_links(self, *links):
        with self.modify() as env:
            self.links = self.links + tuple(links)
            return env.resolve()

    def clone(self):
        with self.modify() as env:
            env.change_all()
            return env.resolve()

    def modify(self):
        return nfaModEnv(True, self)

    def extend(self, targ):
        with self.modify() as env:
            env.replace_final(targ)
            return env.resolve()

    def __repr__(self):
        return f"nfa({id(self)})"

nfa._final = nfa()


class nfaVolatile:
    def __init__(self, base, env):
        self._base = base
        self._env = env
        self._i_links = tuple()
        self._i_rev_links = set()
        self._changed_val = None
        self._done = False
        self._made = False

    def make(self, env):
        if self._made:
            return
        self._made = True
        self._i_links = tuple(env.ref_resolve(ln) for ln in self._base._links)
        for ln in self._i_links:
            ln.add_rev_link(self)

    def add_rev_link(self, node):
        self._i_rev_links.add(id(node))


    def remove_rev_link(self, node):
        self._i_rev_links.remove(id(node))


    def _mark_changed(self, env):
        if self._changed_val is not None or self._base.final:
            return
        self._changed_val = nfa()
        for inode in self._i_rev_links:
            node = env.lookup(inode)
            node._mark_changed(env)

    @property
    def links(self):
        return self._links
    @links.setter
    def links(self, value):
        self._links = value
    @property
    def _links(self):
        return self._i_links
    @_links.setter
    def _links(self, value):
        assert not self._base.final
        with nfaModEnv(False) as env:
            new_links = tuple(env.make_volatile(ln) for ln in value)
            for ln in self._i_links:
                if isinstance(ln, nfaRef):
                    ln = ln.ref
                ln.remove_rev_link(self)
            for ln in new_links:
                if isinstance(ln, nfaRef):
                    ln = ln.ref
                ln.add_rev_link(self)
            self._i_links = new_links
            self._mark_changed(env)

    def resolve(self):
        if self._base.final and self._env.final_replace is not None:
            return self._env.final_replace
        if self._changed_val is None:
            return self._base
        if self._done:
            return self._changed_val
        self._done = True
        self._changed_val._condition = self._base._condition
        self._changed_val._links = tuple(ln.resolve() for ln in self._i_links)
        return self._changed_val

    def add_links(self, *links):
        self.links = self.links + tuple(links)


class nfaModEnv:
    locals = threading.local()

    def __init__(self, wr_en, root=None):
        assert not wr_en or root is not None
        self._wr_en = wr_en
        self._root = root
        self._is_outer = False
        self.final_replace = None
        if __debug__:
            self._has_entered = False
            self._has_exited = False

    @property
    def is_volatile(self):
        return self._wr_en

    def replace_final(self, targ):
        if id(nfa.final) in nfaModEnv.locals.idmap:
            for inode in nfaModEnv.locals.idmap[id(nfa.final)]._i_rev_links:
                node = self.lookup(inode)
                node._mark_changed(self)
        self.final_replace = targ

    def ref_resolve(self, node):
        if id(node) in nfaModEnv.locals.idmap:
            return nfaModEnv.locals.idmap[id(node)]
        else:
            return node

    def mark_and_prop_change(self, node, touched):
        raise NotImplementedError

    def _build_ln_ref(self, vnode, link):
        if link is nfaRef:
            link = link.ref
        self._build_refs(link)
        lnvnode = nfaModEnv.locals.idmap[id(link)]
        lnvnode.add_rev_link(vnode)

    def _build_refs(self, node):
        if id(node) in nfaModEnv.locals.idmap:
            return
        vnode = nfaVolatile(node, self)
        nfaModEnv.locals.idmap[id(node)] = vnode
        nfaModEnv.locals.idmap[id(vnode)] = vnode
        for ln in node._links:
            self._build_refs(ln)
            self._build_ln_ref(vnode, ln)

    def change_all(self):
        for idv in nfaModEnv.locals.idmap:
            nfaModEnv.locals.idmap[idv]._mark_changed(self)

    def make_volatile(self, node):
        is_ref = isinstance(node, nfaRef)
        if is_ref:
            node = node.ref
        self._build_refs(node)
        vnode = nfaModEnv.locals.idmap[id(node)]
        # super slow probably... should only check new ones
        for idv in nfaModEnv.locals.idmap:
            nfaModEnv.locals.idmap[idv].make(self)
        if is_ref:
            return nfaRef(vnode)
        else:
            return vnode

    def lookup(self, idv):
        return nfaModEnv.locals.idmap[idv]

    def resolve(self):
        if nfaModEnv.locals.idmap is None:
            return self._root
        else:
            return nfaModEnv.locals.idmap[id(self._root)].resolve()

    def __enter__(self):
        if not hasattr(nfaModEnv.locals, 'idmap'):
            nfaModEnv.locals.idmap = None
        if __debug__:
            assert not self._has_entered
            self._has_entered = True
        if nfaModEnv.locals.idmap is None:
            nfaModEnv.locals.idmap = {}
            nfaModEnv.locals.volatile = self._wr_en
            self._is_outer = True
            if self._wr_en:
                self._build_refs(self._root)
                for idv in nfaModEnv.locals.idmap:
                    nfaModEnv.locals.idmap[idv].make(self)
        else:
            if __debug__ and not nfaModEnv.locals.volatile:
                assert not self._wr_en
            self._wr_en = nfaModEnv.locals.volatile
        return self

    def _complete(self):
        if self._root is not None:
            self._root = self.resolve()
        nfaModEnv.locals.idmap = None

    def __exit__(self, *pa):
        if __debug__:
            assert self._has_entered
            assert not self._has_exited
            self._has_exited = True
        if self._is_outer:
            self._complete()

    def __del__(self):
        assert self._has_entered == self._has_exited
