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


logger = make_logger(__name__)


register_builder_sig(
    'ExtCommand',
    [('cmd'),
     ('in_buildenv', PT.Target, None),
     ('cmd_env', None),
     ('deps', PT.TargetList, None),
     ])


@register_build_func('ExtCommand')
def ext_command_builder(build_context, target):
    print('Build (run) ExtCommand', target)
    build_context.run_in_buildenv(target.props.in_buildenv, target.props.cmd,
                                  target.props.cmd_env)
    # TODO(itamar): way to describe the artifacts of the external command,
    # so it can be used by dependent targets, and cached in some smart way


@register_manipulate_target_hook('ExtCommand')
def ext_command_manipulate_target(build_context, target):
    logger.debug('Injecting "{}" to deps of {}',
                 target.props.in_buildenv, target)
    target.deps.append(target.props.in_buildenv)
