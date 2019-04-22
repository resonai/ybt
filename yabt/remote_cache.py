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


class RemoteCache:
    """
    An interface for a remote cache
    """
    def has_cache(self, target_hash: str) -> bool:
        """
        returns True if the cache has a target matching the hash
        """
        raise NotImplemented('Method has_cache of class {} was not '
                             'implemented'.format(self.__class__.__name__))

    def get_summary(self, target_hash: str, dst: str):
        """
        Download the summary file of the target to `dst`
        """
        raise NotImplemented('Method get_summary of class {} was not '
                             'implemented'.format(self.__class__.__name__))

    def get_artifacts_meta(self, target_hash: str, dst: str):
        """
        Downloads the metadata about the artifcats cached for the target to
        `dst`.
        """
        raise NotImplemented('Method get_artifacts_meta of class {} was not '
                             'implemented'.format(self.__class__.__name__))

    def get_artifacts(self, artifacts_hashes: List[dict], dst: str):
        """
        Downloads the artifacts to `dst`. In `dst` each artifact will be in a
        file named with its hash.
        """
        raise NotImplemented('Method get_artifacts of class {} was not '
                             'implemented'.format(self.__class__.__name__))
