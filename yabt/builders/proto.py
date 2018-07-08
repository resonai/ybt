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

from ..compat import walk
from ..extend import (
    PropType as PT, register_build_func, register_builder_sig,
    register_manipulate_target_hook)
from ..logging import make_logger
from ..utils import link_artifacts, yprint


logger = make_logger(__name__)


register_builder_sig(
    'Proto',
    [('sources', PT.FileList),
     ('in_buildenv', PT.Target),
     ('proto_cmd', PT.list, 'protoc'),
     ('gen_python', PT.bool, True),
     ('gen_cpp', PT.bool, True),
     ('gen_python_rpcz', PT.bool, False),
     ('gen_cpp_rpcz', PT.bool, False),
     ('gen_python_grpc', PT.bool, False),
     ('gen_cpp_grpc', PT.bool, False),
     ('grpc_plugin_path', PT.str, '/usr/local/bin/grpc_cpp_plugin'),
     ('copy_generated_to', PT.File, None),
     ('cmd_env', None),
     ])


@register_build_func('Proto')
def proto_builder(build_context, target):
    yprint(build_context.conf, 'Build ProtoBuf', target)
    workspace_dir = build_context.get_workspace('ProtoBuilder', target.name)
    proto_dir = join(workspace_dir, 'proto')
    # Collect proto sources from this target and all dependecies,
    # to link under the target sandbox dir
    protos = [source for source in target.props.sources
              if source.endswith('.proto')]
    for dep in build_context.walk_target_deps_topological_order(target):
        if 'sources' in dep.props:
            protos.extend(source for source in dep.props.sources
                          if source.endswith('.proto'))
    link_artifacts(protos, proto_dir, None, build_context.conf)
    buildenv_workspace = build_context.conf.host_to_buildenv_path(
        workspace_dir)
    protoc_cmd = target.props.proto_cmd + ['--proto_path', buildenv_workspace]
    if target.props.gen_cpp:
        protoc_cmd.extend(('--cpp_out', buildenv_workspace))
    if target.props.gen_python:
        protoc_cmd.extend(('--python_out', buildenv_workspace))
    if target.props.gen_cpp_grpc:
        protoc_cmd.extend(
            ('--grpc_out', buildenv_workspace,
             '--plugin=protoc-gen-grpc={}'
             .format(target.props.grpc_plugin_path)))
    if target.props.gen_python_grpc:
        protoc_cmd.extend(('--grpc_python_out', buildenv_workspace))
    if target.props.gen_cpp_rpcz:
        protoc_cmd.extend(('--cpp_rpcz_out', buildenv_workspace))
    if target.props.gen_python_rpcz:
        protoc_cmd.extend(('--python_rpcz_out', buildenv_workspace))
    protoc_cmd.extend((PurePath(buildenv_workspace) / 'proto' / src).as_posix()
                      for src in target.props.sources)
    build_context.run_in_buildenv(
        target.props.in_buildenv, protoc_cmd, target.props.cmd_env)
    generated_files = []
    target.artifacts['gen'] = {}
    target.artifacts['cpp'] = {}

    def add_artifact(file_path, artifact_kind):
        target.artifacts[artifact_kind][relpath(file_path, workspace_dir)] = (
            relpath(file_path, build_context.conf.project_root))

    def process_generated(src_base, gen_suffixes, artifact_kind):
        gen_files = [src_base + gen_suffix for gen_suffix in gen_suffixes]
        if not all(isfile(gen_path) for gen_path in gen_files):
            logger.error('Missing expected generated files: {}',
                         ', '.join(gen_files))
        else:
            if artifact_kind:
                for gen_file in gen_files:
                    add_artifact(gen_file, artifact_kind)
            generated_files.extend(gen_files)

    def create_init_py(path: str):
        init_py_path = join(path, '__init__.py')
        Path(init_py_path).touch(exist_ok=True)
        return init_py_path

    # Add generated files to artifacts / generated list
    for src in target.props.sources:
        src_base = join(proto_dir, splitext(src)[0])
        if target.props.gen_python:
            process_generated(src_base, ('_pb2.py',), 'gen')
        if target.props.gen_cpp:
            process_generated(src_base, ('.pb.cc', '.pb.h'), 'cpp')
        if target.props.gen_python_rpcz:
            process_generated(src_base, ('_rpcz.py',), 'gen')
        if target.props.gen_cpp_rpcz:
            process_generated(src_base, ('.rpcz.cc', '.rpcz.h'), 'cpp')
        if target.props.gen_python_grpc:
            process_generated(src_base, ('_pb2_grpc.py',), 'gen')
        if target.props.gen_cpp_grpc:
            process_generated(src_base, ('.grpc.pb.cc', '.grpc.pb.h'), 'cpp')

    # Create __init__.py files in all generated directories with Python files
    if target.props.gen_python or target.props.gen_python_rpcz:
        join_env = target.props.packaging_params.pop('semicolon_join_env', {})
        if 'PYTHONPATH' in join_env:
            if '/usr/src/gen' not in join_env['PYTHONPATH'].split(':'):
                join_env['PYTHONPATH'] += ':/usr/src/gen'
        else:
            join_env['PYTHONPATH'] = '/usr/src/gen'
        target.props.packaging_params['semicolon_join_env'] = join_env
        py_dirs = set(('',))
        for src in target.props.sources:
            py_dir = dirname(src)
            while py_dir not in py_dirs:
                py_dirs.add(py_dir)
                py_dir = dirname(py_dir)
        for py_dir in py_dirs:
            add_artifact(create_init_py(join(proto_dir, py_dir)), 'gen')

    # Copy generated files to external destination
    if target.props.copy_generated_to:
        link_artifacts(generated_files, target.props.copy_generated_to,
                       workspace_dir, build_context.conf)
        if target.props.gen_python or target.props.gen_python_rpcz:
            # Create __init__.py files in external destination dirs too
            for root, dirs, unused_files in walk(
                    target.props.copy_generated_to):
                for proto_dir in dirs:
                    create_init_py(join(root, proto_dir))


@register_manipulate_target_hook('Proto')
def proto_manipulate_target(build_context, target):
    target.buildenv = target.props.in_buildenv
