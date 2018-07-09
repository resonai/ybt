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


from ostrich.utils.collections import listify

from .dockerapp import build_app_docker_and_bin, register_app_builder_sig
from ..extend import (
    PropType as PT, register_build_func, register_builder_sig,
    register_manipulate_target_hook, register_test_func)
from ..logging import make_logger
from ..utils import yprint


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
    target.artifacts['app'].extend(target.props.sources)
    target.artifacts['app'].extend(target.props.data)


register_app_builder_sig('PythonApp', [('main', PT.File)])


@register_manipulate_target_hook('PythonApp')
def python_app_manipulate_target(build_context, target):
    logger.debug('Injecting "{}" to deps of {}',
                 target.props.base_image, target)
    target.deps.append(target.props.base_image)


@register_build_func('PythonApp')
def python_app_builder(build_context, target):
    yprint(build_context.conf, 'Build PythonApp', target)
    if target.props.main not in target.artifacts['app']:
        target.artifacts['app'].append(target.props.main)
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


@register_build_func('PythonTest')
def pythontest_builder(build_context, target):
    yprint(build_context.conf, 'Build PythonTest', target)


@register_test_func('PythonTest')
def pythontest_tester(build_context, target):
    """Run a Python test"""
    yprint(build_context.conf, 'Run PythonTest', target)
    pytest_params = build_context.conf.get('pytest_params', {})
    test_cmd = target.props.test_cmd
    if not test_cmd:
        test_cmd = list(listify(pytest_params.get('default_test_cmd',
                                                  ['python', '-m'])))
    test_cmd.append(path_to_pymodule(target.props.module))
    test_cmd.extend(target.props.test_flags)
    test_cmd.extend(listify(pytest_params.get('extra_exec_flags')))
    test_env = target.props.test_env or {}
    test_env.setdefault('PYTHONPATH', '.')
    build_context.run_in_buildenv(target.props.in_testenv, test_cmd, test_env)
