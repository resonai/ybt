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
from os.path import join, isdir, isfile
from typing import Dict

from .global_cache import GlobalCache, SUMMARY_FILE, ARTIFACTS_FILE, \
    TESTS_FILE, ARTIFACTS_DIR, TARGETS_DIR


class FSGlobalCache(GlobalCache):
    def __init__(self, directory='/tmp/ybt_cache'):
        self.targets_dir = join(directory, TARGETS_DIR)
        self.artifacts_dir = join(directory, ARTIFACTS_DIR)
        os.makedirs(self.targets_dir, exist_ok=True)
        os.makedirs(self.artifacts_dir, exist_ok=True)

    def has_cache(self, target_hash: str):
        return isdir(join(self.targets_dir, target_hash))

    def download_summary(self, target_hash: str, dst: str) -> bool:
        return self.download_meta_file(target_hash, SUMMARY_FILE, dst)

    def download_artifacts_meta(self, target_hash: str, dst: str) -> bool:
        return self.download_meta_file(target_hash, ARTIFACTS_FILE, dst)

    def download_test_cache(self, target_hash: str, dst: str) -> bool:
        return self.download_meta_file(target_hash, TESTS_FILE, dst)

    def download_meta_file(self, target_hash: str, src: str, dst: str) -> bool:
        src_path = join(self.targets_dir, target_hash, src)
        if not isfile(src_path):
            return False
        shutil.copyfile(src_path, dst)
        return True

    def download_artifacts(self, artifacts_hashes: Dict[str, int], dst: str):
        for artifact_hash in artifacts_hashes.keys():
            file_path = join(self.artifacts_dir, artifact_hash)
            if not isfile(file_path):
                return False
            shutil.copyfile(join(self.artifacts_dir, artifact_hash),
                            join(dst, artifact_hash))
        return True

    def create_target_cache(self, target_hash: str):
        if not isdir(join(self.targets_dir, target_hash)):
            os.mkdir(join(self.targets_dir, target_hash))

    def upload_summary(self, target_hash: str, src: str):
        shutil.copyfile(src,
                        join(self.targets_dir, target_hash, SUMMARY_FILE))

    def upload_artifacts_meta(self, target_hash: str, src: str):
        shutil.copyfile(src,
                        join(self.targets_dir, target_hash, ARTIFACTS_FILE))

    def upload_artifacts(self, artifacts_hashes: Dict[str, int], src: str):
        for artifact_hash in artifacts_hashes.keys():
            shutil.copyfile(join(src, artifact_hash),
                            join(self.artifacts_dir, artifact_hash))

    def upload_test_cache(self, target_hash: str, src: str):
        shutil.copyfile(src, join(self.targets_dir, target_hash, TESTS_FILE))
