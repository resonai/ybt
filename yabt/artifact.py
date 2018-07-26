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
yabt artifacts module
~~~~~~~~~~~~~~~~~~~~~

:author: Itamar Ostricher
"""


from collections import defaultdict
from enum import Enum
from os.path import join

from .config import Config
from .utils import link_node


ArtifactType = Enum('ArtifactType', """app
                                       object
                                       binary
                                       gen_py
                                       gen_cc
                                       gen_h
                                       custom_installer
                                       docker_image
                                       """)


class ArtifactStore:
    """A class for keeping track of artifacts produced during build.

    Generally, the class tracks only *files* produced by *builders* during
    their build func execution.

    Supported artifact types:
    - "app"     An artifact that is just a copy of a file that exists under
                the project tree (not generated / compiled).
                Such artifacts will not be cached.
                When building Docker images, such artifacts are copied under
                the path /usr/src/app within the image.
    - "object"  A compiled object file that is needed by linking-builders, but
                not by other dependent targets, and is not copied to built
                Docker images. Object files are cached as outputs.
    - "binary"  A compiled executable binary file, that will be copied under
                the path /usr/src/bin in dependent Docker images.
                Binary files are cached as outputs.
    - "gen_py"  A generated Python file (e.g. from Proto's) that is used by
                dependent test targets and Docker images. It will be copied
                under the path /usr/src/gen. Cached as outputs.
    - "gen_cc"  A generated C/C++ source file (e.g. from Proto's) that is used
                only by directly dependent C++ builders (used to extend
                sources). Cached as outputs.
    - "gen_h"   A generated C/C++ header file (e.g. from Proto's) that is used
                by any dependent C++ builder (direct or indirect) to extend
                the target headers. Cached as ouputs.

    An artifact is added as a specific type, with a source path (pointing to
    the location of the artifact file relative to project root), and an
    optional destination path (if different from source path).
    """

    # Mapping from artifact type to sub-dir under /usr/src
    type_to_dir = {
        ArtifactType.app: 'app',
        ArtifactType.binary: 'bin',
        ArtifactType.gen_py: 'gen',
        ArtifactType.gen_cc: '',
        ArtifactType.gen_h: '',
    }

    def __init__(self):
        self._artifacts = defaultdict(dict)

    def add(self, artifact_type: ArtifactType, src_path: str,
            dst_path: str=None):
        """Add an artifact of type `artifact_type` at `src_path`.

        `src_path` should be the path of the file relative to project root.
        `dst_path`, if given, is the desired path of the artifact in dependent
        targets, relative to its base path (by type).
        """
        if dst_path is None:
            dst_path = src_path
        other_src_path = self._artifacts[artifact_type].setdefault(
            dst_path, src_path)
        if src_path != other_src_path:
            raise RuntimeError(
                '{} artifact with dest path {} exists with different src '
                'path: {} != {}'.format(artifact_type, dst_path, src_path,
                                        other_src_path))

    def extend(self, artifact_type: ArtifactType, src_paths: list):
        """Add all `src_paths` as artifact of type `artifact_type`."""
        for src_path in src_paths:
            self.add(artifact_type, src_path, src_path)

    def get(self, artifact_type: ArtifactType) -> dict:
        """Return artifacts dict of type `artifact_type`."""
        return self._artifacts[artifact_type]

    def get_all(self) -> dict:
        return self._artifacts

    def reset(self):
        """Clear internal artifacts store."""
        self._artifacts.clear()

    def link_types(self, base_dir: str, types: list, conf: Config) -> int:
        """Link all artifacts with types `types` under `base_dir` and return
           the number of linked artifacts."""
        num_linked = 0
        for kind in types:
            artifact_map = self._artifacts.get(kind)
            if not artifact_map:
                continue
            num_linked += self._link(join(base_dir, self.type_to_dir[kind]),
                                     artifact_map, conf)
        return num_linked

    def link_for_image(self, base_dir: str, conf: Config) -> int:
        """Link all artifacts required for a Docker image under `base_dir` and
           return the number of linked artifacts."""
        return self.link_types(
            base_dir,
            [ArtifactType.app, ArtifactType.binary, ArtifactType.gen_py],
            conf)

    def _link(self, base_dir: str, artifact_map: dict, conf: Config):
        """Link all artifacts in `artifact_map` under `base_dir` and return
           the number of artifacts linked."""
        num_linked = 0
        for dst, src in artifact_map.items():
            abs_src = join(conf.project_root, src)
            abs_dest = join(conf.project_root, base_dir, dst)
            link_node(abs_src, abs_dest)
            num_linked += 1
        return num_linked
