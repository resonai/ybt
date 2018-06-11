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
yabt C++ Builder
~~~~~~~~~~~~~~~~

:author: Itamar Ostricher

TODO: support injecting compile/link flags for 3rd party libs
TODO: support flavors
TODO: CppSharedLib builder
"""


from os.path import basename, dirname, join, relpath, splitext

from .dockerapp import build_app_docker_and_bin, register_app_builder_sig
from ..extend import (
    PropType as PT, register_build_func, register_builder_sig,
    register_manipulate_target_hook)
from ..logging import make_logger
from ..target_utils import split
from ..utils import link_artifacts, yprint


logger = make_logger(__name__)


register_app_builder_sig(
    'CppApp', [('executable', PT.File, None), ('main', PT.Target, None)])


@register_manipulate_target_hook('CppApp')
def cpp_app_manipulate_target(build_context, target):
    logger.debug('Injecting "{}" to deps of {}',
                 target.props.base_image, target)
    target.deps.append(target.props.base_image)
    if target.props.main and target.props.main not in target.deps:
        logger.debug('Injecting "{}" to deps of {}',
                     target.props.main, target)
        target.deps.append(target.props.main)


@register_build_func('CppApp')
def cpp_app_builder(build_context, target):
    """Pack a C++ binary as a Docker image with its runtime dependencies.

    TODO(itamar): Dynamically analyze the binary and copy shared objects
    from its buildenv image to the runtime image, unless they're installed.
    """
    yprint(build_context.conf, 'Build CppApp', target)
    if target.props.executable and target.props.main:
        raise KeyError(
            '`main` and `executable` arguments are mutually exclusive')
    if target.props.executable:
        if target.props.executable not in target.artifacts['app']:
            target.artifacts['app'].append(target.props.executable)
        entrypoint = [target.props.executable]
    elif target.props.main:
        prog = build_context.targets[target.props.main]
        entrypoint = [join('/usr/src/gen',
                           list(prog.artifacts['gen'].keys())[0])]
    else:
        raise KeyError('Must specify either `main` or `executable` argument')
    build_app_docker_and_bin(
        build_context, target, entrypoint=entrypoint)


register_builder_sig(
    'CppProg',
    [('binary', PT.File),
     ('sources', PT.FileList),
     ('in_buildenv', PT.Target),
     ('headers', PT.FileList, None),
     ('cmd_env', None),
     # ('copy_bin_to', PT.File, None),
     ])


@register_manipulate_target_hook('CppProg')
def cpp_prog_manipulate_target(build_context, target):
    target.buildenv = target.props.in_buildenv


def compile_cc(build_context, buildenv, sources, workspace_dir,
               buildenv_workspace, cmd_env):
    """Compile list of C++ source files in a buildenv image
       and return list of generated object file.
    """
    objects = []
    for src in sources:
        obj_rel_path = '{}.o'.format(splitext(src)[0])
        obj_file = join(buildenv_workspace, obj_rel_path)
        # TODO: compiler flags should come from target & project config
        obj_cmd = [
            CC, '-o', obj_file, '-c',
            '-std=c++11', '-Wall', '-fvectorize', '-fslp-vectorize',
            '-fcolor-diagnostics', '-O2', '-DDEBUG',
            '-I{}'.format(buildenv_workspace),
            join(buildenv_workspace, src)]
        # TODO: capture and transform error messages from compiler so file
        # paths match host paths for smooth(er) editor / IDE integration
        build_context.run_in_buildenv(buildenv, obj_cmd, cmd_env)
        objects.append(
            join(relpath(workspace_dir, build_context.conf.project_root),
                 obj_rel_path))
    return objects


# TODO: make configurable
CC = 'clang++-5.0'


@register_build_func('CppProg')
def cpp_prog_builder(build_context, target):
    """Build a C++ binary executable"""
    yprint(build_context.conf, 'Build CppProg', target)
    workspace_dir = build_context.get_workspace('CppProg', target.name)
    all_files = target.props.sources + target.props.headers
    # add headers of direct dependencies
    for dep in build_context.generate_direct_deps(target):
        all_files.extend(dep.props.get('headers', []))
    # add objects of all dependencies (direct & transitive)
    objects = []
    for dep in build_context.generate_all_deps(target):
        objects.extend(dep.props.get('objects', []))
    all_files.extend(objects)
    link_artifacts(all_files, workspace_dir, None, build_context.conf)
    buildenv_workspace = build_context.conf.host_to_buildenv_path(
        workspace_dir)
    objects.extend(compile_cc(
        build_context, target.props.in_buildenv, target.props.sources,
        workspace_dir, buildenv_workspace, target.props.cmd_env))
    bin_file = join(buildenv_workspace, target.props.binary)
    # TODO: linker flags should come from target & project conf
    bin_cmd = [CC, '-o', bin_file] + objects
    build_context.run_in_buildenv(
        target.props.in_buildenv, bin_cmd, target.props.cmd_env)
    target.artifacts['gen'] = {
        join('bin', *split(target.name)):
        join(workspace_dir, *split(target.name))
    }

    # # Copy binary artifacts to external destination
    # if target.props.copy_bin_to:
    #     link_artifacts([join(workspace_dir, target.props.binary)],
    #                    target.props.copy_bin_to,
    #                    workspace_dir, build_context.conf)


register_builder_sig(
    'CppLib',
    [('sources', PT.FileList),
     ('in_buildenv', PT.Target),
     ('headers', PT.FileList, None),
     ('cmd_env', None),
     ])


@register_manipulate_target_hook('CppLib')
def cpp_lib_manipulate_target(build_context, target):
    target.buildenv = target.props.in_buildenv


@register_build_func('CppLib')
def cpp_lib_builder(build_context, target):
    """Build C++ object files"""
    yprint(build_context.conf, 'Build CppLib', target)
    workspace_dir = build_context.get_workspace('CppLib', target.name)
    link_artifacts(target.props.sources + target.props.headers,
                   workspace_dir, None, build_context.conf)
    buildenv_workspace = build_context.conf.host_to_buildenv_path(
        workspace_dir)
    target.props.objects = compile_cc(
        build_context, target.props.in_buildenv, target.props.sources,
        workspace_dir, buildenv_workspace, target.props.cmd_env)
