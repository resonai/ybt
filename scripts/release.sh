#!/bin/bash
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

if ! git diff-index --quiet HEAD --; then
    echo "ERROR: Found local changes - can't release."
    exit 1
fi

if [ $( git symbolic-ref HEAD ) != "refs/heads/master" ]; then
    echo "ERROR: Not on 'master' branch. Please switch to master first."
    exit 1
fi

CUR_VER="$( python -c 'import yabt; print(yabt.__version__)' )"
echo "Current version number is $CUR_VER"
AUTO_NEW_VER="$( ./scripts/bumpver.py )"
read -p "New version number ($AUTO_NEW_VER): " USER_NEW_VER
NEW_VER=${USER_NEW_VER:-$AUTO_NEW_VER}
if ! python -c 'from distutils.version import LooseVersion as LV; import sys; \
        sys.exit(int(LV("'$NEW_VER'") <= LV("'$CUR_VER'")))'; then
    echo "ERROR: New version must be greater than old version!"
    exit 1
fi
sed -i.bak "s/__version__ = .*/__version__ = '$NEW_VER'/" yabt/__init__.py
rm yabt/__init__.py.bak
echo "Bumped version number to $NEW_VER"
git add yabt/__init__.py
git commit -m "Bump version $NEW_VER"
git tag "v$NEW_VER"
git push origin master
git push origin "v$NEW_VER"
