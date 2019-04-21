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

import networkx as nx
import os
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
NUM_TESTS = 20

TMPL_DIR = join(dirname(abspath(__file__)), '..', 'tests', 'data',
                'caching')
CPP_TMPL = 'cpp_prog.cc.tmpl'
CPP_TEST_TMPL = 'cpp_test.cc.tmpl'
CPP_TARGET = """CppProg(
    '{}',
    sources='{}',
    in_buildenv=':builder', deps={}
)"""
CPP_TEST_TARGET = """CppGTest(
    '{}',
    sources='{}',
    in_buildenv=':builder-with-gtest',
    deps={}
)"""
YROOT_TMPL = 'YRoot.tmpl'
INSTALL_GTEST_SCRIPT ='install-gtest.sh'
YSETTINGS = 'YSettings'

slow = pytest.mark.skipif(not pytest.config.getoption('--with-slow'),
                          reason='need --with-slow option to run')

logger = make_logger(__name__)


def random_string():
    return ''.join([random.choice(string.ascii_letters + string.digits)
                    for _ in range(random.randint(20, 40))])


def generate_dag_with_targets(size):
    targets = [random_string() for _ in range(size)]
    test_targets = [random_string() + '_test' for _ in range(size)]
    target_graph = generate_random_dag(targets + test_targets)
    for target in targets:
        generate_cpp_main(target)
    for test_target in test_targets:
        generate_cpp_test(test_target)
    generate_yroot(target_graph, targets, test_targets)
    shutil.copyfile(join(TMPL_DIR, YSETTINGS), YSETTINGS)
    return targets, test_targets, target_graph


def generate_yroot(target_graph, targets, test_targets):
    yroot = []
    for target in targets:
        yroot.append(CPP_TARGET.format(target, get_file_name(target),
                                       get_dependencies(target, target_graph)))
    for target in test_targets:
        yroot.append(CPP_TEST_TARGET.format(target, get_file_name(target),
                                            get_dependencies(target,
                                                             target_graph)))
    with open(join(TMPL_DIR, YROOT_TMPL), 'r') as yroot_tmpl_file:
        yroot_data = yroot_tmpl_file.read()
    with open(config.BUILD_PROJ_FILE, 'w') as yroot_file:
        yroot_file.write(yroot_data + '\n\n'.join(yroot))
    shutil.copyfile(join(TMPL_DIR, INSTALL_GTEST_SCRIPT), INSTALL_GTEST_SCRIPT)


def get_dependencies(target, target_graph):
    return [':' + dep for dep, other_target in target_graph.edges
            if other_target == target]


def generate_cpp_main(target, string_to_print=None):
    if string_to_print is None:
        string_to_print = target
    with open(join(TMPL_DIR, CPP_TMPL), 'r') as tmpl:
        code = tmpl.read().format(string_to_print)
    with open(get_file_name(target), 'w') as target_file:
        target_file.write(code)


def generate_cpp_test(target):
    with open(join(TMPL_DIR, CPP_TEST_TMPL), 'r') as tmpl:
        code = tmpl.read().format(target)
    with open(get_file_name(target), 'w') as target_file:
        target_file.write(code)


def get_file_name(target):
    return join(target + '.cc')


def rebuild(basic_conf, targets_modified, targets, targets_graph, test_tragets):
    build(basic_conf)
    check_modified_targets(basic_conf, targets_modified, targets, [])


def rebuild_after_modify(basic_conf, targets_modified, targets, targets_graph,
                         test_targets):
    target_to_change = random.choice(targets)
    logger.info('modifing target: {}'.format(target_to_change))
    generate_cpp_main(target_to_change, random_string())
    build(basic_conf)

    targets_to_build = list(nx.descendants(targets_graph, target_to_change))
    targets_to_build.append(target_to_change)

    check_modified_targets(basic_conf, targets_modified, targets,
                           targets_to_build)


def check_modified_targets(basic_conf, targets_modified, targets,
                           targets_to_build):
    for target in targets:
        last_modified = get_last_modified(basic_conf, target)
        if target in targets_to_build:
            assert last_modified != targets_modified[target], \
                "target: {} was supposed to be built again and" \
                " wasn't".format(target)
            targets_modified[target] = last_modified
        else:
            assert last_modified == targets_modified[target], \
                "target: {} was modified and it wasn't supposed" \
                " to".format(target)


def delete_file_and_return_no_modify(basic_conf, targets_modified,
                                     targets, targets_graph, test_targets):
    target_to_delete = random.choice(targets)
    logger.info('deleting and returning the same for target: {}'
                .format(target_to_delete))
    file_name = get_file_name(target_to_delete)
    with open(file_name) as target_file:
        curr_content = target_file.read()
    os.remove(file_name)
    with open(file_name, 'w') as target_file:
        target_file.write(curr_content)

    build(basic_conf)
    check_modified_targets(basic_conf, targets_modified, targets, [])


def add_dependency(basic_conf, targets_modified, targets, targets_graph,
                   test_targets):
    new_target = random_string()
    logger.info('adding target: ' + new_target)
    targets.append(new_target)
    basic_conf.targets.append(':' + new_target)
    generate_cpp_main(new_target)
    targets_graph.add_node(new_target)
    targets_graph.add_edges_from((new_target, targets[i])
                                 for i in range(len(targets) - 1)
                                 if random.random() > 0.8)
    generate_yroot(targets_graph, targets, test_targets)
    targets_modified[new_target] = None
    build(basic_conf)
    targets_to_build = nx.descendants(targets_graph, new_target)
    targets_to_build.add(new_target)
    check_modified_targets(basic_conf, targets_modified, targets,
                           targets_to_build)


def get_last_modified(basic_conf, target):
    return getmtime(join(basic_conf.builders_workspace_dir, 'release_flavor',
                         'CppProg', '_' + target, target + '.o'))


@slow
def test_caching(tmp_dir):
    targets, test_targets, targets_graph =\
        generate_dag_with_targets(NUM_TARGETS)
    reset_parser()
    basic_conf = cli.init_and_get_conf(['--non-interactive', 'build'])
    extend.Plugin.load_plugins(basic_conf)
    basic_conf.targets = [':' + target for target in targets] + \
                         [':' + target for target in test_targets]

    build(basic_conf)
    logger.info('done first build')

    targets_modified = {}
    for target in targets:
        targets_modified[target] = get_last_modified(basic_conf, target)

    tests = [rebuild, rebuild_after_modify, delete_file_and_return_no_modify,
             add_dependency]
    for i in range(NUM_TESTS):
        test_func = random.choice(tests)
        logger.info('starting build number: {} with func: {}'.format(
            i + 2, test_func.__name__))
        test_func(basic_conf, targets_modified, targets, targets_graph,
                  test_targets)


def build(basic_conf):
    build_context = BuildContext(basic_conf)
    populate_targets_graph(build_context, basic_conf)
    build_context.build_graph(run_tests=True)
