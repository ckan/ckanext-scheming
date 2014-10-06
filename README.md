ckanext-scheming
================

This extension provides a way to configure and share
CKAN schemas using a JSON schema description. Custom
template snippets for editing and display are also supported.

[![Build Status](https://travis-ci.org/open-data/ckanext-scheming.svg?branch=master)](https://travis-ci.org/open-data/ckanext-scheming)
[![Coverage](https://img.shields.io/coveralls/open-data/ckanext-scheming.svg?branch=master)](https://coveralls.io/r/open-data/ckanext-scheming)


Requirements
============

This plugin relies on the scheming-support branch
of ckan, see: https://github.com/ckan/ckan/pull/1795


Configuration
=============

Set the schemas you want to use with configuration options:

```ini
ckan.plugins = scheming_datasets scheming_groups

#   module-path:file to schemas being used
scheming.dataset_schemas = ckanext.spatialx:spatialx_schema.json
                           ckanext.spatialx:spatialxy_schema.json
scheming.group_schemas = ckanext.spatialx:group_schema.json
scheming.organization_schemas = ckanext.spatialx:org_schema.json
#   will try to load "spatialx_schema.json" and "spatialxy_schema.json"
#   as dataset schemas and "group_schema.json" as a group schema and
#   "org_schema" as an organization schema, all from the directory
#   containing the ckanext.spatialx module code
#
#   URLs may also be used, e.g:
#
# scheming.dataset_schemas = http://example.com/spatialx_schema.json
```


Example dataset schemas
-----------------------

* [default dataset schema](ckanext/scheming/ckan_dataset.json)
* [camel photos schema](ckanext/scheming/camel_photos.json)

These schemas are included in ckanext-scheming and may be enabled
with e.g: `scheming.dataset_schemas = ckanext.scheming:camel_photos.json`



Fields
------


### `scheming_version`

Set to `1`. Future versions of ckanext-scheming may use a larger
number to indicate a change to the description JSON format.


### `dataset_type`, `group_type` or `organization_type`

These are the "type" fields stored in the dataset, group or organization.
For datasets it is used to set the URL for searching this type of dataset.

Normal datasets would be available under `/dataset`, but datasets with
the `camel_photos.json` schema above would appear under `/camel-photos` instead.

For organizations this field should be set to `"organization"` as some
parts of CKAN depend on this value not changing.


### `about_url`

`about_url` is a Link to human-readable information about this schema.
Its use is optional but highly recommended.


### `dataset_fields` and `resource_fields` or `fields`

Fields are specified in the order you
would like them to appear in the dataset, group or organization editing
pages. Datasets have separate lists of dataset and resource fields.
Organizations and groups have a single fields list.

Fields you exclude will not be shown to the end user, and will not
be accepted when editing or updating this type of dataset, group or
organization.


### `field_name`

The `field_name` value is the name of an existing CKAN dataset, resource,
group or organization field or a new new extra field. Existing dataset
field names include:

* `name` - the URI for the dataset
* `title`
* `notes` - the dataset description
* `author`
* `author_email`
* `maintainer`
* `maintainer_email`

New field names should follow the current lowercase_with_underscores
 naming convention. Don't name your field `mySpecialField`, use
 `my_special_field` instead.

This value is available to the form snippet as `field.field_name`.

FIXME: list group/organization fields


### `label`

The `label` value is a human-readable label for this field as
it will appear in the dataset editing form.
This label may be a string or an object providing in multiple
languages:

```json
{
  "en": "Title",
  "fr": "Titre"
}
```

When using a plain string translations will be provided with gettext.


### `required`

Set to `true` for fields that must be included. Set to `false` or
don't include this key for fields that are optional.

Setting to `true` will mark the field as required in the editing form
and include `not_empty` in the default validators that will be applied
when `validators` is not specified.

### `form_snippet`

The `form_snippet` value is the name of the snippet template to
use for this field in the dataset, group or organization editing form.
A number of snippets are provided with this
extension, but you may also provide your own by creating templates
under `scheming/form_snippets/` in a template directory in your
own extension.

This snippet is passed the `field` dict containing all the keys and
values in this field record, including any additional ones
you added to your that aren't handled by this extension.

This extension includes the following form snippets:

* [text.html](ckanext/scheming/templates/scheming/form_snippets/text.html) -
  a simple text field for free-form text or numbers (default when no
  choices list is given)
* [large_text.html](ckanext/scheming/templates/scheming/form_snippets/large_text.html) -
  a larger text field, typically used for the title
* [slug.html](ckanext/scheming/templates/scheming/form_snippets/slug.html) -
  the default name (URL) field
* [license.html](ckanext/scheming/templates/scheming/form_snippets/license.html) -
  a dataset license selection field
* [markdown.html](ckanext/scheming/templates/scheming/form_snippets/markdown.html) -
  a markdown field, often used for descriptions
* [organization.html](ckanext/scheming/templates/scheming/form_snippets/organization.html) -
  an organization selection field for datasets
* [upload.html](ckanext/scheming/templates/scheming/form_snippets/upload.html) -
  an upload field for resource files
* [select.html](ckanext/scheming/templates/scheming/form_snippets/select.html) -
  a select box (default when choices list is given)


### `display_snippet`

The `display_snippet` value is the name of the snippet template to
use for this field in the dataset, group or organization view page.
A number of snippets are provided with this
extension, but you may also provide your own by creating templates
under `scheming/display_snippets/` in a template directory in your
own extension.

This snippet is passed the `field` dict containing all the keys and
values in this field record, including any additional ones
you added to your that aren't handled by this extension.

This extension includes the following display snippets:

* [text.html](ckanext/scheming/templates/scheming/display_snippets/text.html) -
  render as a normal text value (default)
* [link.html](ckanext/scheming/templates/scheming/display_snippets/link.html) -
  render as an external link to open in a new window
* [email.html](ckanext/scheming/templates/scheming/display_snippets/email.html) -
  render as a "mailto:" link


### `validators`

The `validators` value is a space-separated string of validator and
converter functions to use for this field when creating or updating data.
When a validator name is followed by parenthesis the function is called
passing the comma-separated values within as string parameters
and the result is used as the validator/converter.

e.g. `"if_empty_same_as(name) unicode"` is the same as in a plugin specifying:

```python
[get_validator('if_empty_same_as')("name"), unicode]
```

This string does not contain arbitrary python code to be executed,
you may only use registered validator functions, optionally calling
them with static string values provided.

New validators and converters may be added using the IValidators
plugin interface.

This extension automatically adds calls to `convert_to_extras`
for new extra fields,
so you should not add that to this list.

### `output_validators`

The `output_validators` value is like `validators` but used when
retrieving values from the database instead of when saving them.
These validators may be used to transform the data before it is
sent to the user.

This extension automatically adds calls to `convert_from_extras`
for extra fields so you should not add that to this list.


### `choices`

The `choices` list must be provided for multiple-choice and
single-choice fields.  The `label`s are human-readable text for
the dataset editing form and the `value`s are stored in
the dataset field or are used for tag names in tag vocabularies.

A validator is automatically added for creating or updating datasets
that only allows values from this list.


### `tag_vocabulary`

(not yet implemented)

The `tag_vocabulary` value is used for the name of the tag vocabulary
that will store the valid choices for a multiple-choice field.

Tag vocabularies are global to the CKAN instance so this name should
be made unique, e.g. by prefixing it with a domain name in reverse order
and the name of the schema.


