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


if '__main__' == __name__:
  unittest.main()
