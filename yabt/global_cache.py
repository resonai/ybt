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
interface for a remote cache
~~~~~~~~~~~~~~~~~~~

:author: Dana Shamir
"""

from typing import List


class GlobalCache:
    """
    An interface for a remote cache
    """
    def has_cache(self, target_hash: str) -> bool:
        """
        returns True if the cache has a target matching the hash
        """
        raise NotImplemented('Method has_cache of class {} was not '
                             'implemented'.format(self.__class__.__name__))

    def download_summary(self, target_hash: str, dst: str):
        """
        Download the summary file of the target to `dst`
        """
        raise NotImplemented('Method download_summary of class {} was not '
                             'implemented'.format(self.__class__.__name__))

    def download_artifacts_meta(self, target_hash: str, dst: str):
        """
        Downloads the metadata about the artifcats cached for the target to
        `dst`.
        """
        raise NotImplemented(
            'Method download_artifacts_meta of class {} was not '
            'implemented'.format(self.__class__.__name__))

    def download_artifacts(self, artifacts_hashes: List[str], dst: str):
        """
        Downloads the artifacts to `dst`. In `dst` each artifact will be in a
        file named with its hash.
        """
        raise NotImplemented('Method download_artifacts of class {} was not '
                             'implemented'.format(self.__class__.__name__))

    def create_target_cache(self, target_hash: str):
        raise NotImplemented('Method create_target_cache of class {} was not '
                             'implemented'.format(self.__class__.__name__))

    def upload_summary(self, target_hash: str, src: str):
        """
        Upload summary file in `src` describing the target with the given hash
        """
        raise NotImplemented('Method upload_summary of class {} was not '
                             'implemented'.format(self.__class__.__name__))

    def upload_artifacts_meta(self, target_hash: str, src: str):
        """
        Upload the metadata file in `src` describing the artifcats cached for
        the target.
        """
        raise NotImplemented(
            'Method upload_artifacts_meta of class {} was not '
            'implemented'.format(self.__class__.__name__))

    def upload_artifacts(self, artifacts_hashes: List[str], src: str):
        """
        Upload the artifacts with given hashes in directory `src`.
        """
        raise NotImplemented('Method upload_artifacts of class {} was not '
                             'implemented'.format(self.__class__.__name__))