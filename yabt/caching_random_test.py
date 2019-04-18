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
import os
import random
import string
import tempfile
from os.path import join, dirname, abspath

from yabt import config
from yabt.buildcontext import BuildContext
from yabt.buildfile_parser import process_build_file
from yabt.test_utils import generate_random_dag

PYTHON_TMPL = join(dirname(abspath(__file__)), '..', 'tests', 'data',
                   'caching', 'python_target.py.tmpl')
PYTHON_TARGET = """Python('{}', sources='{}')"""


def generate_dag_with_targets(size):
    targets_names = [''.join([random.choice(
        string.ascii_letters + string.digits) for _ in range(32)])
        for _ in range(size)]
    target_graph = generate_random_dag(
        [':' + target for target in targets_names])
    yroot = []
    for target_name in targets_names:
        file_name = join(target_name + '.py')
        with open(PYTHON_TMPL, 'r') as tmpl:
            code = tmpl.read().format(target_name)
        with open(file_name, 'w') as target_file:
            target_file.write(code)
        yroot.append(PYTHON_TARGET.format(target_name, file_name))
    with open(config.BUILD_PROJ_FILE, 'w') as yroot_file:
        yroot_file.write('\n\n'.join(yroot))
    return targets_names, target_graph


def test_caching(basic_conf):
    dir = tempfile.mkdtemp()
    os.chdir(dir)
    basic_conf.project_root = dir
    targets_names, targets_graph = generate_dag_with_targets(10)
    basic_conf.targets = [':' + target for target in targets_names]
    build_context = BuildContext(basic_conf)
    process_build_file(basic_conf.get_project_build_file(), build_context,
                       basic_conf)
    build_context.target_graph = targets_graph
    build_context.build_graph()
