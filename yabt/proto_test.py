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


import pytest

from .builders import proto
from .buildcontext import BuildContext
from .graph import populate_targets_graph, topological_sort
from .utils import yprint
import os

DISTRO = {
    'id': 'Ubuntu',
    'release': '14.04',
    'codename': 'trusty',
    'description': 'Ubuntu 14.04.4 LTS',
}


@pytest.mark.usefixtures('in_prototest_project')
def test_proto(basic_conf):
    build_context = BuildContext(basic_conf)
    basic_conf.targets = ['app:hello']
    populate_targets_graph(build_context, basic_conf)
    for target_name in topological_sort(build_context.target_graph):
        target = build_context.targets[target_name]
        build_context.build_target(target)
    for file in [
        'hello.pb.cc',
        'hello.pb.h',
        'hello_pb2.py'
    ]:
        assert file in os.listdir('./out/app')
