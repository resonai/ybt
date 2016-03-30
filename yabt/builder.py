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
yabt base builder
~~~~~~~~~~~~~~~~~

:author: Itamar Ostricher
"""


from . import target


class BaseBuilder:

    def __init__(self, build_context):
        self._context = build_context

    # def extract_target(self, *args, **kwargs):
    #     raise NotImplementedError(self.__class__.__name__)

    def build(self, target_inst):  # pylint: disable=unused-argument
        raise NotImplementedError(self.__class__.__name__)

    def get_workspace(self, *parts):
        """Return a path to a private builder-specific workspace dir.
           Create sub-tree of dirs using strings from `parts` inside workspace,
           and return full path to innermost directory.

        Upon returning successfully, the directory will exist (potentially
        changed to a safe FS name), even if it didn't exist before, including
        any intermediate parent directories.
        """
        return self._context.get_workspace(self.__class__.__name__, *parts)

    def get_target_by_depname(self, dep):
        return (self._context.targets[target.norm_name(self._context, dep)]
                .target)

    def walk_target_graph(self, node_names):
        yield from self._context.walk_target_graph(node_names)
