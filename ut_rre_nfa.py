#!/usr/bin/env python3
import unittest
import rre

class TestRREAST(unittest.TestCase):
    def test_simple_match(self):
        match = rre.nfa(rre.parse(b'test')).parse(b'test')
        self.assertEqual(match.text, b'test')

    def test_simple_nomatch(self):
        match = rre.nfa(rre.parse(b'tets')).parse(b'test')
        self.assertIsNone(match)