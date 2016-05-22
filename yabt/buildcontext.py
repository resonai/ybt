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
yabt Build context module
~~~~~~~~~~~~~~~~~~~~~~~~~

:author: Itamar Ostricher
"""


from collections import defaultdict
import os
import platform

from ostrich.utils.proc import run
from ostrich.utils.text import get_safe_path

from .config import Config
from .docker import format_qualified_image_name
from .extend import Plugin
from .graph import get_descendants, topological_sort
from .logging import make_logger
from .target_extraction import extractor
from .target_utils import split_build_module, Target


logger = make_logger(__name__)


class BuildContext:
    """Build Context class.

    The framework is designed to operate with a single instance of the
    BuildContext alive, but this is not enforced using a singleton pattern,
    because there's no particular reason to do so...

    While not yet implemented, it is designed to supported concurrent parsing
    of multiple build files using the same build context.
    The design principle to enable this:
    - The "driver" (e.g. main thread in main process) is responsible for
      dispatching build file parsers with copies or references of the build
      context (e.g. on other threads / processes / machines?).
    - Parsers, with their own build context, populate partial target maps.
    - The driver collects the partial results, and is responsible to merge
      them consistently and safely.
    - This will worth it, of course, only if serializing the state to a parser
      and serializing the partial result and merging it back is MUCH cheaper
      than actually doing the parsing, because if it's not, it would be better
      to do it all in the driver (much simpler...) - which is the reason this
      is not yet implemented.
    """

    def __init__(self, conf: Config):
        self.conf = conf
        # A *thread-safe* targets map
        self.targets = {}
        # A *thread-safe* map from build module to set of target names
        # that were extracted from that build module
        self.targets_by_module = defaultdict(set)
        # A *thread-safe* set of processed build-files
        self.processed_build_files = set()
        # Target graph is *not necessarily thread-safe*!
        self.target_graph = None
        # # A *thread-safe* map from BuildEnv name to qualified Docker image
        # #  name for that BuildEnv
        # self.buildenv_images = {}

    def get_workspace(self, *parts) -> str:
        """Return a path to a private workspace dir.
           Create sub-tree of dirs using strings from `parts` inside workspace,
           and return full path to innermost directory.

        Upon returning successfully, the directory will exist (potentially
        changed to a safe FS name), even if it didn't exist before, including
        any intermediate parent directories.
        """
        workspace_dir = os.path.join(self.conf.get_workspace_path(),
                                     *(get_safe_path(part)
                                       for part in parts))
        if not os.path.isdir(workspace_dir):
            # exist_ok=True in case of concurrent creation of the same
            # workspace
            os.makedirs(workspace_dir, exist_ok=True)
        return workspace_dir

    def walk_target_graph(self, target_names: iter):
        """Generate entire target sub-tree for given `target_names` in order.

        Yields target *instances* in the sub-tree, including the nodes given.
        """
        for target_name in target_names:
            yield self.targets[target_name]
            yield from self.walk_target_graph(
                self.target_graph.neighbors_iter(target_name))

    def walk_target_deps_topological_order(self, target: Target):
        all_deps = get_descendants(self.target_graph, target.name)
        for dep_name in topological_sort(self.target_graph):
            if dep_name in all_deps:
                yield self.targets[dep_name]

    def register_target(self, target: Target):
        """Register a `target` instance in this build context.

        A registered target is saved in the `targets` map and in the
        `targets_by_module` map, but is not added to the target graph until
        target extraction is completed (thread safety considerations).
        """
        if target.name in self.targets:
            first = self.targets[target.name]
            raise NameError(
                'Target with name "{0.name}" ({0.builder_name} from module '
                '"{1}") already exists - defined first as '
                '{2.builder_name} in module "{3}"'.format(
                    target, split_build_module(target.name),
                    first, split_build_module(first.name)))
        self.targets[target.name] = target
        self.targets_by_module[split_build_module(target.name)].add(
            target.name)

    def remove_target(self, target_name: str):
        """Remove (unregister) a `target` from this build context.

        Removes the target instance with the given name, if it exists,
        from both the `targets` map and the `targets_by_module` map.

        Doesn't do anything if no target with that name is found.

        Doesn't touch the target graph, if it exists.
        """
        if target_name in self.targets:
            del self.targets[target_name]
        if split_build_module(target_name) in self.targets_by_module:
            self.targets_by_module[split_build_module(target_name)].remove(
                target_name)

    def get_target_extraction_context(self, build_file_path: str) -> dict:
        """Return a build file parser target extraction context.

        The target extraction context is a build-file-specific mapping from
        builder-name to target extraction function,
        for every registered builder.
        """
        extraction_context = {}
        for name, builder in Plugin.builders.items():
            extraction_context[name] = extractor(name, builder,
                                                 build_file_path, self)
        return extraction_context

    # def register_buildenv_image(self, name: str, docker_image: str):
    #     """Register a named BuildEnv Docker image in this build context."""
    #     self.buildenv_images[name] = docker_image

    def run_in_buildenv(
            self, buildenv_target_name: str, cmd: list, cmd_env: dict=None,
            **kwargs):
        """Run a command in a named BuildEnv Docker image.

        :param buildenv_target_name: A named Docker image target in which the
                                     command should be run.
        :param cmd: The command to run, as you'd pass to subprocess.run()
        :param cmd_env: A dictionary of environment variables for the command.
        :param kwargs: Extra keyword arguments that are passed to the
                        subprocess.run() call that runs the BuildEnv container
                        (for, e.g. timeout arg, stdout/err redirection, etc.)

        :raises KeyError: If named BuildEnv is not a registered BuildEnv image
        """
        buildenv_target = self.targets[buildenv_target_name]
        # TODO(itamar): Assert that buildenv_target is up to date
        redirection = any(
            stream_key in kwargs
            for stream_key in ('stdin', 'stdout', 'stderr', 'input'))
        docker_run = [
            'docker', 'run', '-i' if redirection else '-it', '--rm',
            '-v', self.conf.project_root + ':/project', '-w', '/project',
        ]
        if cmd_env:
            for key, value in cmd_env.items():
                # TODO(itamar): escaping
                docker_run.extend(['-e', '{}={}'.format(key, value)])
        if platform.system() == 'Linux':
            # Fix permissions for bind-mounted project dir
            # The fix is not needed when using Docker machine on OS X with
            # VirtualBox or xhyve, because it is somehow taken care of by
            # the shared folder thingie...
            docker_run.extend(['-u', '{}:{}'.format(os.getuid(), os.getgid())])
        docker_run.append(format_qualified_image_name(buildenv_target))
        docker_run.extend(cmd)
        logger.info('Running command in build env "{}" using command {}',
                    buildenv_target_name, docker_run)
        return run(docker_run, **kwargs)

    def build_target(self, target: Target):
        """Invoke the builder function for a target."""
        builder = Plugin.builders[target.builder_name]
        if builder.func:
            logger.info('About to invoke the {} builder function for {}',
                        target.builder_name, target)
            builder.func(self, target)
        else:
            logger.warning('Skipping {} builder function for target {} (no '
                           'function registered)', target.builder_name, target)
