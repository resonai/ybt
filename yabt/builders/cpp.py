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
yabt C++ Builder
~~~~~~~~~~~~~~~~

:author: Itamar Ostricher

TODO: support injecting compile/link flags for 3rd party libs
TODO: CppSharedLib builder
"""


from os.path import basename, dirname, join, relpath, splitext

from ostrich.utils.collections import listify

from ..artifact import ArtifactType as AT
from .dockerapp import build_app_docker_and_bin, register_app_builder_sig
from ..extend import (
    PropType as PT, register_build_func, register_builder_sig,
    register_manipulate_target_hook, register_test_func)
from ..logging import make_logger
from ..target_utils import split
from ..utils import link_artifacts, rmtree, yprint


logger = make_logger(__name__)


class CompilerConfig:
    """Helper class for managing compiler / linker options and flags.

    Design note:
    Notice the `extra_{compile,link}_flags` for target X are collected from
    all the dependencies of target X, but are actually applied to a command
    that is executed within the **build-env image** of target X, which can
    have a completely unrelated subgraph!
    It is the responsibility of the "user" to use these parameters correctly,
    and make sure that the build-env-image contains the **build-time**
    dependencies that are needed to make this parameters work *there*, while
    the target itself has the correct **runtime** dependencies.
    See an example of how this plays out in the YaBT tests - specifically,
    check out the `cpp/hello_boost` test and examine how the build-env image
    contains boost dev-lib (for build-time, including all boost sub-libs),
    while the final target depends on boost-runtime, which installs only 3
    boost shared objects that are needed for this specific application.

    TODO: add this note to proper project docs (also - create proper docs...)
    """

    def __init__(self, build_context, target, extra_params={}):
        self.compiler = self.get(
            'compiler', build_context.conf, target, 'g++')
        self.linker = self.get(
            'linker', build_context.conf, target, 'g++')
        self.compile_flags = self.get(
            'compile_flags', build_context.conf, target, [])
        self.link_flags = self.get(
            'link_flags', build_context.conf, target, [])
        self.include_path = self.get(
            'include_path', build_context.conf, target, [])

        def generate_extra_params():
            yield from (dep.props.build_params
                        for dep in build_context.generate_all_deps(target))
            yield target.props.build_params
            yield extra_params

        for build_params in generate_extra_params():
            self.compile_flags.extend(
                listify(build_params.get('extra_compile_flags')))
            self.link_flags.extend(
                listify(build_params.get('extra_link_flags')))

    def as_dict(self):
        return {key: getattr(self, key)
                for key in ('compiler', 'linker', 'compile_flags',
                            'link_flags', 'include_path')}

    def get(self, param, config, target, fallback):
        """Return the value of `param`, according to priority / expansion.

        First priority - the target itself.
        Second priority - the project config.
        Third priority - a global default ("fallback").

        In list-params, a '$*' term processed as "expansion term", meaning
        it is replaced with all terms from the config-level.
        """
        target_val = target.props.get(param)
        config_val = config.get(param, fallback)
        if not target_val:
            return config_val
        if isinstance(target_val, list):
            val = []
            for el in target_val:
                if el == '$*':
                    val.extend(listify(config_val))
                else:
                    val.append(el)
            return val
        return target_val


# Common C++ builder signature terms
CPP_SIG = [
     ('sources', PT.FileList),
     ('in_buildenv', PT.Target),
     ('headers', PT.FileList, None),
     ('protos', PT.TargetList, None),
     ('cmd_env', None),
     ('compiler', PT.str, None),
     ('linker', PT.str, None),
     ('compile_flags', PT.StrList, None),
     ('link_flags', PT.StrList, None),
     ('include_path', PT.StrList, None),
     # an internal "prop" used internally bt YBT to add compiler config data
     # to the target props, so it is considered by target hashing (for cache)
     ('_internal_dict_', PT.dict, None),
]


register_app_builder_sig(
    'CppApp', [('executable', PT.File, None), ('main', PT.Target, None)])


@register_manipulate_target_hook('CppApp')
def cpp_app_manipulate_target(build_context, target):
    logger.debug('Injecting {} to deps of {}',
                 target.props.base_image, target.name)
    target.deps.append(target.props.base_image)
    if target.props.main and target.props.main not in target.deps:
        logger.debug('Injecting {} to deps of {}',
                     target.props.main, target.name)
        target.deps.append(target.props.main)


@register_build_func('CppApp')
def cpp_app_builder(build_context, target):
    """Pack a C++ binary as a Docker image with its runtime dependencies.

    TODO(itamar): Dynamically analyze the binary and copy shared objects
    from its buildenv image to the runtime image, unless they're installed.
    """
    yprint(build_context.conf, 'Build CppApp', target)
    if target.props.executable and target.props.main:
        raise KeyError(
            '`main` and `executable` arguments are mutually exclusive')
    if target.props.executable:
        if target.props.executable not in target.artifacts.get(AT.app):
            target.artifacts.add(AT.app, target.props.executable)
        entrypoint = [target.props.executable]
    elif target.props.main:
        prog = build_context.targets[target.props.main]
        binary = list(prog.artifacts.get(AT.binary).keys())[0]
        entrypoint = ['/usr/src/bin/' + binary]
    else:
        raise KeyError('Must specify either `main` or `executable` argument')
    build_app_docker_and_bin(
        build_context, target, entrypoint=entrypoint)


register_builder_sig('CppProg', CPP_SIG)
register_builder_sig(
    'CppGTest',
    CPP_SIG + [
        ('test_flags', PT.StrList, None),  # flags to append to test command
        ('test_env', None),  # env vars to inject in test process
        # TODO: support different testenv image for test execution
        # ('in_testenv', PT.Target, None),
    ]
)


def make_pre_build_hook(extra_compiler_config_params):
    """Return a pre-build hook function for C++ builders.

    When called, during graph build, it computes and stores the compiler-config
    object on the target, as well as adding it to the internal_dict prop for
    hashing purposes.
    """

    def pre_build_hook(build_context, target):
        target.compiler_config = CompilerConfig(
            build_context, target, extra_compiler_config_params)
        target.props._internal_dict_['compiler_config'] = (
            target.compiler_config.as_dict())

    return pre_build_hook


@register_manipulate_target_hook('CppProg')
def cpp_prog_manipulate_target(build_context, target):
    target.buildenv = target.props.in_buildenv
    target.pre_build_hook = make_pre_build_hook({})


@register_manipulate_target_hook('CppGTest')
def cpp_gtest_manipulate_target(build_context, target):
    target.tags.add('testable')
    target.buildenv = target.props.in_buildenv
    # target.buildenvs.append(target.props.in_testenv)
    # manipulate the test_flags prop during target extraction (as opposed to
    # during build func), so it is considered during target hashing (for cache)
    target.props.test_flags.extend(listify(
        build_context.conf.get('gtest_params', {}).get('extra_exec_flags')))
    target.pre_build_hook = make_pre_build_hook(
        build_context.conf.get('gtest_params', {}))


def is_cc_file(filename: str) -> bool:
    return splitext(filename)[-1].lower() in ('.cc', '.cpp', '.cxx', '.c++')


def is_h_file(filename: str) -> bool:
    return splitext(filename)[-1].lower() in ('.h', '.hpp', '.hh', '.hxx')


def compile_cc(build_context, compiler_config, buildenv, sources,
               workspace_dir, buildenv_workspace, cmd_env):
    """Compile list of C++ source files in a buildenv image
       and return list of generated object file.
    """
    objects = []
    for src in sources:
        obj_rel_path = '{}.o'.format(splitext(src)[0])
        obj_file = join(buildenv_workspace, obj_rel_path)
        include_paths = [buildenv_workspace] + compiler_config.include_path
        compile_cmd = (
            [compiler_config.compiler, '-o', obj_file, '-c'] +
            compiler_config.compile_flags +
            ['-I{}'.format(path) for path in include_paths] +
            [join(buildenv_workspace, src)])
        # TODO: capture and transform error messages from compiler so file
        # paths match host paths for smooth(er) editor / IDE integration
        build_context.run_in_buildenv(buildenv, compile_cmd, cmd_env)
        objects.append(
            join(relpath(workspace_dir, build_context.conf.project_root),
                 obj_rel_path))
    return objects


def link_cpp_artifacts(build_context, target, workspace_dir,
                       include_objects: bool):
    """Link required artifacts from dependencies under target workspace dir.
       Return list of object files of dependencies (if `include_objects`).

    Includes:
    - Generated code from proto dependencies
    - Header files from all dependencies
    - Generated header files from all dependencies
    - If `include_objects` is True, also object files from all dependencies
      (these will be returned without linking)
    """
    # include the source & header files of the current target
    # add objects of all dependencies (direct & transitive), if needed
    source_files = target.props.sources + target.props.headers
    generated_srcs = {}
    objects = []

    # add headers of dependencies
    for dep in build_context.generate_all_deps(target):
        source_files.extend(dep.props.get('headers', []))

    link_artifacts(source_files, workspace_dir, None, build_context.conf)

    # add generated headers and collect objects of dependencies
    for dep in build_context.generate_all_deps(target):
        dep.artifacts.link_types(workspace_dir, [AT.gen_h], build_context.conf)
        if include_objects:
            objects.extend(dep.artifacts.get(AT.object).values())

    # add generated code from proto dependencies
    for proto_dep_name in target.props.protos:
        proto_dep = build_context.targets[proto_dep_name]
        proto_dep.artifacts.link_types(workspace_dir, [AT.gen_cc],
                                       build_context.conf)

    return objects


def get_source_files(target, build_context) -> list:
    """Return list of source files for `target`."""
    all_sources = list(target.props.sources)
    for proto_dep_name in target.props.protos:
        proto_dep = build_context.targets[proto_dep_name]
        all_sources.extend(proto_dep.artifacts.get(AT.gen_cc).keys())
    return all_sources


def build_cpp(build_context, target, compiler_config, workspace_dir):
    """Compile and link a C++ binary for `target`."""
    rmtree(workspace_dir)
    binary = join(*split(target.name))
    objects = link_cpp_artifacts(build_context, target, workspace_dir, True)
    buildenv_workspace = build_context.conf.host_to_buildenv_path(
        workspace_dir)
    objects.extend(compile_cc(
        build_context, compiler_config, target.props.in_buildenv,
        get_source_files(target, build_context), workspace_dir,
        buildenv_workspace, target.props.cmd_env))
    bin_file = join(buildenv_workspace, binary)
    link_cmd = (
        [compiler_config.linker, '-o', bin_file] +
        objects + compiler_config.link_flags)
    build_context.run_in_buildenv(
        target.props.in_buildenv, link_cmd, target.props.cmd_env)
    target.artifacts.add(AT.binary, relpath(join(workspace_dir, binary),
                         build_context.conf.project_root), binary)


@register_build_func('CppProg')
def cpp_prog_builder(build_context, target):
    """Build a C++ binary executable"""
    yprint(build_context.conf, 'Build CppProg', target)
    workspace_dir = build_context.get_workspace('CppProg', target.name)
    build_cpp(build_context, target, target.compiler_config, workspace_dir)

    # TODO: remove?
    # # Copy binary artifacts to external destination
    # if target.props.copy_bin_to:
    #     link_artifacts([join(workspace_dir, binary)],
    #                    target.props.copy_bin_to,
    #                    workspace_dir, build_context.conf)


@register_build_func('CppGTest')
def cpp_gtest_builder(build_context, target):
    """Build a C++ test executable"""
    yprint(build_context.conf, 'Build CppGTest', target)
    workspace_dir = build_context.get_workspace('CppGTest', target.name)
    build_cpp(build_context, target, target.compiler_config, workspace_dir)


@register_test_func('CppGTest')
def cpp_gtest_tester(build_context, target):
    """Run a C++ test executable"""
    yprint(build_context.conf, 'Run CppGTest', target)
    workspace_dir = build_context.get_workspace('CppGTest', target.name)
    buildenv_workspace = build_context.conf.host_to_buildenv_path(
        workspace_dir)
    test_cmd = [join(buildenv_workspace, *split(target.name))]
    # take gtest exec flags from the target & from project config
    test_cmd.extend(target.props.test_flags)
    build_context.run_in_buildenv(
        # TODO: target.props.in_testenv,
        target.props.in_buildenv, test_cmd, target.props.test_env)


register_builder_sig('CppLib', CPP_SIG)


@register_manipulate_target_hook('CppLib')
def cpp_lib_manipulate_target(build_context, target):
    target.buildenv = target.props.in_buildenv
    # proto targets are also direct dependencies
    target.deps.extend(target.props.protos)
    target.pre_build_hook = make_pre_build_hook({})


@register_build_func('CppLib')
def cpp_lib_builder(build_context, target):
    """Build C++ object files"""
    yprint(build_context.conf, 'Build CppLib', target)
    workspace_dir = build_context.get_workspace('CppLib', target.name)
    workspace_src_dir = join(workspace_dir, 'src')
    rmtree(workspace_src_dir)
    link_cpp_artifacts(build_context, target, workspace_src_dir, False)
    buildenv_workspace = build_context.conf.host_to_buildenv_path(
        workspace_src_dir)
    objects = compile_cc(
        build_context, target.compiler_config, target.props.in_buildenv,
        get_source_files(target, build_context), workspace_src_dir,
        buildenv_workspace, target.props.cmd_env)
    for obj_file in objects:
        target.artifacts.add(AT.object, obj_file)
