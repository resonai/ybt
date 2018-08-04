[![Travis CI status](https://travis-ci.org/resonai/ybt.svg?branch=master)](https://travis-ci.org/resonai/ybt)
[![AppVeyor CI status](https://ci.appveyor.com/api/projects/status/12kdeqf4u0egjwq5/branch/master?svg=true)](https://ci.appveyor.com/project/itamaro/ybt)

YaBT: Yet another Build Tool
============================

## Install

Requires Python 3.4 or above, so make sure you have it (`type -P python3 && python3 -V`).

```sh
sudo apt-get install -y python3-dev python3-pip
sudo pip3 install --upgrade pip
sudo pip3 install ybt
```

To configure bash tab-completion, add the following line to your `.bashrc`:

```sh
eval "$(register-python-argcomplete ybt)"
```

## Development

Requires Python 3.4 or above, so make sure you have it (`type -P python3 && python3 -V`).

Recommended with [virtualenvwrapper](http://virtualenvwrapper.readthedocs.org).

Initial virtualenv setup with virtualenvwrapper (when no virtualenv is active, run `deactivate` to make sure):

```sh
sudo apt-get install -y python3-dev python3-pip
mkvirtualenv --python="$( type -P python3 )" yabt
cd $WORKON_HOME/yabt
git clone git@github.com:resonai/ybt.git
cd ybt
# install development requirements
pip install -r requirements.txt
# install YaBT itself in local dev mode (in the virtualenv)
pip install -e .
```

You should be good to go now.

Try by running unit tests or manual test cases:

```sh
workon yabt
cd $WORKON_HOME/yabt/yabt
# Run unit tests:
make test
# Some manual tests:
cd tests/dag
ybt tree
ybt build
cd ../simple
ybt tree
# this one requires a running Docker engine,
# and the current user to be a member of the docker group
ybt build
```
