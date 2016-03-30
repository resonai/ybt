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
yabt Alias Builder
~~~~~~~~~~~~~~~~~~

:author: Itamar Ostricher
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
