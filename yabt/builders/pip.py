# -*- coding: utf-8 -*-

# Copyright 2016 Yowza Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
yabt PyPI Builder
~~~~~~~~~~~~~~~~~

:author: Itamar Ostricher
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
