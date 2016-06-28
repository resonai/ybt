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

# pylint: disable=invalid-name, unused-argument

"""
yabt Python Builders
~~~~~~~~~~~~~~~~~~~~

:author: Itamar Ostricher
"""


from .dockerapp import build_app_docker_and_bin, register_app_builder_sig
from ..extend import (
    PropType as PT, register_build_func, register_builder_sig,
    register_manipulate_target_hook)
from ..logging import make_logger
from ..utils import yprint


logger = make_logger(__name__)


register_builder_sig(
    'PythonPackage',
    [('package', PT.str),
     ('version', PT.str, None),
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
