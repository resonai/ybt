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

import json
import networkx as nx
import os
from os.path import join, dirname, abspath, getmtime, isfile
import pytest
import random
import shutil
import string
from unittest.mock import Mock

from conftest import reset_parser
from yabt.builders import cpp
from yabt.extend import Plugin
from . import config, cli, extend
from .buildcontext import BuildContext
from .global_cache import SUMMARY_FILE, ARTIFACTS_FILE, TARGETS_DIR, \
    ARTIFACTS_DIR
from .graph import populate_targets_graph
from .logging import make_logger
from .test_utils import generate_random_dag

NUM_TARGETS = 10
NUM_TESTS = 20

TMPL_DIR = join(dirname(abspath(__file__)), '..', 'tests', 'data',
                'caching')
CPP_TMPL = 'cpp_prog.cc.tmpl'
CPP_TEST_TMPL = 'cpp_test.cc.tmpl'
FAILING_TEST_TMPL = 'cpp_failing_test.cc.tmpl'
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
INSTALL_GTEST_SCRIPT = 'install-gtest.sh'
INSTALL_LLVM_REPO_KEY_SCRIPT = 'install-llvm-repo-key.sh'
YSETTINGS = 'YSettings'

TARGET_TYPES = {
    'CppProg': (CPP_TMPL, CPP_TARGET),
    'CppGTest': (CPP_TEST_TMPL, CPP_TEST_TARGET)
}

GLOBAL_CACHE_DIR = '.global_cache'

logger = make_logger(__name__)


class ProjectContext:
    def __init__(self):
        self.targets = {}
        self.test_targets = []
        self.targets_graph = None
        self.last_modified = {}
        self.last_run_tests = {}
        self.conf = None


def generate_random_project(size) -> ProjectContext:
    project = ProjectContext()
    targets = [random_string() for _ in range(size)]
    project.targets_graph = generate_random_dag(targets)
    for target in targets:
        target_type = random.choice(list(TARGET_TYPES.keys()))
        generate_file(target, target_type)
        project.targets[target] = target_type
        if target_type == 'CppGTest':
            project.test_targets.append(target)
    generate_yroot(project)
    with open(join(TMPL_DIR, YSETTINGS + '.tmpl'), 'r') as tmpl:
        ysettings = tmpl.read().format(GLOBAL_CACHE_DIR)
    with open(YSETTINGS, 'w') as ysettings_file:
        ysettings_file.write(ysettings)
    return project


def random_string():
    return ''.join([random.choice(string.ascii_letters + string.digits)
                    for _ in range(random.randint(20, 40))])


def generate_yroot(project: ProjectContext):
    yroot = []
    for target, target_type in project.targets.items():
        yroot.append(TARGET_TYPES[target_type][1].format(
            target, get_file_name(target),
            get_dependencies(target, project.targets_graph)))
    with open(join(TMPL_DIR, YROOT_TMPL), 'r') as yroot_tmpl_file:
        yroot_data = yroot_tmpl_file.read()
    with open(config.BUILD_PROJ_FILE, 'w') as yroot_file:
        yroot_file.write(yroot_data + '\n\n'.join(yroot))
    shutil.copyfile(join(TMPL_DIR, INSTALL_GTEST_SCRIPT), INSTALL_GTEST_SCRIPT)
    shutil.copyfile(join(TMPL_DIR, INSTALL_LLVM_REPO_KEY_SCRIPT),
                    INSTALL_LLVM_REPO_KEY_SCRIPT)


def get_dependencies(target, target_graph):
    return [':' + dep for dep, other_target in target_graph.edges
            if other_target == target]


def generate_file(target, target_type, string_to_print=None):
    if string_to_print is None:
        string_to_print = target
    with open(join(TMPL_DIR, TARGET_TYPES[target_type][0]), 'r') as tmpl:
        code = tmpl.read().format(string_to_print)
    with open(get_file_name(target), 'w') as target_file:
        target_file.write(code)


def get_file_name(target):
    return join(target + '.cc')


