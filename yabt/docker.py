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
yabt Docker module
~~~~~~~~~~~~~~~~~~

NOT to be confused with the Docker builder...

:author: Itamar Ostricher
"""


from collections import defaultdict, deque
import os
from os.path import (
    abspath, basename, dirname, isfile, join, relpath, samefile, split)
from pathlib import PurePath
import platform
import shutil

from ostrich.utils.path import commonpath
from ostrich.utils.proc import run, PIPE, CalledProcessError
from ostrich.utils.text import get_safe_path
from ostrich.utils.collections import listify

from .config import Config
from .logging import make_logger
from .builders.custom_installer import get_installer_desc
from .builders.nodejs import format_npm_specifier
from .builders.ruby import format_gem_specifier
from .pkgmgmt import (
    format_apt_specifier, format_pypi_specifier, parse_apt_repository)
from .target_utils import ImageCachingBehavior
from .utils import link_artifacts, link_node, rmtree, yprint


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


def get_image_name(target):
    # left-stripping ":" to remove the build-module separator for root images,
    # since Docker image names must begin with an alphanumeric character
    return (target.props.image_name if target.props.image_name
            else get_safe_path(target.name.lstrip(':')))


def format_qualified_image_name(target):
    if target.builder_name == 'ExtDockerImage':
        if target.props.tag:
            return '{}:{}'.format(target.props.image, target.props.tag)
        return target.props.image
    elif hasattr(target, 'image_id') and target.image_id is not None:
        return target.image_id
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


def pull_docker_image(qualified_image_name: str, pull_cmd: list):
    docker_pull_cmd = pull_cmd + [qualified_image_name]
    logger.debug('Pulling Docker image {} using command {}',
                 qualified_image_name, docker_pull_cmd)
    run(docker_pull_cmd, check=True)


def push_docker_image(qualified_image_name: str, push_cmd: list):
    docker_push_cmd = push_cmd + [qualified_image_name]
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


def handle_build_cache(
        conf: Config, name: str, tag: str, icb: ImageCachingBehavior):
    """Handle Docker image build cache.

    Return image ID if image is cached, and there's no need to redo the build.
    Return None if need to build the image (whether cached locally or not).
    Raise RuntimeError if not allowed to build the image because of state of
    local cache.

    TODO(itamar): figure out a better name for this function, that reflects
    what it returns (e.g. `get_cached_image_id`),
    without "surprising" the caller with the potential of long
    and non-trivial operations that are not usually expected from functions
    with such names.
    """
    if icb.pull_if_cached or (icb.pull_if_not_cached and
                              get_cached_image_id(icb.remote_image) is None):
        try:
            pull_docker_image(icb.remote_image, conf.docker_pull_cmd)
        except CalledProcessError:
            pass
    local_image = '{}:{}'.format(name, tag)
    if (icb.skip_build_if_cached and
            get_cached_image_id(icb.remote_image) is not None):
        tag_docker_image(icb.remote_image, local_image)
        return get_cached_image_id(local_image)
    if ((not icb.allow_build_if_not_cached) and
            get_cached_image_id(icb.remote_image) is None):
        raise RuntimeError('No cached image for {}'.format(local_image))
    return None


def build_docker_image(
        build_context, name: str, tag: str, base_image, deps: list=None,
        env: dict=None, work_dir: str=None,
        entrypoint: list=None, cmd: list=None, full_path_cmd: bool=False,
        distro: dict=None, image_caching_behavior: dict=None,
        runtime_params: dict=None, ybt_bin_path: str=None,
        build_user: str=None, run_user: str=None, labels: dict=None,
        no_artifacts: bool=False):
    """Build Docker image, and return a (image_id, image_name:tag) tuple of
       built image, if built successfully.

    Notes:
    Using the given image name & tag as they are, but using the global host
    Docker image namespace (as opposed to a private-project-workspace),
    so collisions between projects are possible (and very likely, e.g., when
    used in a CI environment, or shared machine use-case).
    Trying to address this issue to some extent by using the image ID after
    it is built, which is unique.
    There's a race condition between "build" and "get ID" - ignoring this at
    the moment.
    Also, I'm not sure about Docker's garbage collection...
    If I use the image ID in other places, and someone else "grabbed" my image
    name and tag (so now my image ID is floating), is it still safe to use
    the ID? Or is it going to be garbage collected and cleaned up sometime?
    From my experiments, the "floating image ID" was left alone (usable),
    but prone to "manual cleanups".
    Also ignoring this at the moment...
    Thought about an alternative approach based on first building an image
    with a randomly generated tag, so I can use that safely later, and tag it
    to the requested tag.
    Decided against it, seeing that every run increases the local Docker
    images spam significantly with a bunch of random tags, making it even less
    useful.
    Documenting it here to remember it was considered, and to discuss it
    further in case anyone thinks it's a better idea than what I went with.
    """
    docker_image = '{}:{}'.format(name, tag)
    # create directory for this target under a private builder workspace
    workspace_dir = build_context.get_workspace('DockerBuilder', docker_image)
    # generate Dockerfile and build it
    dockerfile_path = join(workspace_dir, 'Dockerfile')
    dockerfile = [
        'FROM {}\n'.format(format_qualified_image_name(base_image)),
        'ARG DEBIAN_FRONTEND=noninteractive\n',
    ]
    if build_user:
        dockerfile.append('USER {}\n'.format(build_user))
    workspace_src_dir = join(workspace_dir, 'src')
    rmtree(workspace_src_dir)
    num_linked = 0
    apt_repo_deps = []
    effective_env = {}
    effective_labels = {}
    KNOWN_RUNTIME_PARAMS = frozenset((
        'ports', 'volumes', 'container_name', 'daemonize', 'interactive',
        'term', 'auto_it', 'rm', 'env', 'work_dir', 'impersonate'))
    if runtime_params is None:
        runtime_params = {}
    runtime_params['ports'] = listify(runtime_params.get('ports'))
    runtime_params['volumes'] = listify(runtime_params.get('volumes'))
    runtime_params['env'] = dict(runtime_params.get('env', {}))
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
        if isinstance(pkg_spec, list):
            layer[1].extend(pkg_spec)
        else:
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

    def check_label_overrides(new_labels: set, labels_source: str):
        overridden_labels = new_labels.intersection(effective_labels.keys())
        if overridden_labels:
            raise ValueError(
                'Following labels set from {} override previously set labels '
                'during build of Docker image "{}": {}'.format(
                    labels_source, docker_image, ', '.join(overridden_labels)))

    def update_runtime_params(new_rt_param: dict, params_source: str):
        invalid_keys = set(
            new_rt_param.keys()).difference(KNOWN_RUNTIME_PARAMS)
        if invalid_keys:
            raise ValueError(
                'Unknown keys in runtime params of {}: {}'.format(
                    params_source, ', '.join(invalid_keys)))
        # TODO(itamar): check for invalid values and inconsistencies
        runtime_params['ports'].extend(listify(new_rt_param.get('ports')))
        runtime_params['volumes'].extend(listify(new_rt_param.get('volumes')))
        runtime_params['env'].update(dict(runtime_params.get('env', {})))
        for param in ('container_name', 'daemonize', 'interactive', 'term',
                      'auto_it', 'rm', 'work_dir', 'impersonate'):
            if param in new_rt_param:
                # TODO(itamar): check conflicting overrides
                runtime_params[param] = new_rt_param[param]

    if deps is None:
        deps = []
    # Get all base image deps, so when building this image we can skip adding
    # deps that already exist in the base image.
    base_image_deps = set(build_context.generate_dep_names(base_image))
    for dep in deps:
        if not distro and 'distro' in dep.props:
            distro = dep.props.distro
        if 'runtime_params' in dep.props:
            update_runtime_params(dep.props.runtime_params,
                                  'dependency {}'.format(dep.name))

        if dep.name in base_image_deps:
            logger.debug('Skipping base image dep {}', dep.name)
            continue
        if not no_artifacts:
            num_linked += dep.artifacts.link_for_image(
                workspace_src_dir, build_context.conf)

        PACKAGING_PARAMS = frozenset(
            ('set_env', 'semicolon_join_env', 'set_label'))
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
        if 'set_label' in dep.props.packaging_params:
            dep_labels = dep.props.packaging_params['set_label']
            check_label_overrides(
                set(dep_labels.keys()), 'dependency {}'.format(dep.name))
            effective_labels.update(dep_labels)

        if 'apt-repository' in dep.tags:
            apt_repo_deps.append(dep)
        if 'apt-installable' in dep.tags:
            add_package('apt', format_apt_specifier(dep))
        if 'pip-installable' in dep.tags:
            add_package(dep.props.pip, format_pypi_specifier(dep))
        if 'custom-installer' in dep.tags:
            add_package('custom', get_installer_desc(build_context, dep))
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
        list_name = '{}.list'.format(name)
        apt_src_file = join(workspace_dir, list_name)
        if make_apt_sources_list(apt_repositories, apt_src_file):
            dockerfile.append(
                'COPY {} /etc/apt/sources.list.d/\n'.format(list_name))

    custom_cnt = 0
    pip_req_cnt = defaultdict(int)

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
            rmtree(workspace_packages_dir)
            os.makedirs(workspace_packages_dir)
            run_installers = []
            for custom_installer_desc in packages:
                target_name, install_script, package = custom_installer_desc
                package_tar = basename(package)
                link_node(package, join(workspace_packages_dir, package_tar))
                run_installers.extend([
                    'tar -xf {0}/{1} -C {0}'.format(tmp_install, package_tar),
                    'cd {}/{}'.format(tmp_install, target_name),
                    'cat {} | tr -d \'\\r\' | bash'.format(install_script),
                ])
            dockerfile.extend([
                'COPY {} {}\n'.format(packages_dir, tmp_install),
                'RUN {} && cd / && rm -rf {}\n'.format(
                    ' && '.join(run_installers), tmp_install),
            ])

        elif pkg_type.startswith('pip'):
            # Handle pip packages (2 layers per occurrence)
            req_fname = 'requirements_{}_{}.txt'.format(
                pkg_type, pip_req_cnt[pkg_type] + 1)
            pip_req_file = join(workspace_dir, req_fname)
            if make_pip_requirements(packages, pip_req_file):
                upgrade_pip = (
                    '{pip} install --no-cache-dir --upgrade pip && '
                    .format(pip=pkg_type)
                    if pip_req_cnt[pkg_type] == 0 else '')
                dockerfile.extend([
                    'COPY {} /usr/src/\n'.format(req_fname),
                    'RUN {upgrade_pip}'
                    '{pip} install --no-cache-dir -r /usr/src/{reqs}\n'
                    .format(upgrade_pip=upgrade_pip, pip=pkg_type,
                            reqs=req_fname)
                ])
                pip_req_cnt[pkg_type] += 1

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

    if num_linked > 0:
        dockerfile.append('COPY src /usr/src\n')

    # Add labels (one layer)
    if labels:
        check_label_overrides(set(labels.keys()), 'the target')
        effective_labels.update(labels)
    if effective_labels:
        dockerfile.append(
            'LABEL {}\n'.format(
                ' '.join('"{}"="{}"'.format(key, value)
                         for key, value in sorted(effective_labels.items()))))

    def format_docker_cmd(docker_cmd):
        return ('"{}"'.format(cmd) for cmd in docker_cmd)

    if run_user:
        dockerfile.append('USER {}\n'.format(run_user))

    # Add ENTRYPOINT (one layer)
    if entrypoint:
        # TODO(itamar): Consider adding tini as entrypoint also if given
        # Docker CMD without a Docker ENTRYPOINT?
        entrypoint[0] = PurePath(entrypoint[0]).as_posix()
        if full_path_cmd:
            entrypoint[0] = (PurePath('/usr/src/app') /
                             entrypoint[0]).as_posix()
        if build_context.conf.with_tini_entrypoint:
            entrypoint = ['tini', '--'] + entrypoint
        dockerfile.append(
            'ENTRYPOINT [{}]\n'.format(
                ', '.join(format_docker_cmd(entrypoint))))

    # Add CMD (one layer)
    if cmd:
        cmd[0] = PurePath(cmd[0]).as_posix()
        if full_path_cmd:
            cmd[0] = (PurePath('/usr/src/app') / cmd[0]).as_posix()
        dockerfile.append(
            'CMD [{}]\n'.format(', '.join(format_docker_cmd(cmd))))

    # TODO(itamar): write only if changed?
    with open(dockerfile_path, 'w') as dockerfile_f:
        dockerfile_f.writelines(dockerfile)
    docker_build_cmd = ['docker', 'build']
    if build_context.conf.no_docker_cache:
        docker_build_cmd.append('--no-cache')
    docker_build_cmd.extend(['-t', docker_image, workspace_dir])
    logger.info('Building docker image "{}" using command {}',
                docker_image, docker_build_cmd)
    run(docker_build_cmd, check=True)
    # TODO(itamar): race condition here
    image_id = get_cached_image_id(docker_image)
    metadata = {
        'image_id': image_id,
        'images': [{
            'name': docker_image,
            'pushed': False,
        }],
    }
    icb = ImageCachingBehavior(name, tag, image_caching_behavior)
    if icb.push_image_after_build:
        tag_docker_image(image_id, icb.remote_image)
        push_docker_image(icb.remote_image, build_context.conf.docker_push_cmd)
        metadata['images'].append({
            'name': icb.remote_image,
            'pushed': True,
        })
    # Generate ybt_bin scripts
    if ybt_bin_path:
        # Make sure ybt_bin's are created only under bin_path
        assert (build_context.conf.get_bin_path() ==
                commonpath([build_context.conf.get_bin_path(), ybt_bin_path]))

        def format_docker_run_params(params: dict):
            param_strings = []
            if 'container_name' in params:
                param_strings.extend(['--name', params['container_name']])
            if params.get('interactive'):
                param_strings.append('-i')
            if params.get('term'):
                param_strings.append('-t')
            if params.get('rm'):
                param_strings.append('--rm')
            if params.get('daemonize'):
                param_strings.append('-d')
            if params.get('impersonate') and platform.system() == 'Linux':
                param_strings.extend([
                    '-u', '$( id -u ):$( id -g )',
                    '-v', '/etc/passwd:/etc/passwd:ro',
                    '-v', '/etc/group:/etc/group:ro'])
            for port in params['ports']:
                param_strings.extend(['-p', port])
            for volume in params['volumes']:
                param_strings.extend(['-v', volume])
            if params.get('work_dir'):
                param_strings.extend(['-w', params['work_dir']])
            for var, value in params['env'].items():
                param_strings.extend(['-e', '{}="{}"'.format(var, value)])
            return ' '.join(param_strings)

        with open(join(dirname(abspath(__file__)),
                  'ybtbin.sh.tmpl'), 'r') as tmpl_f:
            ybt_bin = tmpl_f.read().format(
                image_name=docker_image, image_id=image_id,
                docker_opts=format_docker_run_params(runtime_params),
                default_opts='$IT' if runtime_params.get('auto_it') else '')
        with open(ybt_bin_path, 'w') as ybt_bin_f:
            ybt_bin_f.write(ybt_bin)
        os.chmod(ybt_bin_path, 0o755)
        metadata['ybt_bin'] = ybt_bin_path
    return metadata


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
