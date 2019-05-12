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
import itertools
import json
from os import makedirs
from os.path import isdir, isfile, join, relpath, split
import shutil
from time import time

from ostrich.utils.text import get_safe_path

from .artifact import ArtifactType as AT
from .config import Config
from .docker import get_image_name, handle_build_cache, tag_docker_image
from .graph import get_descendants
from .logging import make_logger
from .target_utils import ImageCachingBehavior, Target
from .utils import hash_tree, rmnode, rmtree


logger = make_logger(__name__)

_NO_CACHE_TYPES = frozenset((AT.app, AT.docker_image))
MAX_FAILS_FROM_GLOBAL = 5


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
            contained_deps.add(target.name)
        else:
            # mark deps of image that is going to be built
            # (and are not deps of its base image) as "required"
            image_deps = cached_descendants.get(target_name)
            base_image_deps = cached_descendants.get(target.props.base_image)
            required_deps.update(image_deps - base_image_deps)
    return contained_deps - required_deps


def write_summary(summary: dict, cache_dir: str):
    """Write the `summary` JSON to `cache_dir`.

    Updated the accessed timestamp to now before writing.
    """
    # update the summary last-accessed timestamp
    summary['accessed'] = time()
    with open(join(cache_dir, 'summary.json'), 'w') as summary_file:
        summary_file.write(json.dumps(summary, indent=4, sort_keys=True))


def load_target_from_global_cache(target: Target, build_context) -> bool:
    target_hash = target.hash(build_context)
    if not build_context.global_cache.has_cache(target_hash):
        return False
    cache_dir = build_context.conf.get_cache_dir(target, build_context)
    makedirs(cache_dir, exist_ok=True)
    build_context.global_cache.download_summary(
        target_hash, join(cache_dir, 'summary.json'))
    build_context.global_cache.download_artifacts_meta(
        target_hash, join(cache_dir, 'artifacts.json'))
    with open(join(cache_dir, 'artifacts.json'), 'r') as artifacts_meta_file:
        artifacts_desc = json.load(artifacts_meta_file)
    makedirs(build_context.conf.get_artifacts_cache_dir(), exist_ok=True)
    build_context.global_cache.download_artifacts(
        get_artifacts_hashes(artifacts_desc),
        build_context.conf.get_artifacts_cache_dir())
    return True


def get_artifacts_hashes(artifacts_desc):
    return [artifact['hash'] for artifact
            in itertools.chain(*artifacts_desc.values())
            if 'hash' in artifact and artifact['hash'] is not None]


def load_target_from_cache(target: Target, build_context) -> (bool, bool):
    """Load `target` from build cache, restoring cached artifacts & summary.
       Return (build_cached, test_cached) tuple.

    `build_cached` is True if target restored successfully.
    `test_cached` is True if build is cached and test_time metadata is valid.
    """
    # TODO(Dana): support partially deleted cache
    cache_dir = build_context.conf.get_cache_dir(target, build_context)
    if not isdir(cache_dir):
        logger.debug('No cache dir found for target {}', target.name)
        has_global_cache = False
        if build_context.global_cache and \
            build_context.conf.download_from_global_cache and \
                build_context.global_cache_failures < MAX_FAILS_FROM_GLOBAL:
            logger.info('trying to load target {} from global cache'
                        .format(target.name))
            try:
                has_global_cache = load_target_from_global_cache(
                    target, build_context)
            except Exception as e:
                logger.warning('an error occurred while trying to download '
                               'target {} from global cache'
                               .format(target.name))
                logger.warning(str(e))
                build_context.global_cache_failures += 1
        if not has_global_cache:
            return False, False
    # read summary file and restore relevant fields into target
    with open(join(cache_dir, 'summary.json'), 'r') as summary_file:
        summary = json.loads(summary_file.read())
    for field in ('build_time', 'test_time', 'created', 'accessed'):
        target.summary[field] = summary.get(field)
    # compare artifacts hash
    if (hash_tree(join(cache_dir, 'artifacts.json')) !=
            summary.get('artifacts_hash', 'no hash')):
        return False, False
    # read cached artifacts metadata
    with open(join(cache_dir, 'artifacts.json'), 'r') as artifacts_meta_file:
        artifact_desc = json.loads(artifacts_meta_file.read())
    # restore all artifacts
    for type_name, artifact_list in artifact_desc.items():
        artifact_type = getattr(AT, type_name)
        for artifact in artifact_list:
            # restore artifact to its expected src path
            if artifact_type not in _NO_CACHE_TYPES:
                if not restore_artifact(
                        artifact['src'], artifact['hash'], build_context.conf):
                    target.artifacts.reset()
                    return False, False
            if artifact_type in (AT.docker_image,):
                # "restore" docker image from local registry
                image_id = artifact['src']
                image_full_name = artifact['dst']
                try:
                    tag_docker_image(image_id, image_full_name)
                except:
                    logger.debug('Docker image with ID {} not found locally',
                                 image_id)
                    target.artifacts.reset()
                    return False, False
                target.image_id = image_id
            target.artifacts.add(
                artifact_type, artifact['src'], artifact['dst'])
    write_summary(summary, cache_dir)
    # check that the testing cache exists.
    if not isfile(join(cache_dir, 'tested.json')):
        logger.debug('No testing cache found for target {}', target.name)
        return True, False
    # read the testing cache.
    with open(join(cache_dir, 'tested.json'), 'r') as tested_file:
        target.tested = json.loads(tested_file.read())
        test_key = target.test_hash(build_context)
        return True, (target.tested.get(test_key) is not None)


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


