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
yabt Target group builder
~~~~~~~~~~~~~~~~~~~~~~~~~

:author: Itamar Ostricher
"""


from ..extend import register_build_func, register_builder_sig
from ..utils import yprint


register_builder_sig('TargetGroup')


@register_build_func('TargetGroup')
def file_group_builder(build_context, target):
    yprint(build_context.conf, 'Build TargetGroup', target)
