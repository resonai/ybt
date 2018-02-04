# -*- coding: utf-8 -*-

# Copyright 2016 Resonai Ltd. All rights reserved
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

# pylint: disable=invalid-name, unused-argument

"""
yabt Alias Builder
~~~~~~~~~~~~~~~~~~

:author: Itamar Ostricher
"""


from ..extend import (
    PropType as PT, register_builder_sig, register_manipulate_target_hook)


register_builder_sig('Alias')


@register_manipulate_target_hook('Alias')
def manipulate_alias_target(build_context, target):
    target.tags.add('prune-me')
