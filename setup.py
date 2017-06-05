#!/usr/bin/env python3

import sys
from os.path import abspath, dirname, join
from subprocess import PIPE, Popen

from setuptools import setup

CWD = dirname(abspath(__file__))


def version():
    """Get the current version according to the git repository."""
    p = Popen(['git', 'describe', '--tags', '--always'], stdout=PIPE, cwd=CWD)
    out = p.communicate()[0]
    if sys.version_info[0] > 2:
        out = out.decode()
    return out.strip()


def requires():
    """Parse the requirements.txt file and generate a requirements list."""
    with open(join(CWD, 'requirements.txt'), 'r') as fp:
        return fp.read().split()


setup(
    name='cacophony',
    version=version(),
    description='Cacophony dump Discord Bot',
    url='https://gitlab.com/ge0_/cacophony',
    licence='MIT',
    include_package_data=True,
    packages=[
        'bsol',
        'chattymarkov',
    ],
    install_requires=requires()
)
