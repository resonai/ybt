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

import networkx as nx
from os.path import join, dirname, abspath, getmtime
import pytest
import random
import shutil
import string

from conftest import reset_parser
from yabt import config, cli, extend
from yabt.buildcontext import BuildContext
from yabt.graph import populate_targets_graph
from yabt.logging import make_logger
from yabt.test_utils import generate_random_dag

NUM_TARGETS = 10
NUM_TESTS = 10

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


def random_string():
    return ''.join([random.choice(string.ascii_letters + string.digits)
                    for _ in range(random.randint(20, 40))])


def generate_dag_with_targets(size):
    targets_names = [random_string() for _ in range(size)]
    target_graph = generate_random_dag(targets_names)
    yroot = []
    for target_name in targets_names:
        generate_cpp_main(target_name)
        deps = [':' + dep for dep, target in target_graph.edges
                if target == target_name]
        yroot.append(CPP_TARGET.format(target_name, get_file_name(target_name),
                                       deps))
    with open(YROOT_TMPL, 'r') as yroot_tmpl_file:
        yroot_data = yroot_tmpl_file.read()
    with open(config.BUILD_PROJ_FILE, 'w') as yroot_file:
        yroot_file.write(yroot_data + '\n\n'.join(yroot))
    shutil.copyfile(YSETTINGS, 'YSettings')
    return targets_names, target_graph


def generate_cpp_main(target_name, string_to_print=None):
    if string_to_print is None:
        string_to_print = target_name
    with open(CPP_TMPL, 'r') as tmpl:
        code = tmpl.read().format(string_to_print)
    with open(get_file_name(target_name), 'w') as target_file:
        target_file.write(code)


def get_file_name(target_name):
    return join(target_name + '.cc')


def rebuild(basic_conf, targets_modified, targets_names, targets_graph):
    build(basic_conf)
    for target in targets_names:
        assert targets_modified[target] == \
               get_last_modified(basic_conf, target),\
            "target: {} was modified and it wasn't supposed to".format(target)


def rebuild_after_modify(basic_conf, targets_modified, targets_names,
                         targets_graph):
    target_to_change = random.choice(targets_names)
    logger.info('modifing target: {}'.format(target_to_change))
    generate_cpp_main(target_to_change, random_string())
    build(basic_conf)

    targets_to_build = list(nx.descendants(targets_graph, target_to_change))
    targets_to_build.append(target_to_change)

    for target in targets_names:
        last_modified = get_last_modified(basic_conf, target)
        if target in targets_to_build:
            assert last_modified != targets_modified[target],\
                "target: {} was supposed to be built again and" \
                " wasn't".format(target)
            targets_modified[target] = last_modified
        else:
            assert last_modified == targets_modified[target],\
                "target: {} was modified and it wasn't supposed" \
                " to".format(target)


def delete_file_and_return_no_modify(basic_conf, targets_modified,
                                     targets_names, targets_graph):
    target_to_delete = random.choice(targets_names)
    logger.info('deleting and returning the same for target: {}'
                .format(target_to_delete))
    file_name = get_file_name(target_to_delete)
    with open(file_name) as target_file:
        curr_content = target_file.read()
    os.remove(file_name)
    with open(file_name, 'w') as target_file:
        target_file.write(curr_content)

    build(basic_conf)

    for target in targets_names:
        assert targets_modified[target] == \
               get_last_modified(basic_conf, target)


def get_last_modified(basic_conf, target):
    return getmtime(join(basic_conf.builders_workspace_dir, 'release_flavor',
                         'CppProg', '_' + target, target + '.o'))


@slow
def test_caching(tmp_dir):
    targets_names, targets_graph = generate_dag_with_targets(NUM_TARGETS)
    reset_parser()
    basic_conf = cli.init_and_get_conf(['--non-interactive', 'build'])
    extend.Plugin.load_plugins(basic_conf)
    basic_conf.targets = [':' + target for target in targets_names]

    build(basic_conf)
    logger.info('done first build')

    targets_modified = {}
    for target in targets_names:
        targets_modified[target] = get_last_modified(basic_conf, target)

    tests = [rebuild, rebuild_after_modify, delete_file_and_return_no_modify]
    for i in range(NUM_TESTS):
        test_func = random.choice(tests)
        logger.info('starting build number: {} with func: {}'.format(
            i + 2, test_func.__name__))
        test_func(basic_conf, targets_modified, targets_names, targets_graph)


def build(basic_conf):
    build_context = BuildContext(basic_conf)
    populate_targets_graph(build_context, basic_conf)
    build_context.build_graph()
