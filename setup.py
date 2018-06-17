# -*- coding: utf-8 -*-

"""
yabt setup

:copyright: (c) 2016 Resonai by Itamar Ostricher
:license: MIT, see LICENSE for more details.
"""


from setuptools import setup, find_packages
import yabt

setup(
    name='ybt',
    version=yabt.__version__,
    author=yabt.__author__,
    author_email='yabt@ostricher.com',
    url='https://yabt.ostrich.io/',
    description=yabt.__oneliner__,
    packages=find_packages(),
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'ybt = yabt.yabt:main'
        ],
        'yabt.builders': [
            'Alias = yabt.builders.alias',
            'AptPackage = yabt.builders.apt',
            'AptRepository = yabt.builders.apt',
            'CppApp = yabt.builders.cpp',
            'CustomInstaller = yabt.builders.custom_installer',
            'DockerImage = yabt.builders.docker',
            'ExtCommand = yabt.builders.extcommand',
            'ExtDockerImage = yabt.builders.docker',
            'FileGroup = yabt.builders.filegroup',
            'GemPackage = yabt.builders.ruby',
            'Grunt = yabt.builders.grunt',
            'NpmPackage = yabt.builders.nodejs',
            'PythonApp = yabt.builders.python',
            'PythonPackage = yabt.builders.python',
            'Python = yabt.builders.python',
            'TargetGroup = yabt.builders.targetgroup',
            'Proto = yabt.builders.proto',

            'DepTester = yabt.builders.fortests',
        ],
        'yabt.scm': [
            'git = yabt.scm_providers.git',
        ]
    },
    install_requires=[
        'argcomplete',
        'colorama',
        'ConfigArgParse',
        'GitPython',
        'munch',
        'networkx>=2.0',
        'ostrichlib',
        'requests>=2.18.0',
        'scandir',
    ],
    setup_requires=['pytest-runner'],
    extras_require={
        'test': ['pytest', 'pytest-cov', 'pytest-pep8'],
    },
    zip_safe=True,
    license='Apache License, Version 2.0',
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Environment :: Console',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: POSIX :: Linux',
        'Topic :: Software Development :: Build Tools',
    ]
)
