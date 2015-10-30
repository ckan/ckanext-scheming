#!/usr/bin/env python
# encoding: utf-8
__all__ = (
    'SchemingException',
    'LoaderError'
)


class SchemingException(Exception):
    pass


class LoaderError(Exception):
    """
    Raised when an error occurs while attempting to load a
    schema.
    """
