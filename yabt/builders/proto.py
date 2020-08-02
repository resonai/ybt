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
yabt ProtoBuf builder
~~~~~~~~~~~~~~~~~~~~~

:author: Zohar Rimon, Itamar Ostricher
"""


import os
from os.path import dirname, isfile, join, relpath, splitext
from pathlib import Path, PurePath

from ostrich.utils.path import commonpath
from ostrich.utils.text import get_safe_path

from ..artifact import ArtifactType as AT
from ..compat import walk
from ..extend import (
    PropType as PT, register_build_func, register_builder_sig,
    register_manipulate_target_hook)
from ..logging import make_logger
from ..utils import link_files, rmtree, yprint, link_node

logger = make_logger(__name__)


register_builder_sig(
    'Proto',
    [('sources', PT.FileList),
     ('in_buildenv', PT.Target),
     ('proto_cmd', PT.list, 'protoc'),
     ('gen_python', PT.bool, True),
     ('gen_cpp', PT.bool, True),
     ('gen_go', PT.bool, False),
     ('gen_python_rpcz', PT.bool, False),
     ('gen_cpp_rpcz', PT.bool, False),
     ('gen_python_grpc', PT.bool, False),
     ('gen_cpp_grpc', PT.bool, False),
     ('gen_go_grpc', PT.bool, False),
     ('gen_descriptor', PT.bool, False),
     ('grpc_plugin_path', PT.str, '/usr/local/bin/grpc_cpp_plugin'),
     ('copy_generated_to', PT.File, None),
     ('cmd_env', None),
     ])

register_builder_sig('ProtoCollector')


@register_build_func('Proto')
def proto_builder(build_context, target):
    yprint(build_context.conf, 'Build ProtoBuf', target)
    workspace_dir = build_context.get_workspace('ProtoBuilder', target.name)
    # make sure workdir is clean
    rmtree(workspace_dir)
    proto_dir = join(workspace_dir, 'proto')
    # Collect proto sources from this target and all dependecies,
    # to link under the target sandbox dir
    protos = [source for source in target.props.sources
              if source.endswith('.proto')]
    for dep in build_context.generate_all_deps(target):
        if 'sources' in dep.props:
            protos.extend(source for source in dep.props.sources
                          if source.endswith('.proto'))
    link_files(protos, proto_dir, None, build_context.conf)
    buildenv_workspace = build_context.conf.host_to_buildenv_path(
        workspace_dir)
    protoc_cmd = target.props.proto_cmd + ['--proto_path', buildenv_workspace]
    descriptor_path = join('proto', get_safe_path(target.name.lstrip(':')) +
                           '_descriptor.pb')
    if target.props.gen_cpp:
        protoc_cmd.extend(('--cpp_out', buildenv_workspace))
    if target.props.gen_python:
        protoc_cmd.extend(('--python_out', buildenv_workspace))
    if target.props.gen_go and not target.props.gen_go_grpc:
        protoc_cmd.extend(('--go_out', buildenv_workspace))
    if target.props.gen_cpp_grpc:
        protoc_cmd.extend(
            ('--grpc_out', buildenv_workspace,
             '--plugin=protoc-gen-grpc={}'
             .format(target.props.grpc_plugin_path)))
    if target.props.gen_python_grpc:
        protoc_cmd.extend(('--grpc_python_out', buildenv_workspace))
    if target.props.gen_go_grpc:
        protoc_cmd.append(
            '--go_out=plugins=grpc:{}'.format(buildenv_workspace))
    if target.props.gen_go or target.props.gen_go_grpc:
        protoc_cmd.append(
            '--go_opt=paths=source_relative'
        )
    if target.props.gen_cpp_rpcz:
        protoc_cmd.extend(('--cpp_rpcz_out', buildenv_workspace))
    if target.props.gen_python_rpcz:
        protoc_cmd.extend(('--python_rpcz_out', buildenv_workspace))
    if target.props.gen_descriptor:
        protoc_cmd.extend(
            ('--include_imports', '--descriptor_set_out',
             (PurePath(buildenv_workspace) / descriptor_path).as_posix()))
    protoc_cmd.extend((PurePath(buildenv_workspace) / 'proto' / src).as_posix()
                      for src in target.props.sources)
    build_context.run_in_buildenv(
        target.props.in_buildenv, protoc_cmd, target.props.cmd_env)
    generated_files = []

    def process_generated(gen_file: str, artifact_type: AT):
        if not isfile(gen_file):
            logger.error('Missing expected generated file: {}', gen_file)
            return
        target.artifacts.add(
            artifact_type,
            relpath(gen_file, build_context.conf.project_root),
            relpath(gen_file, workspace_dir))
        generated_files.append(gen_file)

    def create_init_py(path: str):
        init_py_path = join(path, '__init__.py')
        Path(init_py_path).touch(exist_ok=True)
        return init_py_path

    # Add generated files to artifacts / generated list
    for src in target.props.sources:
        src_base = join(proto_dir, splitext(src)[0])
        process_generated(src_base + '.proto', AT.proto)
        if target.props.gen_python:
            process_generated(src_base + '_pb2.py', AT.gen_py)
        if target.props.gen_cpp:
            process_generated(src_base + '.pb.cc', AT.gen_cc)
            process_generated(src_base + '.pb.h', AT.gen_h)
        if target.props.gen_go or target.props.gen_go_grpc:
            process_generated(src_base + '.pb.go', AT.gen_go)
        if target.props.gen_python_rpcz:
            process_generated(src_base + '_rpcz.py', AT.gen_py)
        if target.props.gen_cpp_rpcz:
            process_generated(src_base + '.rpcz.cc', AT.gen_cc)
            process_generated(src_base + '.rpcz.h', AT.gen_h)
        if target.props.gen_python_grpc:
            process_generated(src_base + '_pb2_grpc.py', AT.gen_py)
        if target.props.gen_cpp_grpc:
            process_generated(src_base + '.grpc.pb.cc', AT.gen_cc)
            process_generated(src_base + '.grpc.pb.h', AT.gen_h)
    if target.props.gen_descriptor:
        process_generated(join(workspace_dir, descriptor_path),
                          AT.proto_descriptor)

    # Create __init__.py files in all generated directories with Python files
    if target.props.gen_python or target.props.gen_python_rpcz:
        py_dirs = set(('',))
        for src in target.props.sources:
            py_dir = dirname(src)
            while py_dir not in py_dirs:
                py_dirs.add(py_dir)
                py_dir = dirname(py_dir)
        for py_dir in py_dirs:
            process_generated(create_init_py(join(proto_dir, py_dir)),
                              AT.gen_py)

    # Copy generated files to external destination
    # TODO: remove this? (deprecate copy_generated_to?)
    if target.props.copy_generated_to:
        link_files(generated_files, target.props.copy_generated_to,
                   workspace_dir, build_context.conf)


def add_gen_python_path(target):
    if target.props.gen_python or target.props.gen_python_rpcz:
        join_env = target.props.packaging_params.pop('semicolon_join_env', {})
        if 'PYTHONPATH' in join_env:
            if '/usr/src/gen' not in join_env['PYTHONPATH'].split(':'):
                join_env['PYTHONPATH'] += ':/usr/src/gen'
        else:
            join_env['PYTHONPATH'] = '/usr/src/gen'
        target.props.packaging_params['semicolon_join_env'] = join_env


@register_manipulate_target_hook('Proto')
def proto_manipulate_target(build_context, target):
    target.buildenv = target.props.in_buildenv
    # manipulating the packaging_params (and storing it in the target props)
    # during target extraction (as opposed to build time), because:
    # 1. it should affect the target hash (for cache)
    # 2. it is used by docker builder further down the graph, so it should be
    #    populated if the target is cached (and build func is never called)
    add_gen_python_path(target)


@register_build_func('ProtoCollector')
def proto_collector_builder(build_context, target):
    """
    Collect all the .proto files that this target depend on to a directory
    under yabtwork/*/ProtoCollector.
    If this target depends on a proto target, then all the .proto files needed
    for building this proto will get to this directory.
    TODO(Dana): Support not building the proto (we only need the .proto files)
    """
    workspace_dir = build_context.get_workspace('ProtoCollector', target.name)
    for dep in build_context.generate_all_deps(target):
        artifact_map = dep.artifacts.get(AT.proto)
        if not artifact_map:
            continue
        for dst, src in artifact_map.items():
            target_file = join(workspace_dir, dst)
            link_node(join(build_context.conf.project_root, src), target_file)
            target.artifacts.add(
                AT.proto,
                relpath(target_file, build_context.conf.project_root),
                relpath(target_file, workspace_dir))
