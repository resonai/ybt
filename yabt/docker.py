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
from ostrich.utils.proc import run, PIPE, CalledProcessError
from ostrich.utils.text import get_safe_path
from ostrich.utils.collections import listify

from .config import Config
from .logging import make_logger
from .builders.apt import format_package_specifier
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


def get_image_name(target):
    return (target.props.image_name if target.props.image_name
            else target_utils.split_name(target.name))


def get_remote_image_name(name: str, tag: str, image_caching_behavior: dict):
    remote_image_name = image_caching_behavior.get('remote_image_name', name)
    remote_image_tag = image_caching_behavior.get('remote_image_tag', tag)
    return '{}:{}'.format(remote_image_name, remote_image_tag)


def format_qualified_image_name(target):
    if target.builder_name == 'ExtDockerImage':
        if target.props.tag:
            return '{}:{}'.format(target.props.image, target.props.tag)
        return target.props.image
    elif target.builder_name == 'DockerImage':
        return '{}:{}'.format(get_image_name(target), target.props.image_tag)
    else:
        raise TypeError(target)


def get_cached_image_id(qualified_image_name):
    docker_cmd = ['docker', 'images', '-q', qualified_image_name]
    result = run(docker_cmd, stdout=PIPE)
    if result.stdout:
        return result.stdout.decode('utf8').strip()
    return None


def pull_docker_image(qualified_image_name):
    docker_pull_cmd = ['docker', 'pull', qualified_image_name]
    logger.debug('Pulling Docker image {} using command {}',
                 qualified_image_name, docker_pull_cmd)
    run(docker_pull_cmd, check=True)


def push_docker_image(qualified_image_name):
    docker_push_cmd = ['docker', 'push', qualified_image_name]
    logger.debug('Pushing Docker image {} using command {}',
                 qualified_image_name, docker_push_cmd)
    run(docker_push_cmd, check=True)


def tag_docker_image(src_image, tag_as_image):
    if src_image == tag_as_image:
        logger.debug('Skipping Docker tag for identical src and dest {}',
                     src_image)
        return
    docker_tag_cmd = ['docker', 'tag', src_image, tag_as_image]
    logger.debug('Tagging Docker image {} as {} using command {}',
                 src_image, tag_as_image, docker_tag_cmd)
    run(docker_tag_cmd, check=True)


def handle_build_cache(name: str, tag: str, image_caching_behavior: dict):
    """Handle Docker image build cache.

    Return True if image is cached, and there's no need to redo the build.
    Return False if need to build the image (whether cahced locally or not).
    Raise RuntimeError if not allowed to build the image because of state of
    local cache.

    TODO(itamar): figure out a better name for this function, that reflects
    the fact that it returns a boolean value (e.g. `should_build` or
    `is_cached`), without "surprising" the caller with the potential of long
    and non-trivial operations that are not usually expected from functions
    with such names.
    """
    local_image = '{}:{}'.format(name, tag)
    remote_image = get_remote_image_name(name, tag, image_caching_behavior)
    pull_if_not_cached = image_caching_behavior.get(
        'pull_if_not_cached', False)
    pull_if_cached = image_caching_behavior.get(
        'pull_if_cached', False)
    allow_build_if_not_cached = image_caching_behavior.get(
        'allow_build_if_not_cached', True)
    skip_build_if_cached = image_caching_behavior.get(
        'skip_build_if_cached', False)
    if pull_if_cached or (pull_if_not_cached and
                          get_cached_image_id(remote_image) is None):
        try:
            pull_docker_image(remote_image)
        except CalledProcessError:
            pass
    local_image = '{}:{}'.format(name, tag)
    if skip_build_if_cached and get_cached_image_id(remote_image) is not None:
        tag_docker_image(remote_image, local_image)
        return True
    if ((not allow_build_if_not_cached) and
            get_cached_image_id(remote_image) is None):
        raise RuntimeError('No cached image for {}'.format(local_image))
    return False


