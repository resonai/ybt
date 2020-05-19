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

from os import listdir, remove
from os.path import isfile, join, relpath

from ..artifact import ArtifactType as AT
from .dockerapp import build_app_docker_and_bin, register_app_builder_sig
from ..extend import (
    PropType as PT, register_build_func, register_builder_sig,
    register_manipulate_target_hook)
from ..logging import make_logger
from ..target_utils import split
from ..utils import rmtree, yprint, link_files, link_node


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


register_builder_sig(
    'GoProg',
    [('sources', PT.FileList),
     ('in_buildenv', PT.Target),
     ('cmd_env', None),
     ])


@register_manipulate_target_hook('GoProg')
def go_prog_manipulate_target(build_context, target):
    target.buildenv = target.props.in_buildenv

def rm_all_but_go_mod(workspace_dir):
  for fname in listdir(workspace_dir):
    if fname == 'go.mod':
      continue
    filepath = join(workspace_dir, fname)
    if isfile(filepath):
      remove(filepath)
    else:
      rmtree(filepath)

@register_build_func('GoProg')
def go_prog_builder(build_context, target):
    """Build a Go binary executable"""
    yprint(build_context.conf, 'Build GoProg', target)
    workspace_dir = build_context.get_workspace('GoProg', target.name)

    # we leave the go.mod file otherwise the caching of downloaded packages
    # doesn't work
    rm_all_but_go_mod(workspace_dir)
    binary = join(*split(target.name))

    buildenv_workspace = build_context.conf.host_to_buildenv_path(
        workspace_dir)
    buildenv_sources = [join(buildenv_workspace, src)
                        for src in target.props.sources]

    link_files(target.props.sources, workspace_dir, None, build_context.conf)
    has_protos = False
    for dep in build_context.generate_all_deps(target):
      artifact_map = dep.artifacts.get(AT.gen_go)
      if not artifact_map:
        continue
      has_protos = True
      for dst, src in artifact_map.items():
        target_file = join(workspace_dir, dst)
        link_node(join(build_context.conf.project_root, src), target_file)


    download_cache_dir = build_context.conf.host_to_buildenv_path(
      join(build_context.conf.get_root_workspace_path(), 'go'))
    build_cmd_env = {
      'CGO_ENABLED': 0,
      #'XDG_CACHE_HOME': '%s/.cache' % download_cache_dir,
      'GOPATH': '%s:/go' % download_cache_dir,  # TODO now /go
    }
    build_cmd_env.update(target.props.cmd_env or {})


    if not isfile(join(workspace_dir, 'go.mod')):
      build_context.run_in_buildenv(
        target.props.in_buildenv,
        ['go', 'mod', 'init', 'resonai.com'],  # TODO now - take from config or go generic..
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
          ['go', 'mod', 'init', 'resonai.com'],  # TODO now - take from config or go generic..
          build_cmd_env,
          work_dir=join(buildenv_workspace, 'proto'))

    bin_file = join(buildenv_workspace, binary)
    build_cmd = ['go', 'build', '-o', bin_file] + buildenv_sources
    build_context.run_in_buildenv(
      target.props.in_buildenv, build_cmd, build_cmd_env,
      work_dir=buildenv_workspace)
    target.artifacts.add(
        AT.binary,
        relpath(join(workspace_dir, binary), build_context.conf.project_root),
        binary)
