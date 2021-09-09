#!/usr/bin/env python3
from typing import Match
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

    def test_nfa_count_unbounded(self):
        parser = rre.parse(b'a+').to_nfa()
        match = parser.parse(b'a')
        self.assertEqual(match.text, b'a')
        match = parser.parse(b'aaa')
        self.assertEqual(match.text, b'aaa')
        with self.assertRaises(nfa.ParsingError) as err_ctx:
            parser.parse(b'aab')
        err = err_ctx.exception
        self.assertEqual(err.ch, 2)
        self.assertEqual(err.partial.text, b'aa')
        with self.assertRaises(nfa.ParsingError) as err_ctx:
            parser.parse(b'')

    def test_nfa_count_bounded(self):
        parser = rre.parse(b'a{1,3}').to_nfa()
        with self.assertRaises(nfa.ParsingError):
            parser.parse(b'')
        self.assertEqual(parser.parse(b'a').text, b'a')
        self.assertEqual(parser.parse(b'aa').text, b'aa')
        self.assertEqual(parser.parse(b'aaa').text, b'aaa')
        with self.assertRaises(nfa.ParsingError):
            parser.parse(b'aaaa')

    def test_nfa_count_none(self):
        parser = rre.parse(b'a?').to_nfa()
        self.assertEqual(parser.parse(b'').text, b'')
        self.assertEqual(parser.parse(b'a').text, b'a')
        with self.assertRaises(nfa.ParsingError):
            parser.parse(b'aa')

    def test_nfa_group(self):
        parser = rre.parse(b'(a?)').to_nfa()
        self.assertEqual(parser.parse(b'').text, b'')
        self.assertEqual(parser.parse(b'a').text, b'a')
        with self.assertRaises(nfa.ParsingError):
            parser.parse(b'aa')

    def test_nfa_named(self):
        env = rre.env.parse(b'name:[a-z]+')
        parser = rre.parse(b'{:name}').to_nfa()
        match = parser.parse(b'abc', env=env)
        self.assertEqual(match.text, b'abc')
        self.assertEqual(len(match.named), 1)
        self.assertEqual(match.named[0].text, b'abc')
        self.assertEqual(match.named[0].ch, 0)
        self.assertEqual(match.named[0].line, 0)
        self.assertEqual(match.named[0].name, b'name')

    def test_nfa_multi_named(self):
        env = rre.env.parse(b'name:[a-z]+\nid:[0-9]{1,2}')
        parser = rre.parse(b'{:name}{:id}').to_nfa()
        match = parser.parse(b'abc01', env=env)
        self.assertEqual(match.text, b'abc01')
        self.assertEqual(len(match.named), 2)
        self.assertEqual(match.named[0].text, b'abc')
        self.assertEqual(match.named[0].ch, 0)
        self.assertEqual(match.named[0].line, 0)
        self.assertEqual(match.named[0].name, b'name')
        self.assertEqual(match.named[1].text, b'01')
        self.assertEqual(match.named[1].ch, 3)
        self.assertEqual(match.named[1].line, 0)
        self.assertEqual(match.named[1].name, b'id')
        with self.assertRaises(nfa.ParsingError):
            parser.parse(b'abc')


if __name__ == '__main__':
    unittest.main()
