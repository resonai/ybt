# -*- coding: utf-8 -*-

# Copyright 2018 Resonai Ltd. All rights reserved
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

:author: Itamar Ostricher
"""


from os.path import join
import shutil
from subprocess import check_output

import pytest

from . import cpp
from ..buildcontext import BuildContext
from ..graph import populate_targets_graph


slow = pytest.mark.skipif(not pytest.config.getoption('--with-slow'),
                          reason='need --with-slow option to run')


def clear_bin():
    try:
        shutil.rmtree('ybt_bin')
    except FileNotFoundError:
        pass


@pytest.mark.usefixtures('in_cpp_project')
@pytest.mark.parametrize(
    'test_case',
    (
        ('compiler_config:defaults', 'clang++-5.0',
         ['-std=c++14', '-Wall', '-fcolor-diagnostics', '-O2', '-DDEBUG'], []),
        ('compiler_config:override-compiler', 'foobar',
         ['-std=c++14', '-Wall', '-fcolor-diagnostics', '-O2', '-DDEBUG'], []),
        ('compiler_config:override-flags', 'clang++-5.0', ['-foo', 'bar'], []),
        # TODO: known failure - make it work...
        # ('compiler_config:override-flags-empty', 'clang++-5.0', [], []),
        ('compiler_config:post-extend-flags', 'clang++-5.0',
         ['-std=c++14', '-Wall', '-fcolor-diagnostics',
          '-O2', '-DDEBUG', '-foo', 'bar'], []),
        ('compiler_config:pre-extend-flags', 'clang++-5.0',
         ['-foo', 'bar', '-std=c++14', '-Wall', '-fcolor-diagnostics',
          '-O2', '-DDEBUG'], []),
        ('compiler_config:dep-extend-flags', 'clang++-5.0',
         ['-std=c++14', '-Wall', '-fcolor-diagnostics',
          '-O2', '-DDEBUG', '-DFOO=BAR'], ['-lfoo']),
    ))
def test_compiler_config(basic_conf, test_case):
    target_name, exp_compiler, exp_compile_flags, exp_link_flags = test_case
    build_context = BuildContext(basic_conf)
    basic_conf.targets = [target_name]
    populate_targets_graph(build_context, basic_conf)
    target = build_context.targets[target_name]
    cc = cpp.CompilerConfig(build_context, target)
    assert cc.compiler == exp_compiler
    assert cc.compile_flags == exp_compile_flags
    assert cc.link_flags == exp_link_flags
    # also check flavored workspace dir
    assert (build_context.get_workspace('foo', 'bar:baz') ==
            join(basic_conf.project_root,
                 'yabtwork', 'release_flavor', 'foo', 'bar_baz'))


@pytest.mark.usefixtures('in_cpp_project')
@pytest.mark.parametrize(
    'test_case',
    (
        ('compiler_config:defaults', 'clang++-5.0',
         ['-std=c++14', '-Wall', '-fcolor-diagnostics', '-g', '-DDEBUG']),
        ('compiler_config:override-compiler', 'foobar',
         ['-std=c++14', '-Wall', '-fcolor-diagnostics', '-g', '-DDEBUG']),
        ('compiler_config:override-flags', 'clang++-5.0', ['-foo', 'bar']),
        # TODO: known failure - make it work...
        # ('compiler_config:override-flags-empty', 'clang++-5.0', []),
        ('compiler_config:post-extend-flags', 'clang++-5.0',
         ['-std=c++14', '-Wall', '-fcolor-diagnostics',
          '-g', '-DDEBUG', '-foo', 'bar']),
        ('compiler_config:pre-extend-flags', 'clang++-5.0',
         ['-foo', 'bar', '-std=c++14', '-Wall', '-fcolor-diagnostics',
          '-g', '-DDEBUG']),
    ))
def test_compiler_config_debug(debug_conf, test_case):
    target_name, exp_compiler, exp_flags = test_case
    build_context = BuildContext(debug_conf)
    debug_conf.targets = [target_name]
    populate_targets_graph(build_context, debug_conf)
    target = build_context.targets[target_name]
    cc = cpp.CompilerConfig(build_context, target)
    assert cc.compiler == exp_compiler
    assert cc.compile_flags == exp_flags
    # also check flavored workspace dir
    assert (build_context.get_workspace('foo', 'bar:baz') ==
            join(debug_conf.project_root,
                 'yabtwork', 'debug_flavor', 'foo', 'bar_baz'))


@slow
@pytest.mark.parametrize(
    'target_name',
    ('hello:hello-app', 'hello_lib:hello-app', 'hello_mod/main:hello-app'))
@pytest.mark.usefixtures('in_cpp_project')
def test_cpp_builder(basic_conf, target_name):
    clear_bin()
    build_context = BuildContext(basic_conf)
    basic_conf.targets = [target_name]
    populate_targets_graph(build_context, basic_conf)
    build_context.build_graph()
    hello_out = str(
        check_output(['ybt_bin/{}'.format(target_name.replace(':', '/'))]))
    assert 'Hello world' in hello_out
    clear_bin()


@slow
@pytest.mark.usefixtures('in_tests_project')
def test_cpp_tester_success(basic_conf):
    build_context = BuildContext(basic_conf)
    basic_conf.targets = ['hello_gtest:greet-test']
    populate_targets_graph(build_context, basic_conf)
    build_context.build_graph(run_tests=True)


@slow
@pytest.mark.usefixtures('in_tests_project')
def test_cpp_tester_fail(basic_conf):
    build_context = BuildContext(basic_conf)
    basic_conf.targets = ['hello_gtest:greet-failing-test']
    populate_targets_graph(build_context, basic_conf)
    with pytest.raises(SystemExit):
        build_context.build_graph(run_tests=True)
