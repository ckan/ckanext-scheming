from setuptools import setup, find_packages
import sys, os

version = '0.0.1'

setup(
    name='ckanext-customschema',
    version=version,
    description="Easy, sharable custom CKAN schemas",
    long_description="""
    """,
    classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    keywords='',
    author='Government of Canada',
    author_email='Michel.Gendron@statcan.gc.ca',
    url='',
    license='MIT',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    namespace_packages=['ckanext', 'ckanext.customschema'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        # -*- Extra requirements: -*-
    ],
    entry_points=\
    """
    [ckan.plugins]
    customschema=ckanext.customschema.plugins:CustomSchemaPlugin

    [paste.paster_command]
    canada=ckanext.customschema.commands:CustomSchemaCommand
    """,
)
