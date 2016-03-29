# -*- coding: utf-8 -*-

"""
yabt PyPI Builder
~~~~~~~~~~~~~~~~~

:copyright: (c) 2016 Yowza by Itamar Ostricher
:license: MIT, see LICENSE for more details.
"""


from ..builder import BaseBuilder
from ..target import BaseTarget


class PyPIPackageTarget(BaseTarget):

    def __init__(self, build_context, name, package, version=None, deps=None):
        super().__init__(build_context, name, deps=deps)
        self.package = package
        self.version = version

    def get_pip_requirements(self):
        if self.version:
            yield '{0.package}=={0.version}'.format(self)
        else:
            yield str(self.package)


class PipBuilder(BaseBuilder):

    @staticmethod
    def get_builder_aliases():
        return frozenset(('PipPackage', 'PyPI'))

    def extract_target(self, name, package, version=None, requires=None):
        target_inst = PyPIPackageTarget(self._context, name, package, version,
                                        deps=requires)
        self._context.register_target(target_inst, self)

    def build(self, target_inst):
        print('Fetch and cache PyPI package',
              target_inst.package, target_inst.version)
