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


from collections import defaultdict, deque
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
from .builders.apt import format_apt_specifier, parse_apt_repository
from .builders.nodejs import format_npm_specifier
from .builders.python import format_pypi_specifier
from .builders.ruby import format_gem_specifier
from . import target_utils
from .utils import yprint


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


def make_apt_sources_list(apt_sources: list, apt_sources_file_path: str):
    if apt_sources:
        try:
            with open(apt_sources_file_path, 'r') as apt_sources_file:
                if (set(line.strip() for line in apt_sources_file) ==
                        set(apt_sources)):
                    # no change in sources file - don't rewrite it
                    logger.debug(
                        'Short circuiting sources list file generation')
                    return True
        except FileNotFoundError:
            pass
        with open(apt_sources_file_path, 'w') as apt_sources_file:
            apt_sources_file.write('\n'.join(sorted(apt_sources)) + '\n')
        return True
    elif isfile(apt_sources_file_path):
        # delete remnant sources list file
        os.remove(apt_sources_file_path)
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
        entrypoint: list=None, cmd: list=None, distro: dict=None,
        image_caching_behavior: dict=None, no_artifacts: bool=False):
    docker_image = '{}:{}'.format(name, tag)
    if image_caching_behavior is None:
        image_caching_behavior = {}
    if handle_build_cache(name, tag, image_caching_behavior):
        yprint(build_context.conf,
               'Skipping build of cached Docker image', docker_image)
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
    apt_repo_deps = []
    effective_env = {}
    env_manipulations = {}
    packaging_layers = []

    def add_package(pkg_type, pkg_spec):
        """Add package specification of certain package type.

        Uses last layer if matches package type, otherwise opens a new layer.

        This can result "Docker layer framgantation", by opening and closing
        many layers.
        No optimization is performed on detecting opportunities to merge layers
        that were split just because of arbitrary topological sort decision
        (tie breaker), and not a real topology in the target graph.
        Such an optimization could be done here by inspecting the graph
        directly, but decided not to go into it at this stage, since it's not
        clear it's beneficial overall (e.g. better to have more layers so
        some of them can remain cached if others change).
        A better optimization (also not implemented) could be to do topological
        sort tie breaking based on Docker-cache optimization - e.g., move new
        things to new layers in order to keep old things in cached layers.
        """
        if len(packaging_layers) == 0:
            layer = (pkg_type, list())
            packaging_layers.append(layer)
        else:
            layer = packaging_layers[-1]
            if pkg_type != layer[0]:
                layer = (pkg_type, list())
                packaging_layers.append(layer)
        layer[1].append(pkg_spec)

    def check_env_overrides(new_vars: set, op_kind: str, vars_source: str):
        overridden_vars = new_vars.intersection(effective_env.keys())
        if overridden_vars:
            raise ValueError(
                'Following env vars {} from {} override previously set vars '
                'during build of Docker image "{}": {}'.format(
                    op_kind, vars_source, docker_image,
                    ', '.join(overridden_vars)))
        if op_kind == 'set':
            overridden_vars = new_vars.intersection(env_manipulations.keys())
            if overridden_vars:
                raise ValueError(
                    'Following env vars {} from {} override previous '
                    'manipulations during build of Docker image "{}": {}'
                    .format(op_kind, vars_source, docker_image,
                            ', '.join(overridden_vars)))

    if deps is None:
        deps = []
    # Get all base image deps, so when building this image we can skip adding
    # deps that already exist in the base image.
    base_image_deps = set(dep.name for dep in
                          build_context.walk_target_graph([base_image.name]))
    for dep in deps:
        if not distro and 'distro' in dep.props:
            distro = dep.props.distro

        if dep.name in base_image_deps:
            logger.debug('Skipping base image dep {}', dep.name)
            continue
        if not no_artifacts:
            for kind, artifacts in dep.artifacts.items():
                all_artifacts[kind].update(artifacts)

        PACKAGING_PARAMS = frozenset(('set_env', 'semicolon_join_env'))
        invalid_keys = set(
            dep.props.packaging_params.keys()).difference(PACKAGING_PARAMS)
        if invalid_keys:
            raise ValueError(
                'Unknown keys in packaging params of target "{}": {}'.format(
                    dep.name, ', '.join(invalid_keys)))
        if 'set_env' in dep.props.packaging_params:
            dep_env = dep.props.packaging_params['set_env']
            check_env_overrides(
                set(dep_env.keys()), 'set', 'dependency {}'.format(dep.name))
            effective_env.update(dep_env)
        if 'semicolon_join_env' in dep.props.packaging_params:
            append_env = dep.props.packaging_params['semicolon_join_env']
            check_env_overrides(set(append_env.keys()), 'manipulations',
                                'dependency {}'.format(dep.name))
            for key, value in append_env.items():
                env_manip = env_manipulations.setdefault(
                    key, ['${{{}}}'.format(key)])
                if value not in env_manip:
                    env_manip.append(value)

        if 'apt-repository' in dep.tags:
            apt_repo_deps.append(dep)
        if 'apt-installable' in dep.tags:
            add_package('apt', format_apt_specifier(dep))
        if 'pip-installable' in dep.tags:
            add_package('pip', format_pypi_specifier(dep))
        if 'custom-installer' in dep.tags:
            add_package('custom', dep.props.installer_desc)
        if 'npm-installable' in dep.tags:
            if dep.props.global_install:
                add_package('npm-global', format_npm_specifier(dep))
            else:
                add_package('npm-local', format_npm_specifier(dep))
        if 'gem-installable' in dep.tags:
            add_package('gem', format_gem_specifier(dep))

    # Add environment variables (one layer)
    if env:
        check_env_overrides(set(env.keys()), 'set', 'the target')
        effective_env.update(env)
    for key, value in env_manipulations.items():
        effective_env[key] = ':'.join(value)
    if effective_env:
        dockerfile.append(
            'ENV {}\n'.format(
                ' '.join('{}="{}"'.format(key, value)
                         for key, value in sorted(effective_env.items()))))

    apt_key_cmds = []
    apt_repositories = []
    for dep in apt_repo_deps:
        source_line, apt_key_cmd = parse_apt_repository(
            build_context, dep, distro)
        apt_repositories.append(source_line)
        if apt_key_cmd:
            apt_key_cmds.append(apt_key_cmd)
    # Handle apt keys (one layer for all)
    if apt_key_cmds:
        dockerfile.append(
            'RUN {}\n'.format(' && '.join(apt_key_cmds)))
    # Handle apt repositories (one layer for all)
    if apt_repositories:
        apt_src_file = join(workspace_dir, 'ybt.list')
        if make_apt_sources_list(apt_repositories, apt_src_file):
            dockerfile.append(
                'COPY ybt.list /etc/apt/sources.list.d/\n')

    custom_cnt = 0
    pip_req_cnt = 0

    def install_npm(npm_packages: list, global_install: bool):
        if npm_packages:
            if not global_install:
                dockerfile.append('WORKDIR /usr/src\n')
            dockerfile.append(
                'RUN npm install {} {}\n'.format(
                    ' '.join(npm_packages),
                    '--global' if global_install else '&& npm dedupe'))

    for layer in packaging_layers:
        pkg_type, packages = layer

        if pkg_type == 'apt':
            dockerfile.append(
                'RUN apt-get update -y && apt-get install '
                '--no-install-recommends -y {} '
                '&& rm -rf /var/lib/apt/lists/*\n'.format(
                    ' '.join(sorted(packages))))

        elif pkg_type == 'custom':
            # Handle custom installers (2 layers per occurrence)
            custom_cnt += 1
            packages_dir = 'packages{}'.format(custom_cnt)
            tmp_install = '/tmp/install{}'.format(custom_cnt)
            workspace_packages_dir = join(workspace_dir, packages_dir)
            try:
                shutil.rmtree(workspace_packages_dir)
            except FileNotFoundError:
                pass
            os.makedirs(workspace_packages_dir)
            run_installers = []
            for custom_installer in packages:
                package_tar = basename(custom_installer.package)
                os.link(custom_installer.package,
                        join(workspace_packages_dir, package_tar))
                run_installers.extend([
                    'tar -xf {0}/{1} -C {0}'.format(tmp_install, package_tar),
                    'cd {}/{}'.format(tmp_install, custom_installer.name),
                    './{}'.format(custom_installer.install_script),
                ])
            dockerfile.extend([
                'COPY {} {}\n'.format(packages_dir, tmp_install),
                'RUN {} && cd / && rm -rf {}\n'.format(
                    ' && '.join(run_installers), tmp_install),
            ])

        elif pkg_type == 'pip':
            # Handle pip packages (2 layers per occurrence)
            pip_req_cnt += 1
            req_fname = 'requirements_{}.txt'.format(pip_req_cnt)
            pip_req_file = join(workspace_dir, req_fname)
            if make_pip_requirements(packages, pip_req_file):
                dockerfile.extend([
                    'COPY {} /usr/src/\n'.format(req_fname),
                    'RUN {}pip install --no-cache-dir -r /usr/src/{}\n'.format(
                        'pip install --no-cache-dir --upgrade pip && '
                        if pip_req_cnt == 0 else '', req_fname)
                ])

        elif pkg_type == 'npm-global':
            # Handle npm global packages (1 layer per occurrence)
            install_npm(packages, True)

        elif pkg_type == 'npm-local':
            # Handle npm local packages (1 layer per occurrence)
            install_npm(packages, False)

        elif pkg_type == 'gem':
            # Handle gem (ruby) packages (1 layer per occurrence)
            dockerfile.append(
                'RUN gem install {}\n'.format(' '.join(packages)))

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

    def format_docker_cmd(docker_cmd):
        return ('"{}"'.format(cmd) for cmd in docker_cmd)

    # Add ENTRYPOINT (one layer)
    if entrypoint:
        # TODO(itamar): Consider adding tini as entrypoint also if given
        # Docker CMD without a Docker ENTRYPOINT?
        if build_context.conf.with_tini_entrypoint:
            entrypoint = ['tini', '--'] + entrypoint
        dockerfile.append(
            'ENTRYPOINT [{}]\n'.format(
                ', '.join(format_docker_cmd(entrypoint))))

    # Add CMD (one layer)
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
