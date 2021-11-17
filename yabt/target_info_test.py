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
yabt target info tests
~~~~~~~~~~~~~~~~~~~~~~~

:author: Dana Shamir
"""
import json
import os
import pytest

from .buildcontext import BuildContext
from .graph import populate_targets_graph
from .target_info import get_target_info_json


@pytest.mark.usefixtures('in_caching_project')
def test_target_info(basic_conf):
    basic_conf.targets = [':builder-base', ':builder']
    build_context = BuildContext(basic_conf)
    populate_targets_graph(build_context, basic_conf)
    result = get_target_info_json(basic_conf, build_context)
    expected = {
        ':builder-base':
            {'workspace': os.path.join(
                os.getcwd(), 'yabtwork', 'flavor__all__', 'DockerImage',
                '_builder-base'),
             'remote_image_name': 'itamarost/builder-base-test',
             'remote_image_tag': 'v1'},
        ':builder':
            {'workspace': os.path.join(
                os.getcwd(), 'yabtwork', 'flavor__all__', 'DockerImage',
                '_builder')}
    }
    assert json.loads(result) == expected
