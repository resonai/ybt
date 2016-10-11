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
yabt DockerApp Builder
~~~~~~~~~~~~~~~~~~~~~~

:author: Itamar Ostricher
"""


from os.path import join

from ostrich.utils.collections import listify

from ..docker import build_docker_image, get_image_name
from ..extend import PropType as PT, register_builder_sig
from .. import target_utils


def register_app_builder_sig(builder_name, sig=None, docstring=None):
    register_builder_sig(
        builder_name,
        listify(sig) + [
            ('base_image', PT.Target),
            ('image_name', PT.str, None),
            ('image_tag', PT.str, 'latest'),
            ('work_dir', PT.str, '/usr/src/app'),
            ('env', PT.dict, None),
            ('distro', PT.dict, None),
            ('image_caching_behavior', PT.dict, None),
            ('truncate_common_parent', PT.str, None),
            ('build_user', PT.str, None),
            ('run_user', PT.str, None),
        ],
        docstring)


def build_app_docker_and_bin(build_context, target, **kwargs):
    build_module, bin_name = target_utils.split(target.name)
    ybt_bin_path = join(build_context.get_bin_dir(build_module), bin_name)
    image_id = build_docker_image(
        build_context,
        name=get_image_name(target),
        tag=target.props.image_tag,
        base_image=build_context.targets[target.props.base_image],
        deps=build_context.walk_target_deps_topological_order(target),
        env=target.props.env,
        work_dir=target.props.work_dir,
        truncate_common_parent=target.props.truncate_common_parent,
        entrypoint=kwargs.get('entrypoint'),
        distro=target.props.distro,
        image_caching_behavior=target.props.image_caching_behavior,
        runtime_params=target.props.runtime_params,
        ybt_bin_path=ybt_bin_path,
        build_user=target.props.build_user,
        run_user=target.props.run_user)
    target.props.docker_image_id = image_id
