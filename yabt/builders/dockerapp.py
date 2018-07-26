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
yabt DockerApp Builder
~~~~~~~~~~~~~~~~~~~~~~

:author: Itamar Ostricher
"""


from os.path import join

from ostrich.utils.collections import listify

from .docker import docker_builder
from ..docker import build_docker_image, get_image_name
from ..extend import PropType as PT, register_builder_sig
from .. import target_utils


def register_app_builder_sig(builder_name, sig=None, docstring=None):
    register_builder_sig(
        builder_name,
        [('base_image', PT.Target)] + listify(sig) + [
            ('image_name', PT.str, None),
            ('image_tag', PT.str, 'latest'),
            ('full_path_cmd', PT.bool, False),
            ('work_dir', PT.str, '/usr/src/app'),
            ('env', PT.dict, None),
            ('distro', PT.dict, None),
            ('image_caching_behavior', PT.dict, None),
            ('build_user', PT.str, None),
            ('run_user', PT.str, None),
            ('docker_labels', PT.dict, None),
        ], cachable=False, docstring=docstring)


def build_app_docker_and_bin(build_context, target, **kwargs):
    build_module, bin_name = target_utils.split(target.name)
    docker_builder(build_context, target, kwargs.get('entrypoint'),
                   join(build_context.get_bin_dir(build_module), bin_name))
