#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import unittest


class TestFlaky(unittest.TestCase):
  """Flaky test function."""

  def test_flaky(self):
    file_name = os.environ['RANDOM_FILE']
    if os.path.isfile(file_name):
      os.remove(file_name)
      return
    open(file_name, 'w+').close()
    self.assertTrue(False)


if '__main__' == __name__:
  unittest.main()
