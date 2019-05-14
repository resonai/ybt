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
A global cache implemented with google cloud storage
~~~~~~~~~~~~~~~~~~~

:author: Dana Shamir
"""

from google.cloud import storage
from os.path import join
from typing import List

from .global_cache import GlobalCache
from .logging import make_logger

SUMMARY_FILE = 'summary.json'
ARTIFACTS_FILE = 'artifact.json'
TARGETS_DIR = 'targets'
ARTIFACTS_DIR = 'artifacts'


logger = make_logger(__name__)


class GSGlobalCache(GlobalCache):
    def __init__(self, gce_project, bucket, directory=None):
        self.gce_project = gce_project
        self.bucket_name = bucket
        self.targets_dir = join(directory, TARGETS_DIR) if directory else \
            TARGETS_DIR
        self.artifacts_dir = join(directory, ARTIFACTS_DIR) if directory \
            else ARTIFACTS_DIR
        self.storage_client = None
        self.bucket = None

    def _create_client(self):
        if not self.storage_client:
            self.storage_client = storage.Client(self.gce_project)
        if not self.bucket:
            self.bucket = self.storage_client.get_bucket(self.bucket_name)

    def has_cache(self, target_hash: str):
        self._create_client()
        return self.bucket.blob(join(self.targets_dir, target_hash,
                                     SUMMARY_FILE)).exists()

    def download_summary(self, target_hash: str, dst: str):
        self._create_client()
        self.bucket.blob(join(self.targets_dir, target_hash,
                              SUMMARY_FILE)).download_to_filename(dst)

    def download_artifacts_meta(self, target_hash: str, dst: str):
        self._create_client()
        self.bucket.blob(join(self.targets_dir, target_hash,
                              ARTIFACTS_FILE)).download_to_filename(dst)

    def download_artifacts(self, artifacts_hashes: List[str], dst: str):
        self._create_client()
        if artifacts_hashes:
            # TODO(Dana): make this work in batch.
            # see https://github.com/googleapis/google-cloud-python/issues/3139
            for artifact_hash in artifacts_hashes:
                self.bucket.blob(join(self.artifacts_dir, artifact_hash))\
                    .download_to_filename(join(dst, artifact_hash))

    def create_target_cache(self, target_hash: str):
        pass

    def upload_summary(self, target_hash: str, src: str):
        self._create_client()
        self.bucket.blob(join(self.targets_dir, target_hash, SUMMARY_FILE))\
            .upload_from_filename(src)

    def upload_artifacts_meta(self, target_hash: str, src: str):
        self._create_client()
        self.bucket.blob(join(self.targets_dir, target_hash, ARTIFACTS_FILE))\
            .upload_from_filename(src)

    def upload_artifacts(self, artifacts_hashes: List[str], src: str):
        self._create_client()
        if artifacts_hashes:
            # TODO(Dana): make this work in batch
            for artifact_hash in artifacts_hashes:
                self.bucket.blob(join(self.artifacts_dir, artifact_hash))\
                    .upload_from_filename(join(src, artifact_hash))
