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
yabt Docker Builder
~~~~~~~~~~~~~~~~~~~

:author: Itamar Ostricher
"""


import os
from os.path import join, split, isdir, isfile, samefile
import subprocess

from ostrich.utils.collections import listify

from ..extend import (
    PropType as PT, register_build_func, register_builder_sig,
    register_manipulate_target_hook)
from ..logging import make_logger
from .. import target_utils


logger = make_logger(__name__)


register_builder_sig(
    'ExtDockerImage', [('image', PT.str), ('tag', PT.str, None)])


@register_build_func('ExtDockerImage')
def ext_docker_image_builder(build_context, target):
    print('Fetch and cache Docker image from registry', target)


register_builder_sig(
    'DockerImage',
    [('start_from', PT.Target),
     ('deps', PT.TargetList, None),
     ('docker_cmd', PT.StrList, None),
     ])


@register_manipulate_target_hook('DockerImage')
def docker_image_manipulate_target(build_context, target):
    build_module = target_utils.split_build_module(target.name)
    norm_start_from = target_utils.norm_name(build_module,
                                             target.props.start_from)
    target.props.start_from = norm_start_from
    logger.debug('Injecting "{}" to deps of {}', norm_start_from, target)
    target.deps.append(norm_start_from)


def make_pip_requirements(pip_requirements, pip_req_file_path):
    if pip_requirements:
        # TODO(itamar): compare `pip_requirements` with those in the
        # existing file, and don't rewrite if it's the same - it appears
        # to be triggering rebuilds even if rewriting identical content!
        with open(pip_req_file_path, 'w') as pip_req_file:
            pip_req_file.write('\n'.join(pip_requirements) + '\n')
        return True
    elif isfile(pip_req_file_path):
        # delete remnant requirements file
        os.remove(pip_req_file_path)
        return False


def sync_copy_sources(copy_sources, workspace_src_dir, conf):
    num_copied = 0
    for src in copy_sources:
        abs_src = join(conf.project_root, src)
        abs_dest = join(workspace_src_dir, src)
        if isfile(abs_dest):
            if not samefile(abs_src, abs_dest):
                print('existing {} in workspace not identical to source - '
                      'replacing'.format(src))
                os.remove(abs_dest)
                os.link(abs_src, abs_dest)
        else:
            dest_parent_dir = split(abs_dest)[0]
            if not isdir(dest_parent_dir):
                # exist_ok=True in case of concurrent creation of the same
                # parent dir
                os.makedirs(dest_parent_dir, exist_ok=True)
            os.link(abs_src, abs_dest)
        num_copied += 1
    return num_copied


@register_build_func('DockerImage')
def docker_image_builder(build_context, target):
    # create directory for this target under a private builder workspace
    workspace_dir = build_context.get_workspace('DockerBuilder', target.name)
    # generate Dockerfile and build it
    dockerfile_path = join(workspace_dir, 'Dockerfile')
    # start_from name should be normalized by the extraction hook
    start_from = build_context.targets[target.props.start_from]
    if start_from.props.tag:
        dockerfile = ['FROM {}:{}\n'.format(
            start_from.props.image, start_from.props.tag)]
    else:
        dockerfile = ['FROM {}\n'.format(start_from.props.image)]
    copy_sources = []
    pip_requirements = []
    for dep_target in build_context.walk_target_graph(target.deps[:-1]):
        print(dep_target)
        if 'pip-installable' in dep_target.tags:
            if dep_target.props.version:
                pip_req = '{0.package}=={0.version}'.format(dep_target.props)
            else:
                pip_req = '{0.package}'.format(dep_target.props)
            pip_requirements.append(pip_req)
        if 'sources' in dep_target.props:
            copy_sources.extend(dep_target.props.sources)
    pip_req_file = join(workspace_dir, 'requirements.txt')
    if make_pip_requirements(pip_requirements, pip_req_file):
        dockerfile.extend([
            'COPY requirements.txt /usr/src/\n',
            'RUN pip install --no-cache-dir -r /usr/src/requirements.txt\n'
        ])
    workspace_src_dir = join(workspace_dir, 'src')
    # sync `sources` files between project and `workspace_src_dir`
    if sync_copy_sources(copy_sources, workspace_src_dir,
                         build_context.conf) > 0:
        dockerfile.extend([
            'RUN mkdir -p /usr/src/app\n',
            'WORKDIR /usr/src/app\n',
            'COPY src /usr/src/app\n',
        ])
    # TODO(itamar): also remove files that shouldn't be there!

    def format_docker_cmd(docker_cmd):
        return ('"{}"'.format(cmd) for cmd in docker_cmd)

    if target.props.docker_cmd:
        dockerfile.append(
            'CMD [{}]\n'.format(
                ', '.join(format_docker_cmd(target.props.docker_cmd))))
    # TODO(itamar): write only if changed?
    with open(dockerfile_path, 'w') as dockerfile_f:
        dockerfile_f.writelines(dockerfile)
    # TODO(itamar): how to determine tag? (between "latest" / git hash /
    # from flag / other)
    docker_image = '{}:bar'.format(target_utils.split_name(target.name))
    docker_build_cmd = [
        'docker', 'build', '-t', docker_image, workspace_dir]
    logger.info('Building docker image "{}" from target "{}" using command {}',
                docker_image, target.name, docker_build_cmd)
    subprocess.run(docker_build_cmd)
