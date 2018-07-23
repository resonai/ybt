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
yabt File group builder
~~~~~~~~~~~~~~~~~~~~~~~

:author: Itamar Ostricher
"""


from ..artifact import ArtifactType as AT
from ..extend import (
    PropType as PT, register_build_func, register_builder_sig,
    register_manipulate_target_hook)
from ..utils import yprint


register_builder_sig(
    'FileGroup',
    [('files', PT.FileList, None),
     ('kind', PT.str, 'app'),
     ])


@register_build_func('FileGroup')
def file_group_builder(build_context, target):
    yprint(build_context.conf, 'Build FileGroup', target)
    kind = getattr(AT, target.props.kind)
    target.artifacts.extend(kind, target.props.files)
