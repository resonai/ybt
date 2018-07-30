# -*- coding: utf-8 -*-

# Copyright 2016 Resonai Ltd. All rights reserved
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

# pylint: disable=invalid-name, unused-argument

"""
yabt Python Builders
~~~~~~~~~~~~~~~~~~~~

:author: Itamar Ostricher
"""

from itertools import chain
from os.path import join, relpath

from ostrich.utils.collections import listify

from ..artifact import ArtifactType as AT
from .dockerapp import build_app_docker_and_bin, register_app_builder_sig
from ..extend import (
    PropType as PT, register_build_func, register_builder_sig,
    register_manipulate_target_hook, register_test_func)
from ..logging import make_logger
from ..utils import rmtree, yprint


logger = make_logger(__name__)


def path_to_pymodule(fpath):
    if fpath.endswith('.py'):
        fpath = fpath[:-3]
    return '.'.join(fpath.split('/'))


register_builder_sig(
    'PythonPackage',
    [('package', PT.str),
     ('version', PT.str, None),
     ('pip', PT.str, 'pip2'),
     ])


@register_build_func('PythonPackage')
def python_package_builder(build_context, target):
    yprint(build_context.conf, 'Fetch and cache PyPI package', target)


@register_manipulate_target_hook('PythonPackage')
def python_package_manipulate_target(build_context, target):
    target.tags.add('pip-installable')


register_builder_sig(
    'Python',
    [('sources', PT.FileList, None),
     ('data', PT.FileList, None),
     ])


@register_build_func('Python')
def python_app_builder(build_context, target):
    yprint(build_context.conf, 'Build Python', target)
    for src in chain(target.props.sources, target.props.data):
        target.artifacts.add(AT.app, src)


register_app_builder_sig('PythonApp', [('main', PT.File)])


@register_manipulate_target_hook('PythonApp')
def python_app_manipulate_target(build_context, target):
    logger.debug('Injecting {} to deps of {}',
                 target.props.base_image, target.name)
    target.deps.append(target.props.base_image)


@register_build_func('PythonApp')
def python_app_builder(build_context, target):
    yprint(build_context.conf, 'Build PythonApp', target)
    build_app_docker_and_bin(
        build_context, target, entrypoint=[target.props.main])


register_builder_sig(
    'PythonTest',
    [('module', PT.File),
     ('test_cmd', PT.StrList, None),
     ('test_flags', PT.StrList, None),  # flags to append to test command
     ('test_env', None),  # env vars to inject in test process
     ('in_testenv', PT.Target, None),
     ])


@register_manipulate_target_hook('PythonTest')
def pythontest_manipulate_target(build_context, target):
    target.tags.add('testable')
    target.buildenv = target.props.in_testenv
    # doing test-command manipulation (and storing it in target props) during
    # target extraction (as opposed to during build) so it is considered
    # during target hashing (for cache)
    prepare_test_cmd(build_context, target)


@register_build_func('PythonTest')
def pythontest_builder(build_context, target):
    yprint(build_context.conf, 'Build PythonTest', target)


@register_test_func('PythonTest')
def pythontest_tester(build_context, target):
    """Run a Python test"""
    yprint(build_context.conf, 'Run PythonTest', target)
    workspace_dir = build_context.get_workspace('PythonTest', target.name)

    # Link generated Python protos & required binaries
    gen_dir = join(workspace_dir, 'gen')
    rmtree(gen_dir)
    for dep in build_context.generate_all_deps(target):
        dep.artifacts.link_types(
            workspace_dir, [AT.gen_py, AT.binary], build_context.conf)

    # Run the test module
    test_env = target.props.test_env or {}
    pypath = test_env.get('PYTHONPATH', '.').split(':')
    pypath.append(relpath(gen_dir, build_context.conf.project_root))
    test_env['PYTHONPATH'] = ':'.join(pypath)
    test_env['BIN_DIR'] = build_context.conf.host_to_buildenv_path(
        join(workspace_dir, 'bin'))
    build_context.run_in_buildenv(
        target.props.in_testenv, target.props.test_cmd, test_env)


def prepare_test_cmd(build_context, target):
    pytest_params = build_context.conf.get('pytest_params', {})
    test_cmd = target.props.test_cmd
    if not test_cmd:
        test_cmd = list(listify(pytest_params.get('default_test_cmd',
                                                  ['python', '-m'])))
    test_cmd.append(path_to_pymodule(target.props.module))
    test_cmd.extend(target.props.test_flags)
    test_cmd.extend(listify(pytest_params.get('extra_exec_flags')))
    target.props.test_cmd = test_cmd
