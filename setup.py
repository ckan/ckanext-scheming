from setuptools import setup, find_packages

version = '2.0.0'

setup(
    name='ckanext-scheming',
    version=version,
    description="Easy, sharable custom CKAN schemas",
    long_description="""
    This CKAN extension provides a way to configure and share metadata schemas using a
    YAML or JSON schema description. Custom validation and template snippets for editing
    and display are supported.

    Originally developed for the Government of Canada's custom metadata schema, part of
    https://github.com/open-data/ckanext-canada
    """,
    classifiers=[],  # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    keywords='',
    author='Ian Ward',
    author_email='ian@excess.org',
    url='https://github.com/ckan/ckanext-scheming',
    license='MIT',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    namespace_packages=['ckanext'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[],
    entry_points="""
    [ckan.plugins]
    scheming_datasets=ckanext.scheming.plugins:SchemingDatasetsPlugin
    scheming_groups=ckanext.scheming.plugins:SchemingGroupsPlugin
    scheming_organizations=ckanext.scheming.plugins:SchemingOrganizationsPlugin
    scheming_test_subclass=ckanext.scheming.tests.plugins:SchemingTestSubclass
    scheming_test_plugin=ckanext.scheming.tests.plugins:SchemingTestSchemaPlugin
    [babel.extractors]
    ckan = ckan.lib.extract:extract_ckan
    """,
    message_extractors={
        'ckanext': [
            ('**.py', 'python', None),
            ('**.js', 'javascript', None),
            ('**/templates/**.html', 'ckan', None),
        ],
    }
)
