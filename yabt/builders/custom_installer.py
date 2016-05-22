# -*- coding: utf-8 -*-

# Copyright 2016 Yowza Ltd. All rights reserved
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

# pylint: disable=invalid-name, unused-argument

"""
yabt Custom Installer Builder
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:author: Itamar Ostricher
"""


from collections import namedtuple
import os
from os.path import basename, isfile, join, relpath, splitext
import shutil
import tarfile
from urllib.parse import urlparse
from zipfile import ZipFile

import git
from git import InvalidGitRepositoryError, NoSuchPathError
import requests

from ..extend import (
    PropType as PT, register_build_func, register_builder_sig,
    register_manipulate_target_hook)
from ..logging import make_logger
from ..target_utils import split_name


logger = make_logger(__name__)


register_builder_sig(
    'CustomInstaller',
    [('uri', PT.str),
     ('script', PT.File),
     ('local_data', PT.FileList, None),
     ('deps', PT.TargetList, None),
     ('uri_type', PT.str, None),
     ])


CustomInstaller = namedtuple('CustomInstaller',
                             ['name', 'package', 'install_script'])


KNOWN_ARCHIVES = frozenset(('.gz', '.bz2', '.tgz', '.zip'))


def guess_uri_type(uri: str, hint: str=None):
    """Return a guess for the URI type based on the URI string `uri`.

    If `hint` is given, it is assumed to be the correct type.
    Otherwise, the URI is inspected using urlparse, and we try to guess
    whether it's a remote Git repository, a remote downloadable archive,
    or a local-only data.
    """
    # TODO(itamar): do this better
    if hint:
        return hint
    norm_uri = uri.lower()
    parsed_uri = urlparse(norm_uri)
    if parsed_uri.path.endswith('.git'):
        return 'git'
    if parsed_uri.scheme in ('http', 'https'):
        ext = splitext(parsed_uri.path)[-1]
        if ext in KNOWN_ARCHIVES:
            return 'archive'
        return 'single'
    return 'local'


def gitfilter(tarinfo):
    """Filter function for tar.add, to filter out git internal stuff."""
    if basename(tarinfo.name) in ['.git', '.gitignore']:
        return None
    return tarinfo


def make_tar(target):
    """Return an open tar object, for writing compressed gz archive."""
    return tarfile.open(target.props.installer_desc.package, 'w:gz',
                        dereference=True)


def git_handler(unused_build_context, target, package_dir):
    """Handle remote Git repository URI.

    Clone the repository under the private builder workspace (unless already
    cloned), and add it to the package tar (filtering out git internals).

    TODO(itamar): Support branches / tags / specific commit hashes
    TODO(itamar): Support updating a cloned repository
    TODO(itamar): Handle submodules?
    TODO(itamar): Handle force pulls?
    """
    target_name = split_name(target.name)
    # clone the repository under a private builder workspace
    try:
        repo = git.Repo(package_dir)
    except (InvalidGitRepositoryError, NoSuchPathError):
        repo = git.Repo.clone_from(target.props.uri, package_dir)
    assert repo.working_tree_dir == package_dir

    tar = make_tar(target)
    tar.add(package_dir, arcname=target_name, filter=gitfilter)
    return tar


def fetch_url(url, dest, parent_to_remove_before_fetch):
    """Helper function to fetch a file from a URL."""
    if isfile(dest):
        logger.debug('File {} is cached', dest)
    else:
        logger.debug('Downloading file {} from {}', dest, url)
        try:
            shutil.rmtree(parent_to_remove_before_fetch)
        except FileNotFoundError:
            pass
        os.makedirs(parent_to_remove_before_fetch)
        # TODO(itamar): Better downloading (multi-process-multi-threaded?)
        # Consider offloading this to a "standalone app" invoked with Docker
        resp = requests.get(url, stream=True)
        with open(dest, 'wb') as fetch_file:
            for chunk in resp.iter_content(chunk_size=32 * 1024):
                fetch_file.write(chunk)


def archive_handler(unused_build_context, target, package_dir):
    """Handle remote downloadable archive URI.

    Download the archive and cache it under the private builer workspace
    (unless already downloaded), extract it, and add the content to the
    package tar.

    TODO(itamar): Support re-downloading if remote changed compared to local.
    TODO(itamar): Support more archive formats (currently only tarballs).
    """
    package_dest = join(package_dir, basename(urlparse(target.props.uri).path))
    package_content_dir = join(package_dir, 'content')
    fetch_url(target.props.uri, package_dest, package_dir)

    # TODO(itamar): Avoid repetition of splitting extension here and above
    # TODO(itamar): Don't use `extractall` on potentially untrsuted archives
    ext = splitext(package_dest)[-1].lower()
    if ext in ('.gz', '.bz2', '.tgz'):
        with tarfile.open(package_dest, 'r:*') as tar:
            tar.extractall(package_content_dir)
    elif ext in ('.zip',):
        with ZipFile(package_dest, 'r') as zipf:
            zipf.extractall(package_content_dir)
    else:
        raise ValueError('Unsupported extension {}'.format(ext))

    tar = make_tar(target)
    tar.add(package_content_dir, arcname=split_name(target.name))
    return tar


def fetch_file_handler(unused_build_context, target, package_dir):
    """Handle remote downloadable file URI.

    Download the file and cache it under the private builer workspace
    (unless already downloaded), and add it to the package tar.

    TODO(itamar): Support re-downloading if remote changed compared to local.
    """
    fetch_url(
        target.props.uri,
        join(package_dir, basename(urlparse(target.props.uri).path)),
        package_dir)

    tar = make_tar(target)
    tar.add(package_dir, arcname=split_name(target.name))
    return tar


def local_handler(build_context, target, package_dir):
    return make_tar(target)


@register_build_func('CustomInstaller')
def custom_installer_builder(build_context, target):
    # TODO(itamar): Handle cached package invalidation
    print('Fetch and cache custom installer package', target)
    workspace_dir = build_context.get_workspace('CustomInstaller', target.name)
    target_name = split_name(target.name)
    script_name = basename(target.props.script)
    package_tarball = '{}.tar.gz'.format(join(workspace_dir, target_name))
    target.props.installer_desc = CustomInstaller(
        name=target_name, package=package_tarball, install_script=script_name)
    if isfile(package_tarball):
        logger.debug('Custom installer package {} is cached', package_tarball)
        return

    logger.debug('Making custom installer package {}', package_tarball)
    handlers = {
        'git': git_handler,
        'archive': archive_handler,
        'single': fetch_file_handler,
        'local': local_handler,
    }
    uri_type = guess_uri_type(target.props.uri, target.props.uri_type)
    logger.debug('CustomInstaller URI {} typed guessed to be {}',
                 target.props.uri, uri_type)
    tar = handlers[uri_type](build_context, target,
                             join(workspace_dir, target_name))
    # Add local data to installer package, if specified
    for local_node in target.props.local_data:
        tar.add(join(build_context.conf.project_root, local_node),
                arcname=join(target_name, local_node))
    # Add the install script to the installer package
    tar.add(join(build_context.conf.project_root, target.props.script),
            arcname=join(target_name,
                         target.props.installer_desc.install_script))
    tar.close()


@register_manipulate_target_hook('CustomInstaller')
def custom_installer_manipulate_target(build_context, target):
    target.tags.add('custom-installer')
