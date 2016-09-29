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
yabt C++ Builder
~~~~~~~~~~~~~~~~

:author: Itamar Ostricher
"""


from .dockerapp import build_app_docker_and_bin, register_app_builder_sig
from ..extend import (
    PropType as PT, register_build_func, register_manipulate_target_hook)
from ..logging import make_logger
from ..utils import yprint


logger = make_logger(__name__)


register_app_builder_sig('CppApp', [('executable', PT.File)])


@register_manipulate_target_hook('CppApp')
def cpp_app_manipulate_target(build_context, target):
    logger.debug('Injecting "{}" to deps of {}',
                 target.props.base_image, target)
    target.deps.append(target.props.base_image)


@register_build_func('CppApp')
def cpp_bin_builder(build_context, target):
    """Pack a C++ binary as a Docker image with its runtime dependencies.

    TODO(itamar): Dynamically analyze the binary and copy shared objects
    from its buildenv image to the runtime image, unless they're installed.
    """
    yprint(build_context.conf, 'Build CppApp', target)
    if target.props.executable not in target.artifacts['app']:
        target.artifacts['app'].append(target.props.executable)
    build_app_docker_and_bin(
        build_context, target, entrypoint=[target.props.executable])