def restore_artifact(src_path: str, artifact_hash: str, conf: Config):
    """Restore the artifact whose hash is `artifact_hash` to `src_path`.

    Return True if cached artifact is found, valid, and restored successfully.
    Otherwise return False.
    """
    cache_dir = conf.get_artifacts_cache_dir()
    if not isdir(cache_dir):
        return False
    cached_artifact_path = join(cache_dir, artifact_hash)
    if isfile(cached_artifact_path) or isdir(cached_artifact_path):
        # verify cached item hash matches expected hash
        actual_hash = hash_tree(cached_artifact_path)
        if actual_hash != artifact_hash:
            logger.warning(
                'Cached artifact {} expected hash {} != actual hash {}',
                src_path, artifact_hash, actual_hash)
            rmnode(cached_artifact_path)
            return False
        # if something exists in src_path, check if it matches the cached item
        abs_src_path = join(conf.project_root, src_path)
        if isfile(abs_src_path) or isdir(abs_src_path):
            existing_hash = hash_tree(src_path)
            if existing_hash == artifact_hash:
                logger.debug('Existing artifact {} matches cached hash {}',
                             src_path, artifact_hash)
                return True
            logger.debug('Replacing existing artifact {} with cached one',
                         src_path)
            rmnode(abs_src_path)
        logger.debug('Restoring cached artifact {} to {}',
                     artifact_hash, src_path)
        shutil.copy(cached_artifact_path, abs_src_path)
        return True
    logger.debug('No cached artifact for {} with hash {}',
                 src_path, artifact_hash)
    return False


def save_target_in_global_cache(target: Target, build_context, cache_dir,
                                artifacts_desc):
    target_hash = target.hash(build_context)
    build_context.global_cache.create_target_cache(target_hash)
    build_context.global_cache.upload_summary(target_hash,
                                              join(cache_dir, 'summary.json'))
    build_context.global_cache.upload_artifacts_meta(
        target_hash, join(cache_dir, 'artifacts.json'))
    build_context.global_cache.upload_artifacts(
        get_artifacts_hashes(artifacts_desc),
        build_context.conf.get_artifacts_cache_dir())


def save_target_in_cache(target: Target, build_context):
    """Save `target` to build cache for future reuse.

    The target hash is used to determine its cache location,
    where the target metadata and artifacts metadata are seriazlied to JSON.
    In addition, relevant artifacts produced by the target are copied under
    the artifacts cache dir by their content hash.

    TODO: pruning policy to limit cache size.
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
        if artifact_type in (AT.docker_image,):
            continue
        for dst_path, src_path in artifact_map.items():
            artifact_hashes[dst_path] = hash_tree(src_path)
            # not caching "app" artifacts, since they're part
            # of the source tree
            if artifact_type not in _NO_CACHE_TYPES:
                copy_artifact(src_path, artifact_hashes[dst_path],
                              build_context.conf)
    # serialize target artifacts metadata + hashes
    artifacts_desc = {
        artifact_type.name:
        [{'dst': dst_path, 'src': src_path,
          'hash': artifact_hashes.get(dst_path)}
         for dst_path, src_path in artifact_map.items()]
        for artifact_type, artifact_map in artifacts.items()
    }
    with open(join(cache_dir, 'artifacts.json'), 'w') as artifacts_meta_file:
        artifacts_meta_file.write(json.dumps(artifacts_desc, indent=4,
                                             sort_keys=True))
    # copying the summary dict so I can modify it without mutating the target
    summary = dict(target.summary)
    summary['name'] = target.name
    summary['artifacts_hash'] = hash_tree(join(cache_dir, 'artifacts.json'))
    if summary.get('created') is None:
        summary['created'] = time()
    write_summary(summary, cache_dir)

    if build_context.global_cache and \
        build_context.conf.upload_to_global_cache and \
            build_context.global_cache_failures < MAX_FAILS_FROM_GLOBAL:
        try:
            save_target_in_global_cache(target, build_context, cache_dir,
                                        artifacts_desc)
        except Exception as e:
            logger.warning('an error occurred while trying to upload '
                           'target {} to global cache'
                           .format(target.name))
            logger.warning(str(e))
            build_context.global_cache_failures += 1


def save_test_in_cache(target: Target, build_context) -> bool:
    """Save `target` testing to build cache for future reuse.

    The target hash is used to determine its cache location,
    where the target testing information is seriazlied to JSON.
    """
    if not target.tested:
        return True
    cache_dir = build_context.conf.get_cache_dir(target, build_context)
    if not isdir(cache_dir):
        logger.debug('Cannot cache test {} - build cache is missing',
                     target.name)
        return False
    with open(join(cache_dir, 'tested.json'), 'w') as tested_file:
        tested_file.write(json.dumps(target.tested, indent=4, sort_keys=True))
    return True
