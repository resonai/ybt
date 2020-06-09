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

TODO: libs, external libs
TODO: does this even work with non-flat source file tree??
"""
from ..config import YSETTINGS_FILE
from os import listdir, remove
from os.path import isfile, join, relpath

from yabt.docker import extend_runtime_params, format_docker_run_params
from ..artifact import ArtifactType as AT
from .dockerapp import build_app_docker_and_bin, register_app_builder_sig
from ..extend import (
    PropType as PT, register_build_func, register_builder_sig,
    register_manipulate_target_hook)
from ..logging import make_logger
from ..target_utils import split
from ..utils import link_files, link_node, rmtree, yprint

logger = make_logger(__name__)


register_app_builder_sig('GoApp', [('main', PT.Target)])


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
    prog = build_context.targets[target.props.main]
    binary = list(prog.artifacts.get(AT.binary).keys())[0]
    entrypoint = ['/usr/src/bin/' + binary]
    build_app_docker_and_bin(
        build_context, target, entrypoint=entrypoint)


# Common Go builder signature terms
GO_SIG = [
    ('sources', PT.FileList),
    ('in_buildenv', PT.Target),
    ('go_package', PT.str, None),
    ('mod_file', PT.File, None),
    ('cmd_env', None),
]

register_builder_sig('GoProg', GO_SIG)


@register_manipulate_target_hook('GoProg')
def go_prog_manipulate_target(build_context, target):
    target.buildenv = target.props.in_buildenv


@register_build_func('GoProg')
def go_prog_builder(build_context, target):
    """Build a Go binary executable"""
    go_builder_internal(build_context, target, command='build')


register_builder_sig('GoTest', GO_SIG)


@register_manipulate_target_hook('GoTest')
def go_test_manipulate_target(build_context, target):
    target.tags.add('testable')
    target.buildenv = target.props.in_buildenv


@register_build_func('GoTest')
def go_test_builder(build_context, target):
    """Test a Go test"""
    go_builder_internal(build_context, target, command='test')


def rm_all_but_go_mod(workspace_dir):
    for fname in listdir(workspace_dir):
        if fname == 'go.mod':
            continue
        filepath = join(workspace_dir, fname)
        if isfile(filepath):
            remove(filepath)
        else:
            rmtree(filepath)


def go_builder_internal(build_context, target, command):
    """Build or test a Go binary executable.
    command is either build or test

    We link all go files source and all proto generated files into workspace.
    We generate a go.mod file in the workspace to make it the root of the
    go project.
    We create a go.mod file in proto dir with the same package name and add
    a "replace proto => ./proto" directive in the go.mod.
    We set the first dir in GOPATH to be yabtwork/go so that all downloaded
    packages are managed in the user machine and not inside the ephemeral
    docker.
    When we clean the workspace we make sure to keep the go.mod since it is new
    go build redownload all packages (can we solve this?)


    TODOs:
      - "replace proto => ./proto" is needed since the generated code import
        doesn't have the package before imports of other generated go files.
        See if there is another way to do it (understanding that can help us
        create a GoLib builder)
    """
    builder_name = target.builder_name
    yprint(build_context.conf, command, builder_name, target)
    workspace_dir = build_context.get_workspace(builder_name, target.name)
    go_package = (target.props.get('go_package') or
                  build_context.conf.get('go_package', None))
    go_mod_path = join(workspace_dir, 'go.mod')
    if not go_package:
        raise KeyError('Must specify go_package in {} common_conf '
                       'or on target'.format(YSETTINGS_FILE))

    # we leave the go.mod file otherwise the caching of downloaded packages
    # doesn't work
    rm_all_but_go_mod(workspace_dir)
    binary = join(*split(target.name))

    buildenv_workspace = build_context.conf.host_to_buildenv_path(
        workspace_dir)
    buildenv_sources = [join(buildenv_workspace, src)
                        for src in target.props.sources]
    if target.props.get('mod_file'):
        link_node(join(build_context.conf.project_root,
                       target.props.get('mod_file')),
                  go_mod_path)
    sources_to_link = list(target.props.sources)
    has_protos = False

    # Goging over all deps and pulling their sources.
    # TODO(eyal): This pull sources of all types which is most likely not
    # needed but not harming. We should revisit this in later iterations.
    for dep in build_context.generate_all_deps(target):
        sources_to_link.extend(dep.props.get('sources', []))
        artifact_map = dep.artifacts.get(AT.gen_go)
        if not artifact_map:
            continue
        has_protos = True
        for dst, src in artifact_map.items():
            target_file = join(workspace_dir, dst)
            link_node(join(build_context.conf.project_root, src), target_file)

    link_files(sources_to_link, workspace_dir, None, build_context.conf)

    download_cache_dir = build_context.conf.host_to_buildenv_path(
      build_context.conf.get_go_packages_path())

    gopaths = [download_cache_dir]
    user_gopath = (target.props.cmd_env or {}).get('GOPATH')
    # if user didn't provide GOPATH we assumes it is /go
    # TODO(eyal): A more correct behavior will be to check the GOPATH var
    # inside the docker then to assumes it is /go.
    # This code provides a way for the user to tell us what is the correct
    # GOPATH but if it come handy we should implement looking into the docker
    gopaths.append(user_gopath if user_gopath else '/go')
    build_cmd_env = {
        'XDG_CACHE_HOME': '/tmp/.cache',
    }
    build_cmd_env.update(target.props.cmd_env or {})
    build_cmd_env['GOPATH'] = ':'.join(gopaths)

    if not isfile(go_mod_path):
        build_context.run_in_buildenv(
          target.props.in_buildenv,
          ['go', 'mod', 'init', go_package],
          build_cmd_env,
          work_dir=buildenv_workspace)
    if has_protos:
        build_context.run_in_buildenv(
          target.props.in_buildenv,
          ['go', 'mod', 'edit', '-replace', 'proto=./proto'],
          build_cmd_env,
          work_dir=buildenv_workspace)
        if not isfile(join(workspace_dir, 'proto', 'go.mod')):
            build_context.run_in_buildenv(
              target.props.in_buildenv,
              ['go', 'mod', 'init', go_package],
              build_cmd_env,
              work_dir=join(buildenv_workspace, 'proto'))

    bin_file = join(buildenv_workspace, binary)
    build_cmd = ['go', command, '-o', bin_file] + buildenv_sources

    run_params = extend_runtime_params(
        target.props.runtime_params,
        build_context.walk_target_deps_topological_order(target),
        build_context.conf.runtime_params, True)

    build_context.run_in_buildenv(
      target.props.in_buildenv, build_cmd, build_cmd_env,
      run_params=format_docker_run_params(run_params),
      work_dir=buildenv_workspace)
    target.artifacts.add(
        AT.binary,
        relpath(join(workspace_dir, binary), build_context.conf.project_root),
        binary)
