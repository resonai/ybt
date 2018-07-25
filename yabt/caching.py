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

TODO: implement also distributed caching
will require keeping track of which machine produced what, so it is possible
to rerun "cached" tests on machines with different hardware (for example).
"""

import json
from os import makedirs, remove
from os.path import isdir, isfile, join, relpath, split
import shutil

from ostrich.utils.text import get_safe_path

from .artifact import ArtifactType as AT
from .config import Config
from .docker import get_image_name, handle_build_cache
from .graph import get_descendants
from .logging import make_logger
from .target_utils import ImageCachingBehavior, Target
from .utils import hash_tree, rmtree


logger = make_logger(__name__)

_NO_CACHE_TYPES = frozenset((AT.app,))


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


def copy_artifact(src_path: str, artifact_hash: str, conf: Config):
    """Copy the artifact at `src_path` with hash `artifact_hash` to artifacts
       cache dir.

    If an artifact already exists at that location, it is assumed to be
    identical (since it's based on hash), and the copy is skipped.

    TODO: pruning policy to limit cache size.
    """
    cache_dir = conf.get_artifacts_cache_dir()
    if not isdir(cache_dir):
        makedirs(cache_dir)
    cached_artifact_path = join(cache_dir, artifact_hash)
    if isfile(cached_artifact_path) or isdir(cached_artifact_path):
        logger.debug('Skipping copy of existing cached artifact {} -> {}',
                     src_path, cached_artifact_path)
        return
    abs_src_path = join(conf.project_root, src_path)
    logger.debug('Caching artifact {} under {}',
                 abs_src_path, cached_artifact_path)
    shutil.copy(abs_src_path, cached_artifact_path)


def save_target_in_cache(target: Target, build_context):
    """Save `target` to build cache for future reuse.

    The target hash is used to determine its cache location,
    where the target metadata and artifacts metadata are seriazlied to JSON.
    In addition, relevant artifacts produced by the target are copied under
    the artifacts cache dir by their content hash.

    TODO: pruning policy to limit cache size.
    TODO: add error checking on serialized metadata
    TODO: also write out "stats" (modified timestamp, last used timestamp,
          stdout/stderr of builder & tester, build time, test time)
    """
    cache_dir = build_context.conf.get_cache_dir(target, build_context)
    if isdir(cache_dir):
        rmtree(cache_dir)
    makedirs(cache_dir)
    logger.debug('Saving target metadata in cache under {}', cache_dir)
    # write target metadata
    with open(join(cache_dir, 'target.json'), 'w') as meta_file:
        meta_file.write(target.json(build_context))
    # copy artifacts to artifact cache by hash
    artifacts = target.artifacts.get_all()
    artifact_hashes = {}
    for artifact_type, artifact_map in artifacts.items():
        for dst_path, src_path in artifact_map.items():
            artifact_hashes[dst_path] = hash_tree(src_path)
            # not caching "app" artifacts, since they're part
            # of the source tree
            if artifact_type not in _NO_CACHE_TYPES:
                copy_artifact(src_path, artifact_hashes[dst_path],
                              build_context.conf)
    # serialize target artifacts metadata + hashes
    artifact_desc = {
        artifact_type.name:
        [{'dst': dst_path, 'src': src_path, 'hash': artifact_hashes[dst_path]}
         for dst_path, src_path in artifact_map.items()]
        for artifact_type, artifact_map in artifacts.items()
    }
    with open(join(cache_dir, 'artifacts.json'), 'w') as artifacts_meta_file:
        artifacts_meta_file.write(json.dumps(
            artifact_desc, indent=4, sort_keys=True))
