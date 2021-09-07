#!/usr/bin/env python3
import unittest
import rre
import nfa

class TestRREAST(unittest.TestCase):
    def test_simple_match(self):
        parser = rre.parse(b'test').to_nfa()
        match = parser.parse(b'test')
        self.assertEqual(match.text, b'test')
        self.assertEqual(match.ch, 0)
        self.assertEqual(match.line, 0)

    def test_simple_nomatch(self):
        parser = rre.parse(b'test').to_nfa()
        with self.assertRaises(nfa.ParsingError) as err_ctx:
            parser.parse(b'nottest')
        err = err_ctx.exception
        self.assertEqual(err.ch, 0)
        self.assertEqual(err.line, 0)

    def test_simple_partialmatch(self):
        parser = rre.parse(b'test').to_nfa()
        with self.assertRaises(nfa.ParsingError) as err_ctx:
            parser.parse(b'testnot')
        err = err_ctx.exception
        self.assertEqual(err.ch, 4)
        self.assertEqual(err.line, 0)
        self.assertEqual(err.partial.text, b'test')
        self.assertEqual(err.partial.ch, 0)
        self.assertEqual(err.partial.line, 0)

    def test_simple_partialtext(self):
        parser = rre.parse(b'testplus').to_nfa()
        with self.assertRaises(nfa.ParsingError) as err_ctx:
            parser.parse(b'test')
        err = err_ctx.exception
        self.assertEqual(err.ch, 4)
        self.assertEqual(err.line, 0)
        self.assertEqual(err.partial.text, b'test')
        self.assertEqual(err.partial.ch, 0)
        self.assertEqual(err.partial.line, 0)

    def test_nfa_char_class(self):
        parser = rre.parse(b'[ab]').to_nfa()
        match_a = parser.parse(b'a')
        match_b = parser.parse(b'b')
        with self.assertRaises(nfa.ParsingError):
            match_c = parser.parse(b'c')
        self.assertEqual(match_a.text, b'a')
        self.assertEqual(match_b.text, b'b')

    def test_nfa_sequence(self):
        parser = rre.parse(b'[Tt]est').to_nfa()
        match_a = parser.parse(b'test')
        match_b = parser.parse(b'Test')
        with self.assertRaises(nfa.ParsingError):
            match_c = parser.parse(b'_est')
        self.assertEqual(match_a.text, b'test')
        self.assertEqual(match_b.text, b'Test')

    def test_nfa_either(self):
        parser = rre.parse(b'abc|def').to_nfa()
        match_a = parser.parse(b'abc')
        match_b = parser.parse(b'def')
        with self.assertRaises(nfa.ParsingError) as err_ctx:
            parser.parse(b'ab')
        self.assertEqual(match_a.text, b'abc')
        self.assertEqual(match_b.text, b'def')
        err = err_ctx.exception
        self.assertEqual(err.ch, 2)
        self.assertEqual(err.line, 0)
        self.assertEqual(err.partial.text, b'ab')
