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

"""
yabt Build context module
~~~~~~~~~~~~~~~~~~~~~~~~~

:author: Itamar Ostricher
"""


from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from functools import reduce
import json
import os
from pathlib import PurePath
import platform
import threading
from time import sleep, time

import networkx as nx
from ostrich.utils.proc import run
from ostrich.utils.text import get_safe_path

from .caching import (
    get_prebuilt_targets, load_target_from_cache, save_target_in_cache)
from .config import Config
from .docker import format_qualified_image_name
from .extend import Plugin
from .graph import get_descendants, topological_sort
from .logging import make_logger
from .target_extraction import extractor
from .target_utils import split_build_module, Target
from .utils import fatal


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
        # A dictionary for collecting metadata on build artifacts
        self.artifacts_metadata = {}
        self.context_lock = threading.Lock()

    def get_workspace(self, *parts) -> str:
        """Return a path to a private workspace dir.
           Create sub-tree of dirs using strings from `parts` inside workspace,
           and return full path to innermost directory.

        Upon returning successfully, the directory will exist (potentially
        changed to a safe FS name), even if it didn't exist before, including
        any intermediate parent directories.
        """
        workspace_dir = os.path.join(self.conf.get_workspace_path(),
                                     *(get_safe_path(part) for part in parts))
        if not os.path.isdir(workspace_dir):
            # exist_ok=True in case of concurrent creation of the same dir
            os.makedirs(workspace_dir, exist_ok=True)
        return workspace_dir

    def get_bin_dir(self, build_module: str) -> str:
        """Return a path to the binaries dir for a build module dir.
           Create sub-tree of missing dirs as needed, and return full path
           to innermost directory.
        """
        bin_dir = os.path.join(self.conf.get_bin_path(), build_module)
        if not os.path.isdir(bin_dir):
            # exist_ok=True in case of concurrent creation of the same dir
            os.makedirs(bin_dir, exist_ok=True)
        return bin_dir

    def walk_target_deps_topological_order(self, target: Target):
        """Generate all dependencies of `target` by topological sort order."""
        all_deps = get_descendants(self.target_graph, target.name)
        for dep_name in topological_sort(self.target_graph):
            if dep_name in all_deps:
                yield self.targets[dep_name]

    def generate_direct_deps(self, target: Target):
        """Generate only direct dependencies of `target`."""
        yield from (self.targets[dep_name] for dep_name in target.deps)

    def generate_dep_names(self, target: Target):
        """Generate names of all dependencies (descendants) of `target`."""
        yield from get_descendants(self.target_graph, target.name)

    def generate_all_deps(self, target: Target):
        """Generate all dependencies of `target` (the target nodes)."""
        yield from (self.targets[dep_name]
                    for dep_name in self.generate_dep_names(target))

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
        build_module = split_build_module(target_name)
        if build_module in self.targets_by_module:
            self.targets_by_module[build_module].remove(target_name)

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

    def get_buildenv_graph(self):
        """Return a graph induced by buildenv nodes"""
        # This implementation first obtains all subsets of nodes that all
        # buildenvs depend on, and then builds a subgraph induced by the union
        # of these subsets. This can be very non-optimal.
        # TODO(itamar): Reimplement efficient algo, or redesign buildenvs
        buildenvs = set(target.buildenv for target in self.targets.values()
                        if target.buildenv)
        return nx.DiGraph(self.target_graph.subgraph(reduce(
            lambda x, y: x | set(y),
            (get_descendants(self.target_graph, buildenv)
             for buildenv in buildenvs), buildenvs)))

    def ready_nodes_iter(self, graph_copy):
        """Generate ready targets from the graph `graph_copy`.

        The input graph is mutated by this method, so it has to be a mutable
        copy of the graph (e.g. not original copy, or read-only view).

        Caller **must** call `done()` after processing every generated
        target, so additional ready targets can be added to the queue.

        The invariant: a target may be yielded from this generator only
        after all its descendant targets were notified "done".
        """

        def is_ready(target_name):
            """Return True if the node `target_name` is "ready" in the graph
               `graph_copy`.

            "Ready" means that the graph doesn't contain any more nodes that
            `target_name` depends on (e.g. it has no successors).
            """
            try:
                next(graph_copy.successors(target_name))
            except StopIteration:
                return True
            return False

        ready_nodes = deque(sorted(
            target_name for target_name in graph_copy.nodes
            if is_ready(target_name)))
        produced_event = threading.Event()
        failed_event = threading.Event()

        def make_done_callback(target: Target):
            """Return a callable "done" notifier to
               report a target as processed."""

            def done_notifier():
                """Mark target as done, adding new ready nodes to queue"""
                if graph_copy.has_node(target.name):
                    affected_nodes = list(sorted(
                        graph_copy.predecessors(target.name)))
                    graph_copy.remove_node(target.name)
                    ready_nodes.extend(
                        target_name for target_name in affected_nodes
                        if is_ready(target_name))
                    produced_event.set()

            return done_notifier

        while True:
            while len(ready_nodes) == 0:
                if graph_copy.order() == 0:
                    return
                if failed_event.is_set():
                    return
                produced_event.wait(0.5)
            produced_event.clear()
            next_node = ready_nodes.popleft()
            node = self.targets[next_node]
            node.done = make_done_callback(node)
            node.fail = lambda: failed_event.set()
            yield node

    def target_iter(self):
        """Generate ready targets from entire target graph.

        Caller **must** call `done()` after processing every generated target,
        so additional ready targets can be added to the queue.

        The invariant: a target may be yielded from this generator only after
        all its descendant targets were notified "done".
        """
        yield from self.ready_nodes_iter(self.target_graph.copy())

    def buildenv_iter(self):
        """Generate ready targets from subgraph of buildenvs.

        Caller **must** call `done()` after processing every generated target,
        so additional ready targets can be added to the queue.

        The invariant: a target may be yielded from this generator only after
        all its descendant targets were notified "done".
        """
        yield from self.ready_nodes_iter(self.get_buildenv_graph())

    def run_in_buildenv(
            self, buildenv_target_name: str, cmd: list, cmd_env: dict=None,
            work_dir: str=None, auto_uid: bool=True, **kwargs):
        """Run a command in a named BuildEnv Docker image.

        :param buildenv_target_name: A named Docker image target in which the
                                     command should be run.
        :param cmd: The command to run, as you'd pass to subprocess.run()
        :param cmd_env: A dictionary of environment variables for the command.
        :param work_dir: A different work dir to run in.
                         Either absolute path, or relative to project root.
        :param auto_uid: Whether to run as the active uid:gid, or as root.
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
        docker_run = ['docker', 'run']
        # if not self.conf.non_interactive:
        #     docker_run.append('-i')
        if not redirection:
            docker_run.append('-t')
        project_vol = (self.conf.docker_volume if self.conf.docker_volume else
                       self.conf.project_root)
        container_work_dir = PurePath('/project')
        if work_dir:
            container_work_dir /= work_dir
        docker_run.extend([
            '--rm',
            '-v', project_vol + ':/project',
            # TODO: windows containers?
            '-w', container_work_dir.as_posix(),
        ])
        if cmd_env:
            for key, value in cmd_env.items():
                # TODO(itamar): escaping
                docker_run.extend(['-e', '{}={}'.format(key, value)])
        if platform.system() == 'Linux' and auto_uid:
            # Fix permissions for bind-mounted project dir
            # The fix is not needed when using Docker For Mac / Windows,
            # because it is somehow taken care of by the sharing mechanics
            docker_run.extend(['-u', '{}:{}'.format(os.getuid(), os.getgid())])
        docker_run.append(format_qualified_image_name(buildenv_target))
        docker_run.extend(cmd)
        logger.info('Running command in build env "{}" using command {}',
                    buildenv_target_name, docker_run)
        return run(docker_run, check=True, **kwargs)

    def build_target(self, target: Target):
        """Invoke the builder function for a target."""
        builder = Plugin.builders[target.builder_name]
        if builder.func:
            logger.debug('About to invoke the {} builder function for {}',
                         target.builder_name, target.name)
            builder.func(self, target)
        else:
            logger.debug('Skipping {} builder function for target {} (no '
                         'function registered)', target.builder_name, target)

    def test_target(self, target: Target):
        """Invoke the tester function for a target."""
        builder = Plugin.builders[target.builder_name]
        if builder.test_func:
            logger.debug('About to invoke the {} tester function for {}',
                         target.builder_name, target.name)
            builder.test_func(self, target)
        else:
            logger.debug('Skipping {} tester function for target {} (no '
                         'function registered)', target.builder_name, target)

    def register_target_artifact_metadata(self, target: str, metadata: dict):
        """Register the artifact metadata dictionary for a built target."""
        with self.context_lock:
            self.artifacts_metadata[target.name] = metadata

    def write_artifacts_metadata(self):
        """Write out a JSON file with all built targets artifact metadata,
           if such output file is specified."""
        if self.conf.artifacts_metadata_file:
            logger.info('Writing artifacts metadata to file "%s"',
                        self.conf.artifacts_metadata_file)
            with open(self.conf.artifacts_metadata_file, 'w') as fp:
                json.dump(self.artifacts_metadata, fp)

    def can_use_cache(self, target: Target) -> bool:
        """Return True if should attempt to load `target` from cache.
           Return False if `target` has to be built, regardless of its cache
           status (because cache is disabled, or dependencies are dirty).
        """
        # if caching is disabled for this execution, then all targets are dirty
        if self.conf.no_build_cache:
            return False
        # if the target's `cachable` prop is falsy, then it is dirty
        if not target.props.cachable:
            return False
        # if any dependency of the target is dirty, then the target is dirty
        if any(self.targets[dep].is_dirty for dep in target.deps):
            return False
        # if the target has a dirty buildenv then it's also dirty
        if target.buildenv and self.targets[target.buildenv].is_dirty:
            return False
        return True

    def build_graph(self, run_tests: bool=False):
        built_targets = set(get_prebuilt_targets(self))

        def build(target: Target):
            """Build `target` if it wasn't built already, and mark it built."""
            # avoid rebuilding built target
            if target.name in built_targets:
                target.done()
                return
            try:
                # check if cache can be used to skip building target
                build_cached, test_cached = False, False
                if self.can_use_cache(target):
                    build_cached, test_cached = load_target_from_cache(
                        target, self)

                target_built = False
                if build_cached:
                    logger.info('Target {} loaded from cache - skipping build',
                                target.name)
                else:
                    logger.info('Building target {}', target.name)
                    target.is_dirty = True
                    # test can't be cached if running build
                    test_cached = False
                    build_start = time()
                    self.build_target(target)
                    target.summary['build_time'] = time() - build_start
                    logger.info('Build of target {} completed in {} sec',
                                target.name, target.summary['build_time'])
                    target_built = True
                built_targets.add(target.name)
                target.done()

                # TODO: retry flaky tests N times
                # TODO: collect stats and print report at the end
                # TODO: support both "fail fast" (exit on first failure) and
                #       run all tests (don't exit on first failure) modes
                target_tested = False
                if run_tests and 'testable' in target.tags:
                    if self.conf.no_test_cache or not test_cached:
                        logger.info('Testing target {}', target.name)
                        test_start = time()
                        self.test_target(target)
                        target.summary['test_time'] = time() - test_start
                        logger.info('Test of target {} completed in {} sec',
                                    target.name, target.summary['test_time'])
                        target_tested = True
                    else:
                        logger.info(
                            'Target {} test cached - skipping test run',
                            target.name)

                # write to cache only if build or test was executed
                if target_built or target_tested:
                    save_target_in_cache(target, self)
            except Exception as ex:
                target.fail()
                fatal('`{}\': {}', target.name, ex)

        def build_in_pool(seq):
            jobs = self.conf.jobs
            # don't use thread pool in case of single worker
            if jobs > 1:
                with ThreadPoolExecutor(max_workers=jobs) as executor:
                    list(executor.map(build, seq))
            else:
                for target in seq:
                    build(target)

        logger.info('Marked {} targets as "pre-built" in cached base images',
                    len(built_targets))

        logger.info('Building {} flavor using {} workers -- BuildEnv PrePass',
                    self.conf.flavor, self.conf.jobs)
        # pre-pass: build detected buildenv targets and their dependencies
        build_in_pool(self.buildenv_iter())
        logger.info('Building {} flavor using {} workers -- Main Pass',
                    self.conf.flavor, self.conf.jobs)
        # main pass: build rest of the graph
        build_in_pool(self.target_iter())
        logger.info('Finished building target graph successfully')
