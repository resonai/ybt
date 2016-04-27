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
yabt Docker module
~~~~~~~~~~~~~~~~~~

NOT to be confused with the Docker builder...

:author: Itamar Ostricher
"""


from collections import defaultdict
import os
from os.path import (
    basename, isdir, isfile, join, normpath, relpath, samefile, split)
import shutil

from ostrich.utils.path import commonpath
from ostrich.utils.proc import run
from ostrich.utils.text import get_safe_path
from ostrich.utils.collections import listify

from .config import Config
from .logging import make_logger
from .builders.python import format_req_specifier
from . import target_utils


logger = make_logger(__name__)


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


def link_artifacts(artifacts: set, workspace_src_dir: str,
                   common_parent: str, conf: Config):
    """Sync the list of files and directories in `artifacts` to destination
       directory specified by `workspace_src_dir`.

    "Sync" in the sense that every file given in `artifacts` will be
    hard-linked under `workspace_src_dir` after this function returns, and no
    other files will exist under `workspace_src_dir`.

    For directories in `artifacts`, hard-links of contained files are
    created recursively.

    All paths in `artifacts`, and the `workspace_src_dir`, must be relative
    to `conf.project_root`.

    If `workspace_src_dir` exists before calling this function, it is removed
    before syncing.

    If `common_parent` is given, and it is a common parent directory of all
    `artifacts`, then the `commonm_parent` part is truncated from the
    sync'ed files destination path under `workspace_src_dir`.

    :raises FileNotFoundError: If `artifacts` contains files or directories
                               that do not exist.

    :raises ValueError: If `common_parent` is given (not `None`), but is *NOT*
                        a common parent of all `artifacts`.
    """
    try:
        shutil.rmtree(workspace_src_dir)
    except FileNotFoundError:
        pass
    if common_parent:
        common_parent = normpath(common_parent)
        base_dir = commonpath(list(artifacts) + [common_parent])
        if base_dir != common_parent:
            raise ValueError('{} is not the common parent of all target '
                             'sources and data'.format(common_parent))
        logger.debug('Rebasing files in image relative to common parent dir {}'
                     .format(base_dir))
    else:
        base_dir = ''
    num_linked = 0
    for src in artifacts:
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


def build_docker_image(
        build_context, name: str, tag: str, base_image: str, deps: list=None,
        env: dict=None, work_dir: str=None, truncate_common_parent: str=None,
        cmd: list=None, no_artifacts: bool=False):
    # create directory for this target under a private builder workspace
    docker_image = '{}:{}'.format(name, tag)
    workspace_dir = build_context.get_workspace('DockerBuilder', docker_image)
    # generate Dockerfile and build it
    dockerfile_path = join(workspace_dir, 'Dockerfile')
    dockerfile = ['FROM {}\n'.format(base_image)]
    all_artifacts = defaultdict(set)
    apt_packages = list()
    pip_requirements = list()
    custom_install_scripts = list()
    custom_packages = set()

    if deps is None:
        deps = []
    for dep in deps:
        if not no_artifacts:
            for kind, artifacts in dep.artifacts.items():
                all_artifacts[kind].update(artifacts)
        if 'apt-installable' in dep.tags:
            apt_packages.append(dep.props.package)
        if 'pip-installable' in dep.tags:
            pip_requirements.append(format_req_specifier(dep))
        if 'custom-installer' in dep.tags:
            custom_packages.add(dep.props.workspace)
            custom_install_scripts.append(dep.props.rel_dir_script)

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
    if link_artifacts(custom_packages, workspace_packages_dir,
                      build_context.get_workspace('CustomInstaller'),
                      build_context.conf) > 0:
        dockerfile.extend([
            'COPY packages /tmp/install\n',
            'RUN {}\n'.format(
                ' && '.join(
                    'cd /tmp/install/{} && ./{}'
                    .format(package_dir, script_name)
                    for package_dir, script_name in custom_install_scripts))
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
    if env:
        dockerfile.append(
            'ENV {}\n'.format(
                ' '.join('{}="{}"'.format(key, value)
                         for key, value in env.items())))

    if work_dir:
        dockerfile.append('WORKDIR {}\n'.format(work_dir))

    if not no_artifacts:
        # Handle copying data to the image
        # start with removing the workspace src dir, to avoid any spurious and
        # leftover files in there - I think this is better than walking it and
        # looking for files to remove - doesn't seem this would scale well
        workspace_src_dir = join(workspace_dir, 'src')
        try:
            shutil.rmtree(workspace_src_dir)
        except FileNotFoundError:
            pass
        # sync artifacts between project and `workspace_src_dir`
        num_linked = 0
        for kind, artifacts in all_artifacts.items():
            num_linked += link_artifacts(
                artifacts, join(workspace_src_dir, kind),
                truncate_common_parent, build_context.conf)
        if num_linked > 0:
            dockerfile.append('COPY src /usr/src\n')

    # Add CMD (one layer)
    def format_docker_cmd(docker_cmd):
        return ('"{}"'.format(cmd) for cmd in docker_cmd)

    if cmd:
        dockerfile.append(
            'CMD [{}]\n'.format(', '.join(format_docker_cmd(cmd))))

    # TODO(itamar): write only if changed?
    with open(dockerfile_path, 'w') as dockerfile_f:
        dockerfile_f.writelines(dockerfile)
    docker_build_cmd = [
        'docker', 'build', '-t', docker_image, workspace_dir]
    logger.info('Building docker image "{}" using command {}',
                docker_image, docker_build_cmd)
    run(docker_build_cmd)