def init_project(project):
    reset_parser()
    project.conf = cli.init_and_get_conf(['--non-interactive',
                                          '--continue-after-fail', 'build',
                                          '--upload-to-global-cache',
                                          '--download-from-global-cache',
                                          '--download-tests-from-global-cache',
                                          '--upload-tests-to-global-cache'])
    extend.Plugin.load_plugins(project.conf)
    project.conf.targets = [':' + target for target in project.targets.keys()]
    build_context = BuildContext(project.conf)
    populate_targets_graph(build_context, project.conf)
    return build_context


def rebuild(project: ProjectContext):
    build_context = init_project(project)
    build_context.build_graph(run_tests=True)
    check_modified_targets(project, build_context, [])


def rebuild_after_modify(project: ProjectContext):
    target_to_change = random.choice(list(project.targets.keys()))
    logger.info('modifing target: {}'.format(target_to_change))
    generate_file(target_to_change, project.targets[target_to_change],
                  random_string())
    build_context = init_project(project)
    build_context.build_graph(run_tests=True)

    targets_to_build = nx.descendants(project.targets_graph, target_to_change)
    targets_to_build.add(target_to_change)
    check_modified_targets(project, build_context, targets_to_build)


def delete_file_and_return_no_modify(project: ProjectContext):
    target_to_delete = random.choice(list(project.targets.keys()))
    logger.info('deleting and returning the same for target: {}'
                .format(target_to_delete))
    file_name = get_file_name(target_to_delete)
    with open(file_name) as target_file:
        curr_content = target_file.read()
    os.remove(file_name)
    with open(file_name, 'w') as target_file:
        target_file.write(curr_content)

    build_context = init_project(project)
    build_context.build_graph(run_tests=True)
    check_modified_targets(project, build_context, [])


def add_dependency(project: ProjectContext):
    new_target = random_string()
    target_type = random.choice(list(TARGET_TYPES.keys()))
    logger.info('adding target: {} of type: {}'.format(new_target,
                                                       target_type))
    project.targets[new_target] = target_type
    project.last_modified[new_target] = None
    if target_type == 'CppGTest':
        project.test_targets.append(new_target)
        project.last_run_tests[new_target] = None
    project.conf.targets.append(':' + new_target)
    generate_file(new_target, target_type)

    project.targets_graph.add_node(new_target)
    targets = list(project.targets.keys())
    project.targets_graph.add_edges_from(
        (new_target, targets[i]) for i in range(len(targets) - 1)
        if random.random() > 0.8 and targets[i] != new_target)
    generate_yroot(project)

    build_context = init_project(project)
    build_context.build_graph(run_tests=True)
    targets_to_build = nx.descendants(project.targets_graph, new_target)
    targets_to_build.add(new_target)
    check_modified_targets(project, build_context, targets_to_build)


def download_from_global_cache(project: ProjectContext):
    target = random.choice(list(project.targets.keys()))
    build_context = init_project(project)
    build_context.build_graph(run_tests=True)
    check_modified_targets(project, build_context, [])
    cache_dir = project.conf.get_cache_dir(
        build_context.targets[':' + target], build_context)
    logger.info('removing cache from: {} of target: {}'.format(cache_dir,
                                                               target))
    shutil.rmtree(cache_dir)

    cppgtest_mock = Mock()
    old_cppgtest_builder = Plugin.builders['CppGTest']
    old_cppgtest_hook = Plugin.hooks['manipulate_target']['CppGTest']
    Plugin.remove_builder('CppGTest')
    Plugin.builders['CppGTest'] = cppgtest_mock
    cppgtest_mock.func.side_effect = cpp.cpp_gtest_builder
    Plugin.hooks['manipulate_target']['CppGTest'] = old_cppgtest_hook

    build_context.build_graph(run_tests=True)
    cppgtest_mock.test_func.assert_not_called()
    check_modified_targets(project, build_context, [], [target])

    Plugin.remove_builder('CppGTest')
    Plugin.builders['CppGTest'] = old_cppgtest_builder
    Plugin.hooks['manipulate_target']['CppGTest'] = old_cppgtest_hook


