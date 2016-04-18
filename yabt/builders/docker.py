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
from os.path import commonpath, isdir, isfile, join, relpath, samefile, split
import shutil
import subprocess

from ostrich.utils.collections import listify

from ..extend import (
    PropType as PT, register_build_func, register_builder_sig,
    register_manipulate_target_hook)
from ..logging import make_logger
from .python import format_req_specifier
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
     ('image_name', PT.str, None),
     ('image_tag', PT.str, 'latest'),
     ('always_keep_parent_dirs_in_image', PT.bool, False)
     ])


@register_manipulate_target_hook('DockerImage')
def docker_image_manipulate_target(build_context, target):
    logger.debug('Injecting "{}" to deps of {}',
                 target.props.start_from, target)
    target.deps.append(target.props.start_from)


def make_pip_requirements(pip_requirements, pip_req_file_path):
    if pip_requirements:
        try:
            with open(pip_req_file_path, 'r') as pip_req_file:
                if (set(line.strip() for line in pip_req_file) ==
                        set(pip_requirements)):
                    # no change in requirements file - don't rewrite it
                    # (it appears that rewriting may trigger spurious rebuilds)
                    logger.debug(
                        'Short circuiting requirements file generation')
                    return True
        except FileNotFoundError:
            pass
        with open(pip_req_file_path, 'w') as pip_req_file:
            pip_req_file.write('\n'.join(sorted(pip_requirements)) + '\n')
        return True
    elif isfile(pip_req_file_path):
        # delete remnant requirements file
        os.remove(pip_req_file_path)
        return False


def sync_copy_sources(copy_sources, workspace_src_dir, common_parent, conf):
    # start with removing the workspace src dir, to avoid any spurious and
    # leftover files in there - I think this is better than walking it and
    # looking for files to remove - doesn't seem this would scale well
    try:
        shutil.rmtree(workspace_src_dir)
    except FileNotFoundError:
        pass
    common_dir = commonpath(copy_sources + [common_parent])
    num_linked = 0
    for src in copy_sources:
        abs_src = join(conf.project_root, src)
        abs_dest = join(workspace_src_dir, relpath(src, common_dir))
        if isfile(abs_src):
            # sync file by linking it to dest
            dest_parent_dir = split(abs_dest)[0]
            if not isdir(dest_parent_dir):
                # exist_ok=True in case of concurrent creation of the same
                # parent dir
                os.makedirs(dest_parent_dir, exist_ok=True)
            os.link(abs_src, abs_dest)
        elif isdir(abs_src):
            # sync dir by recursively linking files under it to dest
            shutil.copytree(abs_src, abs_dest, copy_function=os.link)
        else:
            raise FileNotFoundError(abs_src)
        num_linked += 1
    return num_linked


@register_build_func('DockerImage')
def docker_image_builder(build_context, target):
    # create directory for this target under a private builder workspace
    workspace_dir = build_context.get_workspace('DockerBuilder', target.name)
    # generate Dockerfile and build it
    dockerfile_path = join(workspace_dir, 'Dockerfile')
    start_from = build_context.targets[target.props.start_from]
    if start_from.props.tag:
        dockerfile = ['FROM {}:{}\n'.format(
            start_from.props.image, start_from.props.tag)]
    else:
        dockerfile = ['FROM {}\n'.format(start_from.props.image)]
    copy_sources = []
    pip_requirements = []
    for dep_target in build_context.walk_target_graph(target.deps[:-1]):
        if 'pip-installable' in dep_target.tags:
            pip_requirements.append(format_req_specifier(dep_target))
        if 'sources' in dep_target.props:
            copy_sources.extend(dep_target.props.sources)
        if 'data' in dep_target.props:
            copy_sources.extend(dep_target.props.data)
    pip_req_file = join(workspace_dir, 'requirements.txt')
    if make_pip_requirements(pip_requirements, pip_req_file):
        dockerfile.extend([
            'COPY requirements.txt /usr/src/\n',
            'RUN pip install --no-cache-dir --upgrade pip && \\\n'
            '    pip install --no-cache-dir -r /usr/src/requirements.txt\n'
        ])
    workspace_src_dir = join(workspace_dir, 'src')
    # sync `sources` files between project and `workspace_src_dir`
    if sync_copy_sources(copy_sources, workspace_src_dir,
                         '' if target.props.always_keep_parent_dirs_in_image
                         else target_utils.split_build_module(target.name),
                         build_context.conf) > 0:
        dockerfile.extend([
            'RUN mkdir -p /usr/src/app\n',
            'WORKDIR /usr/src/app\n',
            'COPY src /usr/src/app\n',
        ])

    def format_docker_cmd(docker_cmd):
        return ('"{}"'.format(cmd) for cmd in docker_cmd)

    if target.props.docker_cmd:
        dockerfile.append(
            'CMD [{}]\n'.format(
                ', '.join(format_docker_cmd(target.props.docker_cmd))))
    # TODO(itamar): write only if changed?
    with open(dockerfile_path, 'w') as dockerfile_f:
        dockerfile_f.writelines(dockerfile)
    docker_image = '{}:{}'.format(
        target.props.image_name if target.props.image_name
        else target_utils.split_name(target.name),
        target.props.image_tag)
    docker_build_cmd = [
        'docker', 'build', '-t', docker_image, workspace_dir]
    logger.info('Building docker image "{}" from target "{}" using command {}',
                docker_image, target.name, docker_build_cmd)
    subprocess.run(docker_build_cmd)
