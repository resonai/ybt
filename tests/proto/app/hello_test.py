#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest

from . import hello


class TestMessage(unittest.TestCase):

  def test_hello(self):
    self.assertEqual('Hello, World!', hello.get_message('hello.pb'))


if '__main__' == __name__:
  unittest.main()
