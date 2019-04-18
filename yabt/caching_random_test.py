# -*- coding: utf-8 -*-

# Copyright 2019 Resonai Ltd. All rights reserved
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
yabt caching random tests
~~~~~~~~~~~~~~~~~~

:author: Dana Shamir
"""

import random
import string
from os.path import join, dirname, abspath

from yabt.target_utils import Target
from yabt.test_utils import generate_random_dag

PYTHON_TMPL = join(dirname(abspath(__file__)), 'tests', 'data', 'caching',
                   'python_target.py.tmpl')


def generate_dag_with_targets(size, dir, build_context):
    targets_names = [''.join([random.choice(
        string.ascii_letters + string.digits) for _ in range(32)])
        for _ in range(size)]
    build_context.target_graph = generate_random_dag(targets_names)
    for target_name in build_context.target_graph.nodes():
        file_name = join(dir, target_name + '.py')
        with open(PYTHON_TMPL, 'r') as tmpl:
            code = tmpl.read().format(target_name)
        with open(file_name, 'w') as target_file:
            target_file.write(code)
        target = Target(builder_name='Python')
        target.props['sources'] = [file_name]
        build_context.targets[target_name] = target


