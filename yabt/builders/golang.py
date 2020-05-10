# -*- coding: utf-8 -*-

# Copyright 2020 Resonai Ltd. All rights reserved
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
yabt Go Builder
~~~~~~~~~~~~~~~

:author: Itamar Ostricher

TODO: libs, external libs, protos, go test
TODO: does this even work with non-flat source file tree??
"""


from os.path import join, relpath

from ..artifact import ArtifactType as AT
from .dockerapp import build_app_docker_and_bin, register_app_builder_sig
from ..extend import (
    PropType as PT, register_build_func, register_builder_sig,
    register_manipulate_target_hook)
from ..logging import make_logger
from ..target_utils import split
from ..utils import rmtree, yprint


logger = make_logger(__name__)


<<<<<<< HEAD
register_app_builder_sig(
    'GoApp', [('executable', PT.File, None), ('main', PT.Target, None)])
=======
register_app_builder_sig('GoApp', [('main', PT.Target)])
>>>>>>> origin/go-builders


@register_manipulate_target_hook('GoApp')
def go_app_manipulate_target(build_context, target):
    logger.debug('Injecting {} to deps of {}',
                 target.props.base_image, target.name)
    target.deps.append(target.props.base_image)
    if target.props.main and target.props.main not in target.deps:
        logger.debug('Injecting {} to deps of {}',
                     target.props.main, target.name)
        target.deps.append(target.props.main)


@register_build_func('GoApp')
def go_app_builder(build_context, target):
    """Pack a Go binary as a Docker image with its runtime dependencies."""
    yprint(build_context.conf, 'Build GoApp', target)
<<<<<<< HEAD
    if target.props.executable and target.props.main:
        raise KeyError(
            '`main` and `executable` arguments are mutually exclusive')
    if target.props.executable:
        if target.props.executable not in target.artifacts.get(AT.app):
            target.artifacts.add(AT.app, target.props.executable)
        entrypoint = [target.props.executable]
    elif target.props.main:
        prog = build_context.targets[target.props.main]
        binary = list(prog.artifacts.get(AT.binary).keys())[0]
        entrypoint = ['/usr/src/bin/' + binary]
    else:
        raise KeyError('Must specify either `main` or `executable` argument')
=======
    prog = build_context.targets[target.props.main]
    binary = list(prog.artifacts.get(AT.binary).keys())[0]
    entrypoint = ['/usr/src/bin/' + binary]
>>>>>>> origin/go-builders
    build_app_docker_and_bin(
        build_context, target, entrypoint=entrypoint)


register_builder_sig(
    'GoProg',
    [('sources', PT.FileList),
     ('in_buildenv', PT.Target),
     ('cmd_env', None),
     ])


@register_manipulate_target_hook('GoProg')
def go_prog_manipulate_target(build_context, target):
    target.buildenv = target.props.in_buildenv


@register_build_func('GoProg')
def go_prog_builder(build_context, target):
    """Build a Go binary executable"""
    yprint(build_context.conf, 'Build GoProg', target)
    workspace_dir = build_context.get_workspace('GoProg', target.name)
    rmtree(workspace_dir)
    binary = join(*split(target.name))
    buildenv_sources = [build_context.conf.host_to_buildenv_path(source)
                        for source in target.props.sources]
    buildenv_workspace = build_context.conf.host_to_buildenv_path(
        workspace_dir)
    bin_file = join(buildenv_workspace, binary)
    build_cmd = ['go', 'build', '-o', bin_file] + buildenv_sources
    build_cmd_env = {
        'CGO_ENABLED': 0,
        'XDG_CACHE_HOME': '/tmp/.cache',
    }
    build_cmd_env.update(target.props.cmd_env or {})
    build_context.run_in_buildenv(
        target.props.in_buildenv, build_cmd, build_cmd_env)
    target.artifacts.add(
        AT.binary,
        relpath(join(workspace_dir, binary), build_context.conf.project_root),
        binary)
