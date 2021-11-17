# -*- coding: utf-8 -*-

# Copyright 2021 Resonai Ltd. All rights reserved
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
Gives information about the target
~~~~~~~~~~~~~~~~~

:author: Dana Shamir
"""

import json

from .config import Config
from .target_utils import parse_target_selectors


def get_target_info_json(conf: Config, build_context):
    targets = parse_target_selectors(conf.targets, conf)
    targets_info = {}
    for target_name in targets:
        target = build_context.targets[target_name]
        info = {
            'workspace': build_context.get_workspace(target.builder_name,
                                                     target_name)
        }
        if 'image_caching_behavior' in target.props:
            if 'remote_image_name' in target.props.image_caching_behavior:
                info['remote_image_name'] = \
                    target.props.image_caching_behavior['remote_image_name']
            if 'remote_image_tag' in target.props.image_caching_behavior:
                info['remote_image_tag'] = \
                    target.props.image_caching_behavior['remote_image_tag']
        targets_info[target_name] = info
    return json.dumps(targets_info)