def build_docker_image(
        build_context, name: str, tag: str, base_image, deps: list=None,
        env: dict=None, work_dir: str=None, truncate_common_parent: str=None,
        cmd: list=None, image_caching_behavior: dict=None,
        no_artifacts: bool=False):
    docker_image = '{}:{}'.format(name, tag)
    if image_caching_behavior is None:
        image_caching_behavior = {}
    if handle_build_cache(name, tag, image_caching_behavior):
        print('Skipping build of cached Docker image', docker_image)
        return
    # create directory for this target under a private builder workspace
    workspace_dir = build_context.get_workspace('DockerBuilder', docker_image)
    # generate Dockerfile and build it
    dockerfile_path = join(workspace_dir, 'Dockerfile')
    dockerfile = [
        'FROM {}\n'.format(format_qualified_image_name(base_image)),
        'ARG DEBIAN_FRONTEND=noninteractive\n',
    ]
    all_artifacts = defaultdict(set)
    apt_keys = set()
    apt_repositories = set()
    apt_packages = list()
    pip_requirements = list()
    custom_installers = list()

    if deps is None:
        deps = []
    # Get all base image deps, so when building this image we can skip adding
    # deps that already exist in the base image.
    base_image_deps = set(dep.name for dep in
                          build_context.walk_target_graph([base_image.name]))
    for dep in deps:
        if dep.name in base_image_deps:
            logger.debug('Skipping base image dep {}', dep.name)
            continue
        if not no_artifacts:
            for kind, artifacts in dep.artifacts.items():
                all_artifacts[kind].update(artifacts)
        if 'apt-installable' in dep.tags:
            apt_packages.append(format_package_specifier(dep))
            if dep.props.repository:
                apt_repositories.add(dep.props.repository)
            if dep.props.repo_key:
                apt_keys.add((dep.props.repo_key, dep.props.repo_keyserver))
        if 'pip-installable' in dep.tags:
            pip_requirements.append(format_req_specifier(dep))
        if 'custom-installer' in dep.tags:
            custom_installers.append(dep.props.installer_desc)

    # Handle apt keys, repositories, and packages (one layer for all)
    apt_cmd = ''
    if apt_keys:
        apt_cmd += ' && '.join(
            'apt-key adv --keyserver {} --recv {}'.format(keyserver, repo_key)
            for repo_key, keyserver in sorted(apt_keys)) + ' && '
    if apt_repositories:
        apt_cmd += (
            # TODO(itamar): I'm assuming software-properties-common exists in
            # the base image, because it's much faster this way, but need a
            # better solution for when it's not true...
            # 'apt-get update -y && apt-get install -y '
            # 'software-properties-common --no-install-recommends && ' +
            ' && '.join('add-apt-repository -y "{}"'.format(repo)
                        for repo in sorted(apt_repositories))) + ' && '
    if apt_packages:
        apt_cmd += (
            'apt-get update -y && apt-get install -y {} '
            '--no-install-recommends'.format(' '.join(sorted(apt_packages))))
        if False:
            apt_cmd += ' && rm -rf /var/lib/apt/lists/*'
    if apt_cmd:
        dockerfile.append('RUN {}\n'.format(apt_cmd))

    # Handle custom installers (2 layers)
    if custom_installers:
        workspace_packages_dir = join(workspace_dir, 'packages')
        try:
            shutil.rmtree(workspace_packages_dir)
        except FileNotFoundError:
            pass
        os.makedirs(workspace_packages_dir)
        run_installers = []
        for custom_installer in custom_installers:
            package_tar = basename(custom_installer.package)
            os.link(custom_installer.package,
                    join(workspace_packages_dir, package_tar))
            run_installers.extend([
                'tar -xf /tmp/install/{} -C /tmp/install'.format(package_tar),
                'cd /tmp/install/{}'.format(custom_installer.name),
                './{}'.format(custom_installer.install_script),
            ])
        dockerfile.extend([
            'COPY packages /tmp/install\n',
            'RUN {} && cd / && rm -rf /tmp/install\n'.format(
                ' && '.join(run_installers)),
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
                         for key, value in sorted(env.items()))))

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
    run(docker_build_cmd, check=True)
    if image_caching_behavior.get('push_image_after_build', False):
        remote_image = get_remote_image_name(name, tag, image_caching_behavior)
        tag_docker_image(docker_image, remote_image)
        push_docker_image(remote_image)


def base_image_caching_behavior(conf: Config, **kwargs):
    base_dict = {
        'skip_build_if_cached': not conf.build_base_images,
        'pull_if_not_cached': not conf.offline,
        'pull_if_cached': conf.force_pull and not conf.offline,
        'fail_build_if_pull_failed': not conf.offline,
        'allow_build_if_not_cached': conf.build_base_images,
        'push_image_after_build': conf.push and not conf.offline,
    }
    base_dict.update(kwargs)
    return base_dict


def deployable_caching_behavior(conf: Config, **kwargs):
    base_dict = {
        'push_image_after_build': conf.push and not conf.offline,
    }
    base_dict.update(kwargs)
    return base_dict
