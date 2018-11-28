#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import unittest


class TestFlaky(unittest.TestCase):
  """
  Flaky test function.
  This test should fail once and pass once.
  This way we can make sure that the retry happened.
  The idea is that upon first run this fails and creates a local file.
  The file is a bit that represents that we failed last time so the
  consecutive run should pass.
  """

  def test_flaky(self):
    file_name = os.environ['RANDOM_FILE']
    if os.path.isfile(file_name):
      os.remove(file_name)
      return
    open(file_name, 'w+').close()
    self.assertTrue(False)


"""
The following peculiar test is designed to test that give 2 tests: A and B,
WLOG A runs before B and A fails.
We want to assets that A won't be run again until B has completed at least
attempt.
This would test that A was sent to the end of the queue.
To achieve that we use a persistent file, and we write to it when the first
test ran, fail him, write when the second ran, and then pass both of them.
Anything else is considered faulty behavior of YBT, including endless loop.
"""
def aba_test(self):
  file_name = os.environ['RANDOM_FILE']
  f = open(file_name, 'a+')
  f.seek(0)
  content = f.read()
  if content == '':
    f.write('A')
    f.close()
    self.assertTrue(False)
  elif content == 'A':
    f.write('B')
  elif content == 'AB':
    os.remove(file_name)
  else:
    self.assertTrue(False)
  f.close()

class TestA(unittest.TestCase):
  """Not necessarily the test that writes A (depands on the order)"""

  def test_a(self):
    aba_test(self)


class TestB(unittest.TestCase):
  """Not necessarily the test that writes A (depands on the order)"""

  def test_b(self):
    aba_test(self)

if '__main__' == __name__:
  unittest.main()
