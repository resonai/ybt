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
from os.path import (
    basename, commonpath, isdir, isfile, join,
    normpath, relpath, samefile, split)
import shutil
import subprocess

from ostrich.utils.text import get_safe_path
from ostrich.utils.collections import listify

from ..config import Config
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
     ('work_dir', PT.str, '/usr/src/app'),
     ('env', None),
     ('truncate_common_parent', PT.str, None)
     ])


@register_manipulate_target_hook('DockerImage')
def docker_image_manipulate_target(build_context, target):
    logger.debug('Injecting "{}" to deps of {}',
                 target.props.start_from, target)
    target.deps.append(target.props.start_from)


def make_pip_requirements(pip_requirements: set, pip_req_file_path: str):
    if pip_requirements:
        try:
            with open(pip_req_file_path, 'r') as pip_req_file:
                if (set(line.strip() for line in pip_req_file) ==
                        pip_requirements):
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


def sync_copy_sources(copy_sources: set, workspace_src_dir: str,
                      common_parent: str, conf: Config):
    """Sync the list of files and directories in `copy_sources` to destination
       directory specified by `workspace_src_dir`.

    "Sync" in the sense that every file given in `copy_sources` will be
    hard-linked under `workspace_src_dir` after this function returns, and no
    other files will exist under `workspace_src_dir`.

    For directories in `copy_sources`, hard-links of contained files are
    created recursively.

    All paths in `copy_sources`, and the `workspace_src_dir`, must be relative
    to `conf.project_root`.

    If `workspace_src_dir` exists before calling this function, it is removed
    before syncing.

    If `common_parent` is given, and it is a common parent directory of all
    `copy_sources`, then the `commonm_parent` part is trauncated from the
    sync'ed files destination path under `workspace_src_dir`.

    :raises FileNotFoundError: If `copy_sources` contains files or directories
                               that do not exist.

    :raises ValueError: If `common_parent` is given (not `None`), but is *NOT*
                        a common parent of all `copy_sources`.
    """
    # start with removing the workspace src dir, to avoid any spurious and
    # leftover files in there - I think this is better than walking it and
    # looking for files to remove - doesn't seem this would scale well
    try:
        shutil.rmtree(workspace_src_dir)
    except FileNotFoundError:
        pass
    if common_parent:
        common_parent = normpath(common_parent)
        base_dir = commonpath(list(copy_sources) + [common_parent])
        if base_dir != common_parent:
            raise ValueError('{} is not the common parent of all target '
                             'sources and data'.format(common_parent))
        logger.debug('Rebasing files in image relative to common parent dir {}'
                     .format(base_dir))
    else:
        base_dir = ''
    num_linked = 0
    for src in copy_sources:
        abs_src = join(conf.project_root, src)
        abs_dest = join(workspace_src_dir, relpath(src, base_dir))
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
            shutil.copytree(abs_src, abs_dest,
                            copy_function=os.link,
                            ignore=shutil.ignore_patterns('.git'))
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
    copy_sources = set()
    apt_packages = set()
    pip_requirements = set()
    custom_installers = list()
    custom_packages = set()
    for dep_target in build_context.walk_target_deps_topological_order(target):
        print(dep_target.name)
        if 'apt-installable' in dep_target.tags:
            apt_packages.add(dep_target.props.package)
        if 'pip-installable' in dep_target.tags:
            pip_requirements.add(format_req_specifier(dep_target))
        if 'custom-installer' in dep_target.tags:
            custom_packages.add(dep_target.props.workspace)
            custom_installers.append(dep_target.props.rel_dir_script)
        if 'sources' in dep_target.props:
            copy_sources.update(dep_target.props.sources)
        if 'data' in dep_target.props:
            copy_sources.update(dep_target.props.data)
    # Handle apt packages (one layer)
    if apt_packages:
        apt_get_cmd = (
            'RUN apt-get update && apt-get install -y {} '
            '--no-install-recommends'.format(' '.join(sorted(apt_packages))))
        if False:
            apt_get_cmd += ' && rm -rf /var/lib/apt/lists/*'
        dockerfile.append(apt_get_cmd + '\n')
    # Sync custom installer packages
    workspace_packages_dir = join(workspace_dir, 'packages')
    if sync_copy_sources(custom_packages, workspace_packages_dir,
                         build_context.get_workspace('CustomInstaller'),
                         build_context.conf) > 0:
        dockerfile.extend([
            'COPY packages /tmp/install\n',
            'RUN {}\n'.format(
                ' && '.join('cd /tmp/install/{} && ./{}'
                            .format(package_dir, script_name)
                            for package_dir, script_name in custom_installers))
            ])
    # Handle pip packages (2 layers)
    pip_req_file = join(workspace_dir, 'requirements.txt')
    if make_pip_requirements(pip_requirements, pip_req_file):
        dockerfile.extend([
            'COPY requirements.txt /usr/src/\n',
            'RUN pip install --no-cache-dir --upgrade pip && '
            'pip install --no-cache-dir -r /usr/src/requirements.txt\n'
        ])
    # Add environment variables (one layer)
    if target.props.env:
        dockerfile.append(
            'ENV {}\n'.format(
                ' '.join('{}="{}"'.format(key, value)
                         for key, value in target.props.env.items())))
    # Handle copying data to the image
    workspace_src_dir = join(workspace_dir, 'src')
    # sync `sources` files between project and `workspace_src_dir`
    if sync_copy_sources(copy_sources, workspace_src_dir,
                         target.props.truncate_common_parent,
                         build_context.conf) > 0:
        dockerfile.extend([
            'WORKDIR {}\n'.format(target.props.work_dir),
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
