#!/usr/bin/env python3
import unittest
import nfa

class TestNFA(unittest.TestCase):
    def testNFAInit(self):
        n = nfa.nfa()
        self.assertIsNone(n.condition)
        self.assertFalse(n.final)
        self.assertTrue(nfa.nfa.final.final)
        self.assertEqual(len(n.links), 0)

    def testNFANoContition(self):
        n = nfa.nfa()
        self.assertEqual(n.test_condition('123'), ('', '123'))

    def testBasicNFACondition(self):
        n = nfa.nfa(condition=lambda s : ('a', s[1:]) if s.startswith('a') else(None, s))
        self.assertEqual(n.test_condition(''), (None, ''))
        self.assertEqual(n.test_condition('a'), ('a', ''))
        self.assertEqual(n.test_condition('b'), (None, 'b'))

    def testBadCondition(self):
        n = nfa.nfa(condition=lambda s : ('a', s))
        if __debug__:
            with self.assertRaises(AssertionError):
                n.test_condition('')

    def testFinalError(self):
        if __debug__:
            with self.assertRaises(AssertionError):
                nfa.nfa.final.test_condition('')
            with self.assertRaises(AssertionError):
                nfa.nfa.final.test_condition('a')

    def testBytesNFANoContition(self):
        n = nfa.nfa()
        self.assertEqual(n.test_condition(b'123'), (b'', b'123'))

    def testBytesBasicNFACondition(self):
        n = nfa.nfa(condition=lambda s : (b'a', s[1:]) if s.startswith(b'a') else(None, s))
        self.assertEqual(n.test_condition(b''), (None, b''))
        self.assertEqual(n.test_condition(b'a'), (b'a', b''))
        self.assertEqual(n.test_condition(b'b'), (None, b'b'))

    def testBytesBadCondition(self):
        n = nfa.nfa(condition=lambda s : (b'a', s))
        if __debug__:
            with self.assertRaises(AssertionError):
                n.test_condition(b'')

    def testBytesFinalError(self):
        if __debug__:
            with self.assertRaises(AssertionError):
                nfa.nfa.final.test_condition(b'')
            with self.assertRaises(AssertionError):
                nfa.nfa.final.test_condition(b'a')

    def testMakeLinked(self):
        n = nfa.nfa()
        n2 = n.add_links(nfa.nfa())
        n3 = n.add_links(nfa.nfa(), nfa.nfa())
        self.assertEqual(len(n.links), 0)
        self.assertEqual(len(n2.links), 1)
        self.assertTrue(isinstance(n2.links[0], nfa.nfa))
        self.assertEqual(len(n3.links), 2)
        self.assertTrue(isinstance(n3.links[0], nfa.nfa))
        self.assertTrue(isinstance(n3.links[1], nfa.nfa))

    def testCircularLink(self):
        n = nfa.nfa()
        n2 = n.add_links(n)
        self.assertEqual(len(n.links), 0)
        self.assertEqual(len(n2.links), 1)
        self.assertEqual(id(n2), id(n2.links[0]))

    def testDeepCircularLinks(self):
        n = nfa.nfa()
        n = n.add_links(nfa.nfa())
        ln_orig = n.links[0]
        m = n.as_var()
        m.links[0].add_links(n)
        n2 = m.as_invar()
        self.assertEqual(len(n.links), 1)
        self.assertEqual(len(n.links[0].links), 0)
        self.assertEqual(id(n.links[0]), id(ln_orig))
        self.assertEqual(len(n2.links[0].links), 1)
        self.assertEqual(id(n2), id(n2.links[0].links[0]))
        self.assertNotEqual(id(n2), id(n2.links[0]))

    def testRefLink(self):
        n = nfa.nfa()
        nr = nfa.nfa()
        n2 = n.add_links(nfa.nfaRef(nr))
        self.assertNotEqual(id(n), id(n2))
        self.assertEqual(id(n2.links[0].ref), id(nr))
        nr2 = nr.add_links(n)
        self.assertNotEqual(id(n2.links[0].ref), id(nr2))

    def testRefClone(self):
        n = nfa.nfa()
        n2 = nfa.nfa()
        n = n.add_links(n2)
        ext_n = nfa.nfa()
        n3 = n.add_links(nfa.nfaRef(n), nfa.nfaRef(n2), nfa.nfaRef(ext_n))
        self.assertNotEqual(id(n3), id(n))
        self.assertEqual(id(n3), id(n3.links[1].ref))
        self.assertEqual(id(n2), id(n3.links[2].ref))
        self.assertNotEqual(id(n3.links[0]), id(n3.links[2].ref))
        self.assertEqual(id(ext_n), id(n3.links[3].ref))

    def testDup(self):
        n = nfa.nfa()
        n = n.add_links(n.clone())
        self.assertEqual(len(n.links), 1)
        self.assertNotEqual(id(n), id(n.links[0]))
        self.assertEqual(len(n.links[0].links), 0)

    def testEnd(self):
        n = nfa.nfa()
        n = n.add_links(nfa.nfa.final)
        self.assertTrue(n.links[0].final)

    def testCloneEnd(self):
        n = nfa.nfa()
        n = n.add_links(nfa.nfa.final)
        n2 = n.clone()
        self.assertNotEqual(id(n), id(n2))
        self.assertTrue(n.links[0].final)
        self.assertTrue(n2.links[0].final)

    def testExtend(self):
        n = nfa.nfa()
        n = n.add_links(nfa.nfa.final)
        n2 = n.extend(nfa.nfa())
        self.assertNotEqual(id(n), id(n2))
        self.assertEqual(len(n.links), 1)
        self.assertTrue(n.links[0].final)
        self.assertEqual(len(n2.links), 1)
        self.assertFalse(n2.links[0].final)
        self.assertEqual(len(n2.links[0].links), 0)

if __name__ == '__main__':
    unittest.main()
