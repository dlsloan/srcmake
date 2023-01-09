#!/usr/bin/env python3
import unittest
import rre
import nfa

class TestNFA_Raw(unittest.TestCase):
    def test_init(self):
        test_nfa = nfa.nfa()
        self.assertTrue(test_nfa.is_terminal())
        test_nfa.parse(b'')
        with self.assertRaises(Exception):
            test_nfa.parse(b' ')

    def test_basic(self):
        test_nfa = nfa.nfa(condition=lambda ch: ch == b'a')
        self.assertFalse(test_nfa.is_terminal())
        test_nfa.parse(b'a')
        with self.assertRaises(Exception):
            test_nfa.parse(b'b')

    def test_basic_opt(self):
        test_ch = nfa.nfa(condition=lambda ch: ch == b'a')
        test_nfa = nfa.nfa(next=[test_ch, nfa.nfa()])
        test_nfa.parse(b'')
        test_nfa.parse(b'a')
        with self.assertRaises(Exception):
            test_nfa.parse(b'b')


if __name__ == '__main__':
    unittest.main()