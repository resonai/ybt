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
        for entry in os.scandir(start_at):
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
