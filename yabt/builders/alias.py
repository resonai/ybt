# -*- coding: utf-8 -*-

"""
yabt Alias Builder
~~~~~~~~~~~~~~~~~~

:copyright: (c) 2016 Yowza by Itamar Ostricher
:license: MIT, see LICENSE for more details.
"""


from ..builder import BaseBuilder
from ..target import BaseTarget as Target


class AliasBuilder(BaseBuilder):

    @staticmethod
    def get_builder_aliases():
        return frozenset(('Alias',))

    def extract_target(self, name, requires=None):
        # force alias target names to conform to "phony target" name pattern
        # so they are pruned from targets graph after ti is populated.
        if not name.startswith('@'):
            name = '@{}'.format(name)
        target_inst = Target(self._context, name, deps=requires)
        self._context.register_target(target_inst, self)

    def build(self, target_inst):
        raise RuntimeError(target_inst)
