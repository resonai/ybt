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
yabt External command builder
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:author: Itamar Ostricher
"""


from ..extend import (
    PropType as PT, register_build_func, register_builder_sig,
    register_manipulate_target_hook)
from ..logging import make_logger
from ..utils import yprint


logger = make_logger(__name__)


register_builder_sig(
    'ExtCommand',
    [('cmd'),
     ('in_buildenv', PT.Target, None),
     ('cmd_env', None),
     ('work_dir', PT.str, None),
     ('auto_uid', PT.bool, True),
     ],
    # not cachable by default, since in general this builder doesn't know how
    # to keep track of its artifacts
    cachable=False)


@register_build_func('ExtCommand')
def ext_command_builder(build_context, target):
    yprint(build_context.conf, 'Build (run) ExtCommand', target)
    build_context.run_in_buildenv(
        target.props.in_buildenv, target.props.cmd, target.props.cmd_env,
        target.props.work_dir, target.props.auto_uid)
    # TODO(itamar): way to describe the artifacts of the external command,
    # so it can be used by dependent targets, and cached in some smart way


@register_manipulate_target_hook('ExtCommand')
def ext_command_manipulate_target(build_context, target):
    target.buildenv = target.props.in_buildenv
