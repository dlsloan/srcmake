#!/usr/bin/env python3
import unittest
import ut_rre_src
import ut_nfa

def test(ut):
    suite = unittest.TestLoader().loadTestsFromModule(ut)
    result = unittest.TextTestRunner(failfast=True).run(suite)
    if len(result.errors) or len(result.failures) or len(result.unexpectedSuccesses):
        exit(1)

if __name__ == '__main__':
    test(ut_nfa)