#!/usr/bin/env python3

import ast
import re
from pathlib import Path

from setuptools import find_packages, setup


INSTALL_REQUIRES = [
    'discord.py==1.1.0',
    'click',
    'sqlalchemy',
    'pyaml'
]


def get_meta():
    """Get meta information from package init python file."""
    meta_re = re.compile(r'^__(?P<name>\w+?)__\s*=\s=*(?P<value>.+)$')
    meta_filepath = Path('src') / 'cacophony' / '__init__.py'
    meta = {}
    with open(meta_filepath) as meta_fileobj:
        for line in meta_fileobj:
            match = meta_re.match(line)
            if match is None:
                continue
            meta_name = match.group('name')
            meta_value = ast.literal_eval(match.group('value'))
            meta[meta_name] = meta_value
    return meta


META = get_meta()


setup(
    name=META['name'],
    version=META['version'],
    description=META['description'],
    author=META['author'],
    author_email=META['email'],
    url=META['uri'],
    package_dir={'': 'src'},
    packages=find_packages('src'),
    entry_points={
        'console_scripts': [
            'cacophony=cacophony.__main__:main',
        ],
    },
    license='MIT',
    install_requires=INSTALL_REQUIRES
)