def no_cache_at_all(project: ProjectContext):
    target_name = random.choice(list(project.targets.keys()))
    build_context = init_project(project)
    build_context.build_graph(run_tests=True)
    check_modified_targets(project, build_context, [])
    target = build_context.targets[':' + target_name]
    logger.info('removing local and global cache of target: {}'.format(
        target_name))
    shutil.rmtree(project.conf.get_cache_dir(target, build_context))
    shutil.rmtree(join(GLOBAL_CACHE_DIR, TARGETS_DIR,
                       target.hash(build_context)))
    build_context.build_graph(run_tests=True)
    targets_to_build = nx.descendants(project.targets_graph, target_name)
    targets_to_build.add(target_name)
    check_modified_targets(project, build_context, targets_to_build)


def failing_test(project: ProjectContext):
    test_to_fail = random.choice(project.test_targets)
    logger.info('Making target: {} fail'.format(test_to_fail))
    with open(join(TMPL_DIR, FAILING_TEST_TMPL), 'r') as tmpl:
        code = tmpl.read().format(test_to_fail)
    with open(get_file_name(test_to_fail), 'w') as target_file:
        target_file.write(code)

    build_context = init_project(project)
    with pytest.raises(SystemExit):
        build_context.build_graph(run_tests=True)
    test_cache = get_test_cache(project.conf, test_to_fail, build_context)
    assert not os.path.isfile(test_cache), \
        "test: {} is failing but was put into cache".format(test_to_fail)

    generate_file(test_to_fail, project.targets[test_to_fail], random_string())
    build_context = init_project(project)
    build_context.build_graph(run_tests=True)
    targets_to_build = nx.descendants(project.targets_graph, test_to_fail)
    targets_to_build.add(test_to_fail)
    check_modified_targets(project, build_context, targets_to_build)


def randomly_delete_global_cache(project: ProjectContext, file_to_delete):
    build_context = init_project(project)
    build_context.build_graph(run_tests=True)
    paths_to_delete, targets_to_delete = get_random_targets_to_delete(
        project, build_context)
    for path in paths_to_delete:
        if isfile(join(path, file_to_delete)):
            os.remove(join(path, file_to_delete))

    remove_targets_from_local_cache(build_context, project, targets_to_delete)
    build_and_check_built(project, targets_to_delete)
    logger.info('deleted targets: {}, paths deleted: {}'.format(
        targets_to_delete, paths_to_delete))


def remove_targets_from_local_cache(build_context, project, targets_to_delete):
    for target in targets_to_delete:
        shutil.rmtree(project.conf.get_cache_dir(
            build_context.targets[':' + target], build_context))


def randomly_delete_summary_from_global_cache(project: ProjectContext):
    randomly_delete_global_cache(project, SUMMARY_FILE)


def randomly_delete_artifacts_desc_from_global_cache(project: ProjectContext):
    randomly_delete_global_cache(project, ARTIFACTS_FILE)


def randomly_delete_artifacts_from_global_cache(project: ProjectContext):
    build_context = init_project(project)
    build_context.build_graph(run_tests=True)
    paths_to_delete, targets_to_build = get_random_artifacts_to_delete(
        project, build_context)
    for path in paths_to_delete:
        os.remove(path)
    remove_targets_from_local_cache(build_context, project, targets_to_build)

    build_and_check_built(project, targets_to_build)


def build_and_check_built(project, modified_targets):
    build_context = init_project(project)
    build_context.build_graph(run_tests=True)
    targets_to_build = set(modified_targets)
    for target in modified_targets:
        targets_to_build.update(nx.descendants(project.targets_graph, target))
    check_modified_targets(project, build_context, targets_to_build)


