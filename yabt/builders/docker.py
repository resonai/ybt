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
yabt Docker Builder
~~~~~~~~~~~~~~~~~~~

:author: Itamar Ostricher
"""


import os
from os.path import (
    basename, isdir, isfile, join, normpath, relpath, samefile, split)
import shutil

from ostrich.utils.path import commonpath
from ostrich.utils.proc import run
from ostrich.utils.text import get_safe_path
from ostrich.utils.collections import listify

from ..config import Config
from ..extend import (
    PropType as PT, register_build_func, register_builder_sig,
    register_manipulate_target_hook)
from ..logging import make_logger
from ..docker import build_docker_image
from .. import target_utils


logger = make_logger(__name__)


register_builder_sig(
    'ExtDockerImage', [('image', PT.str), ('tag', PT.str, None)])


def format_qualified_image_name(target):
    if target.props.tag:
        return '{}:{}'.format(target.props.image, target.props.tag)
    return target.props.image


@register_build_func('ExtDockerImage')
def ext_docker_image_builder(build_context, target):
    print('Fetch and cache Docker image from registry', target)


register_builder_sig(
    'DockerImage',
    [('start_from', PT.Target),
     ('deps', PT.TargetList, None),
     ('docker_cmd', PT.StrList, None),
     ('image_name', PT.str, None),
     ('image_tag', PT.str, 'latest'),
     ('work_dir', PT.str, '/usr/src/app'),
     ('env', None),
     ('truncate_common_parent', PT.str, None)
     ])


@register_manipulate_target_hook('DockerImage')
def docker_image_manipulate_target(build_context, target):
    logger.debug('Injecting "{}" to deps of {}',
                 target.props.start_from, target)
    target.deps.append(target.props.start_from)


@register_build_func('DockerImage')
def docker_image_builder(build_context, target):
    build_docker_image(
        build_context,
        name=(target.props.image_name if target.props.image_name
              else target_utils.split_name(target.name)),
        tag=target.props.image_tag,
        base_image=format_qualified_image_name(
            build_context.targets[target.props.start_from]),
        deps=build_context.walk_target_deps_topological_order(target),
        env=target.props.env,
        work_dir=target.props.work_dir,
        truncate_common_parent=target.props.truncate_common_parent,
        cmd=target.props.docker_cmd)
