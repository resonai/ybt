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
yabt Python Lib Builder
~~~~~~~~~~~~~~~~~~~~~~~

:author: Itamar Ostricher
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
