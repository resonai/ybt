# -*- coding: utf-8 -*-

"""
yabt Python Lib Builder
~~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2016 Yowza by Itamar Ostricher
:license: MIT, see LICENSE for more details.
"""


from os.path import join

from ..builder import BaseBuilder
from ..target import BaseTarget as Target


class PyLibTarget(Target):

    def __init__(self, build_context, name, sources=None, requires=None):
        super().__init__(build_context, name, sources, requires)
        # self.add_external_deps(external_deps)
        # print(self, self.sources, self.deps, self.external_deps)

    def get_sources(self):
        return (join(self.build_context.get_build_module(), source)
                for source in self.sources)

    def __repr__(self):
        return "'PyLib:{}'".format(self)


class PyLibBuilder(BaseBuilder):

    @staticmethod
    def get_builder_aliases():
        return frozenset(('PyLib', 'PythonLib', 'PythonLibrary'))

    def extract_target(self, name, sources=None, requires=None):
        self._context.register_target(
            PyLibTarget(self._context, name, sources, requires),
            self)

    def build(self, target_inst):
        print('Build PyLib', target_inst)
