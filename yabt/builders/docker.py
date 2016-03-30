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

"""
yabt Docker Builder
~~~~~~~~~~~~~~~~~~~

:author: Itamar Ostricher
"""


import os
from os.path import join, split, isdir, isfile, samefile
import subprocess

from ostrich.utils.collections import listify

from ..builder import BaseBuilder
from .. import target


class DockerImageRegistryTarget(target.BaseTarget):

    def __init__(self, build_context, name, image, tag=None):
        super().__init__(build_context, name)
        self.image = image
        self.tag = tag

    def __repr__(self):
        return "'DockerImageFromRegistry:{}'".format(self)


class DockerRegistryBuilder(BaseBuilder):

    @staticmethod
    def get_builder_aliases():
        return frozenset(('DockerRegistry', 'DockerHub'))

    def extract_target(self, name, image, tag=None):
        target_inst = DockerImageRegistryTarget(
            self._context, name, image, tag)
        # target_inst.add_deps(requires)
        self._context.register_target(target_inst, self)

    def build(self, target_inst):
        print('Fetch and cache Docker image from registry',
              target_inst.image, target_inst.tag)


class DockerImageTarget(target.BaseTarget):

    def __init__(self, build_context, name, start_from, requires=None,
                 docker_cmd=None):
        super().__init__(build_context, name, deps=requires)
        # self.add_external_deps(external_deps)
        # print(self, start_from, self.deps, self.external_deps, docker_cmd)
        self.start_from = start_from
        self.docker_cmd = docker_cmd

    def __repr__(self):
        return "'DockerImage:{}'".format(self)


class DockerImageBuilder(BaseBuilder):

    @staticmethod
    def get_builder_aliases():
        return frozenset(('DockerImage',))

    def extract_target(
            self, name, start_from, requires=None, docker_cmd=None):
        self._context.register_target(
            DockerImageTarget(self._context, name, start_from,
                              [start_from] + listify(requires),
                              docker_cmd),
            self)

    def sync_copy_sources(self, copy_sources, workspace_src_dir):
        num_copied = 0
        for src in copy_sources:
            abs_src = join(self._context.conf.project_root, src)
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

    @staticmethod
    def make_pip_requirements(pip_requirements, pip_req_file_path):
        if pip_requirements:
            with open(pip_req_file_path, 'w') as pip_req_file:
                pip_req_file.write('\n'.join(pip_requirements) + '\n')
            return True
        elif isfile(pip_req_file_path):
            # delete remnant requirements file
            os.remove(pip_req_file_path)
            return False

    def build(self, target_inst):
        # create directory for this target under a private builder workspace
        workspace_dir = self.get_workspace(target_inst.name)
        # generate Dockerfile and build it
        dockerfile_path = join(workspace_dir, 'Dockerfile')
        start_from = self.get_target_by_depname(target_inst.start_from)
        if start_from.tag:
            dockerfile = ['FROM {}:{}\n'.format(
                start_from.image, start_from.tag)]
        else:
            dockerfile = ['FROM {}\n'.format(start_from.image)]
        copy_sources = []
        pip_requirements = []
        for dep_target in self.walk_target_graph(target_inst.deps[1:]):
            copy_sources.extend(dep_target.get_sources())
            pip_requirements.extend(dep_target.get_pip_requirements())
        print(pip_requirements)
        pip_req_file = join(workspace_dir, 'requirements.txt')
        if self.make_pip_requirements(pip_requirements, pip_req_file):
            dockerfile.extend([
                'COPY requirements.txt /usr/src/\n',
                'RUN pip install --no-cache-dir -r /usr/src/requirements.txt\n'
            ])
        workspace_src_dir = join(workspace_dir, 'src')
        # sync `sources` files between project and `workspace_src_dir`
        if self.sync_copy_sources(copy_sources, workspace_src_dir) > 0:
            dockerfile.extend([
                'RUN mkdir -p /usr/src/app\n',
                'WORKDIR /usr/src/app\n',
                'COPY src /usr/src/app\n',
            ])
        # TODO(itamar): also remove files that shouldn't be there!

        def format_docker_cmd(docker_cmd):
            return ('"{}"'.format(cmd) for cmd in listify(docker_cmd))

        if target_inst.docker_cmd:
            dockerfile.append(
                'CMD [{}]\n'.format(
                    ', '.join(format_docker_cmd(target_inst.docker_cmd))))
        # TODO(itamar): write only if changed?
        with open(dockerfile_path, 'w') as dockerfile_f:
            dockerfile_f.writelines(dockerfile)
        # TODO(itamar): how to determine tag? (between "latest" / git hash /
        # from flag / other)
        docker_build_cmd = [
            'docker', 'build', '-t', '{}:bar'.format(
                target.split_name(target_inst.name)), workspace_dir]
        subprocess.run(docker_build_cmd)
        print('Build Docker image', docker_build_cmd)
