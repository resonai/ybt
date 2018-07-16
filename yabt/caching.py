# -*- coding: utf-8 -*-

# Copyright 2018 Resonai Ltd. All rights reserved
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
yabt Caching module
~~~~~~~~~~~~~~~~~~~

:author: Itamar Ostricher
"""


from .docker import get_image_name, handle_build_cache
from .graph import get_descendants
from .logging import make_logger
from .target_utils import ImageCachingBehavior


logger = make_logger(__name__)


class CachedDescendants(dict):
    """Utility dict-like class for holding mappings from target-name to set of
       descendants of that target.
    """

    def __init__(self, target_graph):
        self._target_graph = target_graph
        super().__init__()

    def get(self, key):
        """Return set of descendants of node named `key` in `target_graph`.

        Returns from cached dict if exists, otherwise compute over the graph
        and cache results in the dict.
        """
        if key not in self:
            self[key] = set(get_descendants(self._target_graph, key))
        return self[key]


def get_prebuilt_targets(build_context):
    """Return set of target names that are contained within cached base images

    These targets may be considered "pre-built", and skipped during build.
    """
    logger.info('Scanning for cached base images')
    # deps that are part of cached based images
    contained_deps = set()
    # deps that are needed by images that are going to be built,
    # but are not part of their base images
    required_deps = set()
    # mapping from target name to set of all its deps (descendants)
    cached_descendants = CachedDescendants(build_context.target_graph)

    for target_name, target in build_context.targets.items():
        if 'image_caching_behavior' not in target.props:
            continue
        image_name = get_image_name(target)
        image_tag = target.props.image_tag
        icb = ImageCachingBehavior(image_name, image_tag,
                                   target.props.image_caching_behavior)
        target.image_id = handle_build_cache(build_context.conf, image_name,
                                             image_tag, icb)
        if target.image_id:
            # mark deps of cached base image as "contained"
            image_deps = cached_descendants.get(target_name)
            contained_deps.update(image_deps)
        else:
            # mark deps of image that is going to be built
            # (and are not deps of its base image) as "required"
            image_deps = cached_descendants.get(target_name)
            base_image_deps = cached_descendants.get(target.props.base_image)
            required_deps.update(image_deps - base_image_deps)
    return contained_deps - required_deps