def get_random_targets_to_delete(project: ProjectContext,
                                 build_context: BuildContext):
    targets_dir = join(GLOBAL_CACHE_DIR, TARGETS_DIR)
    all_targets = os.listdir(targets_dir)
    paths_to_delete = [join(targets_dir, filename) for filename in
                       random.sample(all_targets, len(all_targets) // 10)]
    targets_to_delete = []
    for path in paths_to_delete:
        if isfile(join(path, SUMMARY_FILE)):
            with open(join(path, SUMMARY_FILE), 'rb') as summary_file:
                summary = json.loads(summary_file.read().decode('utf-8'))
            target = summary['name'].strip(':')
            if target not in project.targets:
                paths_to_delete.remove(path)
            elif build_context.targets[summary['name']].hash(build_context) \
                    == os.path.split(path)[-1]:
                targets_to_delete.append(target)
    return paths_to_delete, targets_to_delete


def get_random_artifacts_to_delete(project: ProjectContext,
                                   build_context: BuildContext):
    targets_dir = join(GLOBAL_CACHE_DIR, TARGETS_DIR)
    artifacts_dir = join(GLOBAL_CACHE_DIR, ARTIFACTS_DIR)
    all_artifacts = os.listdir(artifacts_dir)
    artifacts_to_delete = set(random.sample(all_artifacts,
                                            len(all_artifacts) // 10))

    targets_to_build = set()
    for path in [join(targets_dir, file) for file in os.listdir(targets_dir)]:
        if isfile(join(path, ARTIFACTS_FILE)) \
                and isfile(join(path, SUMMARY_FILE)):
            with open(join(path, ARTIFACTS_FILE), 'rb') as f:
                artifact_desc = json.loads(f.read().decode('utf-8'))
            with open(join(path, SUMMARY_FILE), 'rb') as f:
                summary = json.loads(f.read().decode('utf-8'))
            target = summary['name'].strip(':')
            for type_name, artifact_list in artifact_desc.items():
                for artifact in artifact_list:
                    if artifact['hash'] in artifacts_to_delete:
                        if target not in project.targets:
                            artifacts_to_delete.remove(artifact['hash'])
                        elif build_context.targets[summary['name']].hash(
                                build_context) == os.path.split(path)[-1]:
                            targets_to_build.add(target)

    paths_to_delete = [join(artifacts_dir, filename) for filename in
                       artifacts_to_delete]
    return paths_to_delete, targets_to_build


def check_modified_targets(project: ProjectContext, build_context,
                           targets_to_build, tests_to_build=None):
    for target, target_type in project.targets.items():
        last_modified = get_last_modified(project.conf, target, target_type)
        if target in targets_to_build:
            assert last_modified != project.last_modified[target], \
                "target: {} was supposed to be built again and" \
                " wasn't".format(target)
            project.last_modified[target] = last_modified
        else:
            assert last_modified == project.last_modified[target], \
                "target: {} was modified and it wasn't supposed" \
                " to".format(target)

    tests_to_build = tests_to_build or targets_to_build
    for target in project.test_targets:
        last_run = getmtime(get_test_cache(project.conf, target,
                                           build_context))
        if target in tests_to_build:
            assert last_run != project.last_run_tests[target],\
                "test: {} was supposed to run again but wasn't".format(target)
            project.last_run_tests[target] = last_run
        else:
            assert last_run == project.last_run_tests[target],\
                "test: {} was rerun and it wasn't supposed to".format(target)


def get_last_modified(basic_conf, target, target_type):
    return getmtime(join(basic_conf.builders_workspace_dir, 'release_flavor',
                         target_type, '_' + target, target + '.o'))


def get_test_cache(basic_conf, target, build_context):
    return join(basic_conf.get_cache_dir(build_context.targets[':' + target],
                                         build_context), 'tested.json')


@pytest.mark.slow
def test_caching(tmp_dir):
    project = generate_random_project(NUM_TARGETS)

    build_context = init_project(project)
    build_context.build_graph(run_tests=True)
    logger.info('done first build')

    for target, target_type in project.targets.items():
        project.last_modified[target] = get_last_modified(project.conf, target,
                                                          target_type)
    for target in project.test_targets:
        project.last_run_tests[target] = getmtime(get_test_cache(
            project.conf, target, build_context))

    tests = [rebuild, rebuild_after_modify, delete_file_and_return_no_modify,
             add_dependency, failing_test, download_from_global_cache,
             no_cache_at_all, randomly_delete_summary_from_global_cache,
             randomly_delete_artifacts_desc_from_global_cache,
             randomly_delete_artifacts_from_global_cache]
    for i in range(NUM_TESTS):
        test_func = random.choice(tests)
        logger.info('starting build number: {} with func: {}'.format(
            i + 2, test_func.__name__))
        test_func(project)
