=======================
YABT: Yaweza Build Tool
=======================

AKA: Yet Another Build Tool (the open source project).


Install
-------

Requires Python 3.4 or above, so make sure you have it (``type -P python3 && python3 -V``).

.. code-block:: shell
    sudo apt-get install -y python3-dev python3-pip
    sudo pip3 install --upgrade pip
    sudo pip3 install ybt


To configure bash tab-completion, add the following line to your `.bashrc`:

.. code-block:: shell
    eval "$(register-python-argcomplete ybt)"


Development
-----------

Requires Python 3.4 or above, so make sure you have it (``type -P python3 && python3 -V``).

Recommended with `virtualenvwrapper <http://virtualenvwrapper.readthedocs.org>`_.

Initial virtualenv setup with virtualenvwrapper
(when no virtualenv is active, run ``deactivate`` to make sure):

.. code-block:: shell
    sudo apt-get install -y python3-dev python3-pip
    mkvirtualenv --python="$(type -P python3)" yabt
    cd $WORKON_HOME/yabt
    git clone git@bitbucket.org:yowza3d/yabt.git
    cd yabt
    # install development requirements
    pip install -r requirements.txt
    # install YABT itself in local dev mode (in the virtualenv)
    pip install -e .


You should be good to go now.

Try by running unit tests or manual test cases:

.. code-block:: shell

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
