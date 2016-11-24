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

:author: Zohar Rimon
"""


import os
from os.path import isdir, isfile, join
import shutil

import pytest

from . import proto
from ..buildcontext import BuildContext
from ..graph import populate_targets_graph, topological_sort
from ..utils import yprint


slow = pytest.mark.skipif(not pytest.config.getoption('--with-slow'),
                          reason='need --with-slow option to run')


def clear_output():
    try:
        shutil.rmtree('build')
    except FileNotFoundError:
        pass


@slow
@pytest.mark.usefixtures('in_prototest_project')
def test_proto_builder(basic_conf):
    clear_output()
    build_context = BuildContext(basic_conf)
    basic_conf.targets = ['app:hello-proto']
    populate_targets_graph(build_context, basic_conf)
    for target_name in topological_sort(build_context.target_graph):
        target = build_context.targets[target_name]
        if target.buildenv:
            buildenv = build_context.targets[target.buildenv]
            for dep in build_context.walk_target_deps_topological_order(
                    buildenv):
                build_context.build_target(dep)
            build_context.build_target(buildenv)
        build_context.build_target(target)
    assert isdir('build')
    assert isdir(join('build', 'gen'))
    assert isdir(join('build', 'gen', 'proto'))
    assert isfile(join('build', 'gen', 'proto', '__init__.py'))
    assert isdir(join('build', 'gen', 'proto', 'app'))
    assert isfile(join('build', 'gen', 'proto', 'app', '__init__.py'))
    for exp_gen_fname in [
        'hello.pb.cc',
        'hello.pb.h',
        'hello_pb2.py'
    ]:
        assert isfile(join('build', 'gen', 'proto', 'app', exp_gen_fname))
    clear_output()
