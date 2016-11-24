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
yabt utils
~~~~~~~~~~

:author: Itamar Ostricher
"""


import os
from os.path import isdir, isfile, join, normpath, relpath, split
import shutil
import sys

from ostrich.utils.path import commonpath

from .compat import scandir
from .logging import make_logger


logger = make_logger(__name__)


def rmtree(path: str):
    """Forcibly remove directory tree.
       Fail silently if base dir doesn't exist."""
    try:
        shutil.rmtree(path)
    except FileNotFoundError:
        pass


def link_func(src: str, dst: str):
    try:
        os.link(src, dst)
    except FileExistsError:
        pass


def link_node(abs_src: str, abs_dest: str):
    """Sync source node (file / dir) to destination path using hard links."""
    if isfile(abs_src):
        # sync file by linking it to dest
        dest_parent_dir = split(abs_dest)[0]
        if not isdir(dest_parent_dir):
            # exist_ok=True in case of concurrent creation of the same
            # parent dir
            os.makedirs(dest_parent_dir, exist_ok=True)
        link_func(abs_src, abs_dest)
    elif isdir(abs_src):
        # sync dir by recursively linking files under it to dest
        shutil.copytree(abs_src, abs_dest,
                        copy_function=link_func,
                        ignore=shutil.ignore_patterns('.git'))
    else:
        raise FileNotFoundError(abs_src)


def link_artifacts(artifacts: set, workspace_src_dir: str,
                   common_parent: str, conf):
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
    norm_dir = normpath(workspace_src_dir)
    if norm_dir not in conf.deleted_dirs:
        conf.deleted_dirs.add(norm_dir)
        rmtree(norm_dir)
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
        link_node(abs_src, abs_dest)
        num_linked += 1
    return num_linked


def norm_proj_path(path, build_module):
    """Return a normalized path for the `path` observed in `build_module`.

    The normalized path is "normalized" (in the `os.path.normpath` sense),
    and relative from the project root directory.

    Supports making references from project root directory by prefixing the
    path with "//".

    :raises ValueError: If path references outside the project sandbox.
    """
    if path == '//':
        return ''

    if path.startswith('//'):
        norm = normpath(path[2:])
        if norm[0] in ('.', '/', '\\'):
            raise ValueError("Invalid path: `{}'".format(path))
        return norm

    if path.startswith('/'):
        raise ValueError("Invalid path: `{}' - use '//' to start from "
                         "project root".format(path))

    norm = normpath(join(build_module, path))
    if norm == '.':
        return ''
    if norm.startswith('..'):
        raise ValueError(
            "Invalid path `{}' - must remain inside project sandbox"
            .format(path))
    return norm


def search_for_parent_dir(start_at: str=None, with_files: set=None,
                          with_dirs: set=None) -> str:
    """Return absolute path of first parent directory of `start_at` that
       contains a file named `BUILD_PROJ_FILE` (including `start_at`).

    If `start_at` not specified, start at current working directory.

    :param start_at: Initial path for searching for the project build file.

    Returns `None` upon reaching FS root without finding a project buildfile.
    """
    if not start_at:
        start_at = os.path.abspath(os.curdir)
    if not with_files:
        with_files = set()
    if not with_dirs:
        with_dirs = set()
    exp_hits = len(with_files) + len(with_dirs)
    while start_at:
        num_hits = 0
        for entry in scandir(start_at):
            if ((entry.is_file() and entry.name in with_files) or
                    (entry.is_dir() and entry.name in with_dirs)):
                num_hits += 1
            if num_hits == exp_hits:
                return start_at
        cur_level = start_at
        start_at = os.path.split(cur_level)[0]
        if os.path.realpath(cur_level) == os.path.realpath(start_at):
            # looped on root once
            break


def yprint(config, *objects, **kwargs):
    if config.verbose:
        print(*objects, **kwargs)
    else:
        logger.info('{}', ' '.join(str(obj) for obj in objects))
