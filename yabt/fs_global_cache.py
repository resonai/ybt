# -*- coding: utf-8 -*-

# Copyright 2019 Resonai Ltd. All rights reserved
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
A global cache implemented in local dick
~~~~~~~~~~~~~~~~~~~

:author: Dana Shamir
"""
import os
import shutil
from os.path import join, isdir
from typing import List

from .global_cache import GlobalCache

SUMMARY_FILE = 'summary.json'
ARTIFACTS_FILE = 'artifact.json'
TARGETS_DIR = 'targets'
ARTIFACTS_DIR = 'artifacts'


class FSGlobalCache(GlobalCache):
    def __init__(self, directory='/tmp/cache'):
        self.targets_dir = join(directory, TARGETS_DIR)
        self.artifacts_dir = join(directory, ARTIFACTS_DIR)
        os.makedirs(self.targets_dir, exist_ok=True)
        os.makedirs(self.artifacts_dir, exist_ok=True)

    def has_cache(self, target_hash: str):
        return isdir(join(self.targets_dir, target_hash))

    def download_summary(self, target_hash: str, dst: str):
        shutil.copyfile(join(self.targets_dir, target_hash, SUMMARY_FILE),
                        dst)

    def download_artifacts_meta(self, target_hash: str, dst: str):
        shutil.copyfile(join(self.targets_dir, target_hash, ARTIFACTS_FILE),
                        dst)

    def download_artifacts(self, artifacts_hashes: List[str], dst: str):
        for artifact_hash in artifacts_hashes:
            shutil.copyfile(join(self.artifacts_dir, artifact_hash),
                            join(dst, artifact_hash))

    def create_target_cache(self, target_hash: str):
        if not isdir(join(self.targets_dir, target_hash)):
            os.mkdir(join(self.targets_dir, target_hash))

    def upload_summary(self, target_hash: str, src: str):
        shutil.copyfile(src,
                        join(self.targets_dir, target_hash, SUMMARY_FILE))

    def upload_artifacts_meta(self, target_hash: str, src: str):
        shutil.copyfile(src,
                        join(self.targets_dir, target_hash, ARTIFACTS_FILE))

    def upload_artifacts(self, artifacts_hashes: List[str], src: str):
        for artifact_hash in artifacts_hashes:
            shutil.copyfile(join(src, artifact_hash),
                            join(self.artifacts_dir, artifact_hash))
