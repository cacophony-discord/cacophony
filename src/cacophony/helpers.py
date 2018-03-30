"""Cacophony helpers."""
import os

import yaml


def create_config_dir():
    """Create config directory in $HOME/.config"""
    os.makedirs(os.path.expanduser("~/.config/bsol"))


def load_yaml_file(filename):
    """Load a yaml file into a python data structure."""
    with open(filename) as stream:
        return yaml.load(stream, Loader=yaml.Loader)
