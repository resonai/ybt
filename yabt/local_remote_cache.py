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
A remote cache implemented in local dick
~~~~~~~~~~~~~~~~~~~

:author: Dana Shamir
"""
from os.path import join, isdir

from yabt.remote_cache import RemoteCache

SUMMARY_FILE = 'summary.json'
ARTIFACTS_FILE = 'artifact.json'
TARGETS_DIR = 'targets'
ARTIFACTS_DIR = 'artifacts'


class LocalRemoteCache(RemoteCache):
    def __init__(self, directory):
        self.targets_dir = join(directory, TARGETS_DIR)
        self.artifacts_dir = join(directory, ARTIFACTS_DIR)

    def has_cache(self, target_hash: str):
        return isdir(join(self.targets_dir, target_hash))

    def get_summary(self, target_hash: str):
        with open(join(self.targets_dir, target_hash,
                       SUMMARY_FILE)) as summary:
            return summary.read()

    def get_artifacts_meta(self, target_hash: str):
        with open(join(self.targets_dir, target_hash,
                       ARTIFACTS_FILE)) as artifacts:
            return artifacts.read()

    def get_artifact(self, artifact_hash: str):
        with open(join(self.artifacts_dir, artifact_hash)) as artifact:
            return artifact.read()
