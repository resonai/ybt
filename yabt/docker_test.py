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

"""
yabt Docker tests
~~~~~~~~~~~~~~~~~

:author: Itamar Ostricher
"""


import pytest

from subprocess import PIPE

from .buildcontext import BuildContext
from .docker import build_docker_image
from .graph import populate_targets_graph, topological_sort


@pytest.mark.usefixtures('in_simple_project')
def test_target_graph(basic_conf):
    build_context = BuildContext(basic_conf)
    populate_targets_graph(build_context, basic_conf)
    build_docker_image(
            build_context,
            name='ybt-buildenv',
            tag='latest',
            base_image='python:3.5',
            deps=[build_context.targets[target_name] for target_name in
                  topological_sort(build_context.target_graph)],
            no_artifacts=True)
    build_context.register_buildenv_image('ybt-buildenv',
                                          'ybt-buildenv:latest')
    result = build_context.run_in_buildenv(
        'ybt-buildenv', 'pip', 'freeze', stdout=PIPE, stderr=PIPE)
    assert 0 == result.returncode
    exp_pip_freeze = b'\n'.join([
        b'Flask==0.10.1',
        b'itsdangerous==0.24',
        b'Jinja2==2.8',
        b'MarkupSafe==0.23',
        b'Werkzeug==0.11.8',
    ]) + b'\n'
    assert exp_pip_freeze == result.stdout
