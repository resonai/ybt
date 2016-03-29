# -*- coding: utf-8 -*-

"""
yabt setup

:copyright: (c) 2016 Yowza by Itamar Ostricher
:license: MIT, see LICENSE for more details.
"""


from setuptools import setup, find_packages
import yabt

setup(
    name='yabt',
    version=yabt.__version__,
    author=yabt.__author__,
    author_email='yabt@ostricher.com',
    url='https://yabt.ostrich.io/',
    description=yabt.__oneliner__,
    packages=['yabt'],
    entry_points={
        'console_scripts': [
            'ybt = yabt.yabt:main'
        ],
        'yabt.builders': [
            'AliasBuilder = yabt.builders.alias:AliasBuilder',
            'DockerImageBuilder = yabt.builders.docker:DockerImageBuilder',
            'DockerRegistryBuilder = yabt.builders.docker:DockerRegistryBuilder',
            'PipBuilder = yabt.builders.pip:PipBuilder',
            'PyLibBuilder = yabt.builders.pylib:PyLibBuilder',

            'DepTesterBuilder = yabt.builders.fortests:DepTesterBuilder',
        ],
    },
    install_requires=[
        'argcomplete',
        'colorama',
        'ConfigArgParse',
        'networkx',
        'ostrichlib',
    ],
    setup_requires=['pytest-runner'],
    extras_require={
        'test': ['pytest', 'pytest-cov', 'pytest-pep8'],
    },
    zip_safe=True,
    license='MIT',
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Development Status :: 1 - Planning',
        'Intended Audience :: Developers',
        'Environment :: Console',
        'License :: OSI Approved :: MIT License',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: POSIX :: Linux',
        'Topic :: Software Development :: Build Tools',
    ]
)
