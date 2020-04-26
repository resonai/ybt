# -*- coding: utf-8 -*-

# Copyright 2016 Resonai Ltd. All rights reserved
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
from os.path import basename, isdir, join, relpath, splitext
import shutil
import tarfile
from urllib.parse import urlparse
from zipfile import ZipFile

import git
from git import InvalidGitRepositoryError, NoSuchPathError
import requests

from ..artifact import ArtifactType as AT
from ..extend import (
    PropType as PT, register_build_func, register_builder_sig,
    register_manipulate_target_hook)
from ..logging import make_logger
from ..target_utils import split_name
from ..utils import rmtree, yprint


logger = make_logger(__name__)


register_builder_sig(
    'CustomInstaller',
    [('script', PT.File),
     ('fetch', PT.list, None),
     ('local_data', PT.FileList, None),
     ('script_args', PT.StrList, None),
     ('uri', PT.str, None),  # deprecated
     ('uri_type', PT.str, None),  # deprecated
     ])


CustomInstaller = namedtuple('CustomInstaller',
                             ['name', 'package', 'install_script'])
FetchDesc = namedtuple('FetchDesc', ['uri', 'type', 'name'])


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


def git_handler(unused_build_context, target, fetch, package_dir, tar):
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
    repo_dir = join(package_dir, fetch.name) if fetch.name else package_dir
    try:
        repo = git.Repo(repo_dir)
    except (InvalidGitRepositoryError, NoSuchPathError):
        repo = git.Repo.clone_from(fetch.uri, repo_dir)
    assert repo.working_tree_dir == repo_dir
    tar.add(package_dir, arcname=target_name, filter=gitfilter)


def fetch_url(url, dest, parent_to_remove_before_fetch):
    """Helper function to fetch a file from a URL."""
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


def archive_handler(unused_build_context, target, fetch, package_dir, tar):
    """Handle remote downloadable archive URI.

    Download the archive and cache it under the private builer workspace
    (unless already downloaded), extract it, and add the content to the
    package tar.

    TODO(itamar): Support re-downloading if remote changed compared to local.
    TODO(itamar): Support more archive formats (currently only tarballs).
    """
    package_dest = join(package_dir, basename(urlparse(fetch.uri).path))
    package_content_dir = join(package_dir, 'content')
    extract_dir = (join(package_content_dir, fetch.name)
                   if fetch.name else package_content_dir)
    fetch_url(fetch.uri, package_dest, package_dir)

    # TODO(itamar): Avoid repetition of splitting extension here and above
    # TODO(itamar): Don't use `extractall` on potentially untrsuted archives
    ext = splitext(package_dest)[-1].lower()
    if ext in ('.gz', '.bz2', '.tgz'):
        with tarfile.open(package_dest, 'r:*') as src_tar:
            src_tar.extractall(extract_dir)
    elif ext in ('.zip',):
        with ZipFile(package_dest, 'r') as zipf:
            zipf.extractall(extract_dir)
    else:
        raise ValueError('Unsupported extension {}'.format(ext))
    tar.add(package_content_dir, arcname=split_name(target.name))


def fetch_file_handler(unused_build_context, target, fetch, package_dir, tar):
    """Handle remote downloadable file URI.

    Download the file and cache it under the private builer workspace
    (unless already downloaded), and add it to the package tar.

    TODO(itamar): Support re-downloading if remote changed compared to local.
    """
    dl_dir = join(package_dir, fetch.name) if fetch.name else package_dir
    fetch_url(fetch.uri,
              join(dl_dir, basename(urlparse(fetch.uri).path)),
              dl_dir)
    tar.add(package_dir, arcname=split_name(target.name))


def local_handler(build_context, target, fetch, package_dir, tar):
    pass


def get_installer_desc(build_context, target) -> tuple:
    """Return a target_name, script, args, package_tarball
       tuple for `target`"""
    workspace_dir = build_context.get_workspace('CustomInstaller', target.name)
    target_name = split_name(target.name)
    script_name = basename(target.props.script)
    package_tarball = '{}.tar.gz'.format(join(workspace_dir, target_name))
    return target_name, script_name, target.props.script_args, package_tarball


@register_build_func('CustomInstaller')
def custom_installer_builder(build_context, target):
    yprint(build_context.conf, 'Fetch custom installer package', target)
    if target.props.fetch and (target.props.uri or target.props.uri_type):
        raise AttributeError(
            '{}: `uri` & `uri_type` are deprecated - use `fetch` exclusively'
            .format(target.name))

    workspace_dir = build_context.get_workspace('CustomInstaller', target.name)
    # cleanup workspace
    if isdir(workspace_dir):
        rmtree(workspace_dir)
    os.makedirs(workspace_dir)

    target_name, script_name, _, package_tarball = get_installer_desc(
        build_context, target)

    logger.debug('Making custom installer package {}', package_tarball)
    handlers = {
        'git': git_handler,
        'archive': archive_handler,
        'single': fetch_file_handler,
        'local': local_handler,
    }

    def to_fetch_desc(fetch_arg):
        if isinstance(fetch_arg, dict):
            return FetchDesc(
                uri=fetch_arg['uri'], type=fetch_arg.get('type', None),
                name=fetch_arg.get('name', None))
        assert isinstance(fetch_arg, str)
        return FetchDesc(uri=fetch_arg, type=None, name='')

    fetches = ([to_fetch_desc(fetch) for fetch in target.props.fetch]
               if target.props.fetch
               else [FetchDesc(name='', uri=target.props.uri,
                               type=target.props.uri_type)])
    if len(fetches) > 1 and any(fetch.name is None for fetch in fetches):
        raise ValueError('{}: Implicit empty name not allowed with multiple '
                         'fetches. To fetch a URI under the top dir, '
                         'explicitly set the name to \'\''.format(target.name))
    used_names = set()
    for fetch in fetches:
        if fetch.name in used_names:
            raise ValueError('{}: Duplicate fetch name "{}"'.format(
                target.name, fetch.name))
        used_names.add(fetch.name)
    tar = tarfile.open(package_tarball, 'w:gz', dereference=True)
    for fetch in fetches:
        uri_type = guess_uri_type(fetch.uri, fetch.type)
        logger.debug('CustomInstaller URI {} typed guessed to be {}',
                     fetch.uri, uri_type)
        package_dir = join(workspace_dir, target_name,
                           fetch.name or '_unnamed_')
        handlers[uri_type](build_context, target, fetch, package_dir, tar)
    # Add local data to installer package, if specified
    for local_node in target.props.local_data:
        tar.add(join(build_context.conf.project_root, local_node),
                arcname=join(target_name, local_node))
    # Add the install script to the installer package
    tar.add(join(build_context.conf.project_root, target.props.script),
            arcname=join(target_name, script_name))
    tar.close()
    target.artifacts.add(
        AT.custom_installer,
        relpath(package_tarball, build_context.conf.project_root))


@register_manipulate_target_hook('CustomInstaller')
def custom_installer_manipulate_target(build_context, target):
    target.tags.add('custom-installer')
