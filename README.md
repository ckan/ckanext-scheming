ckanext-scheming
================

This extension provides a way to configure and share
CKAN schemas using a JSON schema description. Custom
validators and template snippets for editing are also
supported.


Installation
============

This plugin relies on the scheming-support branch
of ckan, see: https://github.com/ckan/ckan/pull/1795


Configuration
=============

The schemas used are configured with configuration options:

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


Example dataset schema description
----------------------------------

```json
{
  "scheming_version": 1,
  "dataset_type": "camel-photos",
  "about_url": "http://example.com/the-camel-photos-schema",
  "dataset_fields": [
    {
      "field_name": "title",
      "label": "Title",
      "form_snippet": "large_text.html",
      "validators": "if_empty_same_as(name) unicode",
      "form_attrs": {"data-module": "slug-preview-target"},
      "form_placeholder": "eg. Larry, Peter, Susan"
    },
    {
      "field_name": "name",
      "label": "URL",
      "form_snippet": "dataset_slug.html",
      "validators": "not_empty unicode name_validator package_name_validator",
      "form_placeholder": "eg. camel-no-5"
    },
    {
      "field_name": "humps",
      "label": "Humps",
      "validators": "ignore_missing int_validator",
      "form_placeholder": "eg. 2"
    }
  ],
  "resource_fields": [
    {
      "field_name": "url",
      "label": "Photo",
      "validators": "not_empty unicode remove_whitespace",
      "form_snippet": "upload.html",
      "form_placeholder": "http://example.com/my-camel-photo.jpg",
      "upload_field": "upload",
      "upload_clear": "clear_upload",
      "upload_label": "Photo"
    }
  ]
}
```


scheming_version
----------------

Set to 1. Future versions of ckanext-scheming may use a larger
number to indicate a change to the description JSON format.

type
----

`type` is the "type" field stored in the dataset, group or organization.
For datasets it is used to set the URL for this type of dataset.

Normal datasets would be available under `/dataset`, but datasets with
the schema above would appear under `/spatialx` instead.

For organizations this field should be set to "organization" as some
parts of CKAN depend on this value not changing.


about_url
---------

`about_url` is a Link to human-readable information about this schema.
Its use is optional but highly recommended.


fields
------

Fields are specified in the `fields` list in the order you
would like them to appear in the dataset, group or organization editing
form.

Fields you exclude will not be shown to the end user, and will not
be accepted when editing or updating this type of dataset, group or
organization.

FIXME: list special cases


### field_name

The `field_name` value is the name of an existing CKAN dataset field
or a new new extra or keyword vocabulary field. Existing dataset field names
include:

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


### label

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


### form_snippet

The `form_snippet` value is the name of the snippet template to
use for this field in the dataset editing form.
A number of snippets are provided with this
extension, but you may also provide your own by creating templates
under `scheming/snippets/` in a template directory in your
own extension.

This snippet is passed the `field` dict containing all the keys and
values in this `dataset_field` record, including any additional ones
you added to your that aren't handled by this extension.


This extension includes the following snippets:

* text.html - a simple text field for free-form text or numbers
* large_text.html - a larger text field, typically used for the title
* choice_selectbox.html - a drop-down list for single-choice fields
* ... FIXME: complete this


### validators

The `validators` value is a space-separated string of validator functions
to use for this field when creating or updating data.
When a validator name is followed by parenthesis the function is called
passing the comma-separated values within as string parameters
and the result is used as the validator.

This string does not contain arbitrary python code to be executed,
you may only use registered validator functions, optionally calling
them with static string values provided.

FIXME: provide a way to register new validator functions form extensions

This extension automatically adds calls to `convert_to_extras` or
`convert_to_tags` for new extra fields and new tag vocabulary fields,
so you should not add those validators to this list.


### choices

The `choices` list must be provided for multiple-choice and
single-choice fields.  The `label`s are human-readable text for
the dataset editing form and the `value`s are stored in
the dataset field or are used for tag names in tag vocabularies.

A validator is automatically added for creating or updating datasets
that only allows values from this list.


### tag_vocabulary

The `tag_vocabulary` value is used for the name of the tag vocabulary
that will store the valid choices for a multiple-choice field.

Tag vocabularies are global to the CKAN instance so this name should
be made uniqe by prefixing it with a domain name in reverse order
and the name of the schema.


