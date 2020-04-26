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
yabt utils
~~~~~~~~~~

:author: Itamar Ostricher
"""


import functools
import hashlib
import os
from os.path import isdir, isfile, join, normpath, relpath, split
import shutil
import sys
from traceback import format_exc

from colorama import Fore, Style
from ostrich.utils.path import commonpath

from .compat import scandir, walk
from .logging import make_logger


logger = make_logger(__name__)


def fatal(msg, *args, **kwargs):
    """Print a red `msg` to STDERR and exit.
    To be used in a context of an exception, also prints out the exception.
    The message is formatted with `args` & `kwargs`.
    """
    exc_str = format_exc()
    if exc_str.strip() != 'NoneType: None':
        logger.info('{}', format_exc())
    fatal_noexc(msg, *args, **kwargs)


def fatal_noexc(msg, *args, **kwargs):
    """Print a red `msg` to STDERR and exit.

    The message is formatted with `args` & `kwargs`.
    """
    print(Fore.RED + 'Fatal: ' + msg.format(*args, **kwargs) + Style.RESET_ALL,
          file=sys.stderr)
    sys.exit(1)


def rmnode(path: str):
    """Forcibly remove file or directory tree at `path`.
       Fail silently if base dir doesn't exist."""
    if isdir(path):
        rmtree(path)
    elif isfile(path):
        os.remove(path)


def rmtree(path: str):
    """Forcibly remove directory tree.
       Fail silently if base dir doesn't exist."""
    try:
        shutil.rmtree(path)
    except FileNotFoundError:
        pass


def link_func(src: str, dst: str, force: bool=True):
    if force:
        try:
            os.remove(dst)
        except FileNotFoundError:
            pass
    try:
        os.link(src, dst)
    except FileExistsError:
        pass


def link_node(abs_src: str, abs_dest: str, force: bool=True):
    """Sync source node (file / dir) to destination path using hard links."""
    dest_parent_dir = split(abs_dest)[0]
    if not isdir(dest_parent_dir):
        # exist_ok=True in case of concurrent creation of the same
        # parent dir
        os.makedirs(dest_parent_dir, exist_ok=True)
    if isfile(abs_src):
        # sync file by linking it to dest
        link_func(abs_src, abs_dest, force)
    elif isdir(abs_src):
        # sync dir by recursively linking files under it to dest
        shutil.copytree(abs_src, abs_dest,
                        copy_function=functools.partial(link_func,
                                                        force=force),
                        ignore=shutil.ignore_patterns('.git'))
    else:
        raise FileNotFoundError(abs_src)


def link_files(files: set, workspace_src_dir: str,
               common_parent: str, conf):
    """Sync the list of files and directories in `files` to destination
       directory specified by `workspace_src_dir`.

    "Sync" in the sense that every file given in `files` will be
    hard-linked under `workspace_src_dir` after this function returns, and no
    other files will exist under `workspace_src_dir`.

    For directories in `files`, hard-links of contained files are
    created recursively.

    All paths in `files`, and the `workspace_src_dir`, must be relative
    to `conf.project_root`.

    If `common_parent` is given, and it is a common parent directory of all
    `files`, then the `commonm_parent` part is truncated from the
    sync'ed files destination path under `workspace_src_dir`.

    :raises FileNotFoundError: If `files` contains files or directories
                               that do not exist.

    :raises ValueError: If `common_parent` is given (not `None`), but is *NOT*
                        a common parent of all `files`.
    """
    base_dir = ''
    if common_parent:
        common_parent = normpath(common_parent)
        base_dir = commonpath(list(files) + [common_parent])
        if base_dir != common_parent:
            raise ValueError('{} is not the common parent of all target '
                             'sources and data'.format(common_parent))
        logger.debug(
            'Rebasing files in image relative to common parent dir {}',
            base_dir)
    num_linked = 0
    for src in files:
        abs_src = join(conf.project_root, src)
        abs_dest = join(conf.project_root, workspace_src_dir,
                        relpath(src, base_dir))
        link_node(abs_src, abs_dest)
        num_linked += 1
    return num_linked


def norm_proj_path(path, build_module):
    """Return a normalized path for the `path` observed in `build_module`.

    The normalized path is "normalized" (in the `os.path.normpath` sense),
    relative from the project root directory, and OS-native.

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

    if build_module == '//':
        build_module = ''
    norm = normpath(join(build_module, path))
    if norm.startswith('..'):
        raise ValueError(
            "Invalid path `{}' - must remain inside project sandbox"
            .format(path))
    return norm.strip('.')


def search_for_parent_dir(start_at: str=None, with_files: set=None,
                          with_dirs: set=None) -> str:
    """Return absolute path of first parent directory of `start_at` that
       contains all files `with_files` and all dirs `with_dirs`
       (including `start_at`).

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
        logger.debug('{}', ' '.join(str(obj) for obj in objects))


_BUF_SIZE = 1024 * 1024  # read file in 1MB chunks


def acc_hash(filepath: str, hasher):
    """Accumulate content of file at `filepath` in `hasher`."""
    with open(filepath, 'rb') as f:
        while True:
            chunk = f.read(_BUF_SIZE)
            if not chunk:
                break
            hasher.update(chunk)


def hash_file(filepath: str) -> str:
    """Return the hexdigest MD5 hash of content of file at `filepath`."""
    md5 = hashlib.md5()
    acc_hash(filepath, md5)
    return md5.hexdigest()


def hash_tree(filepath: str) -> str:
    """Return the hexdigest MD5 hash of file or directory at `filepath`.

    If file - just hash file content.
    If directory - walk the directory, and accumulate hashes of all the
    relative paths + contents of files under the directory.
    """
    if isfile(filepath):
        return hash_file(filepath)
    if isdir(filepath):
        base_dir = filepath
        md5 = hashlib.md5()
        for root, dirs, files in walk(base_dir):
            dirs.sort()
            for fname in sorted(files):
                filepath = join(root, fname)
                # consistent hashing between POSIX & Windows
                md5.update(relpath(filepath, base_dir)
                           .replace('\\', '/').encode('utf8'))
                acc_hash(filepath, md5)
        return md5.hexdigest()
    return None
