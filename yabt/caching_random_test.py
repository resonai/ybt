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
import shutil
import string
from os.path import join, dirname, abspath, getmtime
import pytest

from conftest import reset_parser
from yabt import config, cli, extend
from yabt.buildcontext import BuildContext
from yabt.graph import populate_targets_graph
from yabt.logging import make_logger
from yabt.test_utils import generate_random_dag

CPP_TMPL = join(dirname(abspath(__file__)), '..', 'tests', 'data',
                'caching', 'cpp_prog.cc.tmpl')
CPP_TARGET = """CppProg('{}', sources='{}', in_buildenv=':builder', deps={})"""
YROOT_TMPL = join(dirname(abspath(__file__)), '..', 'tests', 'data',
                'caching', 'YRoot.tmpl')
YSETTINGS = join(dirname(abspath(__file__)), '..', 'tests', 'data',
                 'caching', 'YSettings')

slow = pytest.mark.skipif(not pytest.config.getoption('--with-slow'),
                          reason='need --with-slow option to run')

logger = make_logger(__name__)

def generate_dag_with_targets(size):
    targets_names = [''.join([random.choice(
        string.ascii_letters + string.digits) for _ in range(32)])
        for _ in range(size)]
    target_graph = generate_random_dag(targets_names)
    yroot = []
    for target_name in targets_names:
        file_name = join(target_name + '.cc')
        deps = [':' + dep for dep, target in target_graph.edges
                if target == target_name]
        with open(CPP_TMPL, 'r') as tmpl:
            code = tmpl.read().format(target_name)
        with open(file_name, 'w') as target_file:
            target_file.write(code)
        yroot.append(CPP_TARGET.format(target_name, file_name, deps))
    with open(YROOT_TMPL, 'r') as yroot_tmpl_file:
        yroot_data = yroot_tmpl_file.read()
    with open(config.BUILD_PROJ_FILE, 'w') as yroot_file:
        yroot_file.write(yroot_data + '\n\n'.join(yroot))
    shutil.copyfile(YSETTINGS, 'YSettings')
    return targets_names, target_graph


@slow
def test_caching(tmp_dir):
    targets_names, targets_graph = generate_dag_with_targets(10)
    reset_parser()
    basic_conf = cli.init_and_get_conf(['--non-interactive', 'build'])
    extend.Plugin.load_plugins(basic_conf)
    basic_conf.targets = [':' + target for target in targets_names]
    build_context = BuildContext(basic_conf)
    populate_targets_graph(build_context, basic_conf)

    build_context.build_graph()
    logger.info('done first build')
    targets_modified = {}
    for target in targets_names:
        targets_modified[target] = get_last_modified(basic_conf, target)

    logger.info('starting second build')
    build_context = BuildContext(basic_conf)
    populate_targets_graph(build_context, basic_conf)
    build_context.build_graph()
    for target in targets_names:
        assert targets_modified[target] == \
               get_last_modified(basic_conf, target)


def get_last_modified(basic_conf, target):
    return getmtime(join(basic_conf.builders_workspace_dir, 'release_flavor',
                         'CppProg', '_' + target, target + '.o'))
