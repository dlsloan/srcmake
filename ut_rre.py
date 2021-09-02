#!/usr/bin/env python3
import unittest
import rre

# next steps in order, escape/short-hand sequences,
#   named rules, terminal-match, terminal-match error messages,
#   structured output, structure tags vs nodes

class TestRRE(unittest.TestCase):
    def test_const(self):
        self.assertEqual(rre.parse(b'test'), rre.const(b'test'))

    def test_class(self):
        self.assertEqual(rre.parse(b'[tT]'), rre.char_class([b't', b'T']))

    def test_class_close_bracket(self):
        self.assertEqual(rre.parse(b'[]tT]'), rre.char_class([ b']', b't', b'T']))

    def test_class_dash_begin(self):
        self.assertEqual(rre.parse(b'[-tT]'), rre.char_class([ b'-', b't', b'T']))

    def test_class_dash_end(self):
        self.assertEqual(rre.parse(b'[tT-]'), rre.char_class([ b'-', b't', b'T']))

    def test_class_range(self):
        self.assertEqual(rre.parse(b'[a-c]'), rre.char_class([ b'a', b'b', b'c']))

    def test_invert(self):
        expr = rre.parse(b'[^tT]')
        for i in range(256):
            if i == ord('t') or i == ord('T'):
                self.assertFalse(bytes([i]) in expr.set)
            else:
                self.assertTrue(bytes([i]) in expr.set)
        self.assertEqual(expr, rre.char_class([b't', b'T'], invert=True))

    def test_seq(self):
        self.assertEqual(rre.parse(b'[tT]est'),
            rre.seq(rre.char_class([b't', b'T']), rre.const(b'est')))

    def test_seq2(self):
        self.assertEqual(rre.parse(b'[tT]es[tT]'),
            rre.seq(
                rre.char_class([b't', b'T']),
                rre.const(b'es'),
                rre.char_class([b't', b'T'])))

    def test_either(self):
        self.assertEqual(rre.parse(b'a|bc'), rre.either(rre.const(b'a'), rre.const(b'bc')))

    def test_multi_either(self):
        self.assertEqual(rre.parse(b'a|bc|d'), rre.either(rre.const(b'a'), rre.const(b'bc'), rre.const(b'd')))

    def test_group(self):
        self.assertEqual(rre.parse(b'(bc)'), rre.group(rre.const(b'bc')))

    def test_count_any(self):
        self.assertEqual(rre.parse(b'a*'), rre.rep(rre.const(b'a'), 0, None))
        self.assertNotEqual(rre.parse(b'a*'), rre.rep(rre.const(b'a'), 0, 0))

    def test_count_seq(self):
        self.assertEqual(rre.parse(b'[tT]a*'), rre.seq(rre.char_class([b't', b'T']), rre.rep(rre.const(b'a'), 0, None)))

    def test_count_either(self):
        self.assertEqual(rre.parse(b'a|b*'), rre.either(rre.const(b'a'), rre.rep(rre.const(b'b'), 0, None)))

    def test_count_group(self):
        self.assertEqual(rre.parse(b'(ab)*'), rre.rep(rre.group(rre.const(b'ab')), 0, None))

    def test_count_plus(self):
        self.assertEqual(rre.parse(b'a+'), rre.rep(rre.const(b'a'), 1, None))

    def test_count_opt(self):
        self.assertEqual(rre.parse(b'a?'), rre.rep(rre.const(b'a'), 0, 1))

    def test_count_fixed(self):
        self.assertEqual(rre.parse(b'a{2}'), rre.rep(rre.const(b'a'), 2, 2))

    def test_count_range(self):
        self.assertEqual(rre.parse(b'a{2,4}'), rre.rep(rre.const(b'a'), 2, 4))

    def test_count_min(self):
        self.assertEqual(rre.parse(b'a{3,}'), rre.rep(rre.const(b'a'), 3, None))

    def test_wild(self):
        self.assertEqual(rre.parse(b'.'), rre.char_class([], invert=True))

    def test_sh_word(self):
        chars = []
        for i in range(26):
            chars.append(bytes([b'a'[0] + i]))
            chars.append(bytes([b'A'[0] + i]))
        for i in range(10):
            chars.append(bytes([b'0'[0] + i]))
        chars.append(b'_')
        self.assertEqual(rre.parse(b'\\w'), rre.char_class(chars))
        self.assertEqual(rre.parse(b'\\W'), rre.char_class(chars, invert=True))

    def test_sh_digit(self):
        chars = []
        for i in range(10):
            chars.append(bytes([b'0'[0] + i]))
        self.assertEqual(rre.parse(b'\\d'), rre.char_class(chars))
        self.assertEqual(rre.parse(b'\\D'), rre.char_class(chars, invert=True))

    def test_sh_whitespace(self):
        chars = [b' ', b'\t', b'\r', b'\n']
        self.assertEqual(rre.parse(b'\\s'), rre.char_class(chars))
        self.assertEqual(rre.parse(b'\\S'), rre.char_class(chars, invert=True))

    def test_sh_in_class(self):
        chars = [b' ', b'\t', b'\r', b'\n']
        self.assertEqual(rre.parse(b'[_\\s]'), rre.char_class([b'_'] + chars))

if __name__ == '__main__':
    unittest.main()