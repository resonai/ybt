# -*- coding: utf-8 -*-

"""
yabt Builders for tests
~~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2016 Yowza by Itamar Ostricher
:license: MIT, see LICENSE for more details.
"""


from ..builder import BaseBuilder
from ..target import BaseTarget as Target


class DepTesterBuilder(BaseBuilder):

    @staticmethod
    def get_builder_aliases():
        return frozenset(('DepTester',))

    def extract_target(self, name, requires=None):
        target_inst = Target(self._context, name, deps=requires)
        self._context.register_target(target_inst, self)

    def build(self, target_inst):
        print('Build DepTest', target_inst)
