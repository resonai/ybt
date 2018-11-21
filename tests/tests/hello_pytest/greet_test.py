#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest

from .greet import greet


class TestGreet(unittest.TestCase):
  """Test greet function."""

  def test_greet(self):
    self.assertEqual('Hello World!', greet('World'))


class TestGreetFail(unittest.TestCase):
  """Test greet function (and fail)."""

  def test_greet_fail(self):
    self.assertEqual('Hello world', greet('World'))


if '__main__' == __name__:
  unittest.main()
