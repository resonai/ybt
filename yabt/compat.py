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

"""
yabt Compatability module
~~~~~~~~~~~~~~~~~~~~~~~~~

:author: Itamar Ostricher
"""


# os.scandir, performant os.walk
try:
    # Python 3.5, use builtin implementation
    # https://docs.python.org/3/library/os.html#os.scandir
    from os import scandir, walk
except ImportError:
    # pre-Python 3.5, use third party package
    # https://pypi.python.org/pypi/scandir
    from scandir import scandir, walk
