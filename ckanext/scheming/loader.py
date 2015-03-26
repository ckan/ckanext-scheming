"""
Load either yaml or json, based on the name of the resource
"""

import json

try:
    import yaml
except ImportError:
    yaml = None

def load(f):
    if is_yaml(f.name):
        return yaml.load(f)
    return json.load(f)

def loads(s, url):
    if is_yaml(url):
        return yaml.load(s)
    return json.loads(s)

def is_yaml(n):
    return n[-5:].lower() == '.yaml' or n[-4:] == '.yml'
