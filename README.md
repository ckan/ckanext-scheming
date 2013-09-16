ckanext-scheming
================

*This document describes a planned CKAN extension.
The code here doesn't actually accomplish any of this yet.*

This extension provides a way to configure and share
CKAN schemas using a JSON schema description. Custom
validators and template snippets for editing are also
supported.

The schemas used are configured with a configuration option
similar to `licenses_group_url`, e.g.:

```ini
#   URLs to shared schemas being used
scheming.schemas = http://example.com/spatialx_schema.json

#   module-path:file name may also be used, e.g:
#
# scheming.schemas = ckanext.spatialx:spatialx_schema.json
#
#   will try to load "spatialx_schema.json" from the directory
#   containing the ckanext.spatialx module
```


Example JSON schema description
-------------------------------

```json
{
  "dataset_type": "com.example.spatialx",
  "about_url": "http://example.com/the-spatialx-schema",
  "dataset_fields": [
    {
      "field_name": "title",
      "label": (language-text),
      "form_snippet": "large_text.html",
      "validators": "if_empty_same_as(name)"
    },
    {
      "field_name": "name",
      "label": (language-text),
      "form_snippet": "autofill_from_title.html",
      "validators": "not_empty name_validator package_name_validator"
    },
    {
      "field_name": "internal_flag",
      "label": (language-text),
      "form_snippet": "choice_selectbox.html",
      "validators": "not_empty",
      "choices": [
        {
          "label": (language-text),
          "value": "X",
        },
        {
          "label": (language-text),
          "value": "Y",
        }
      ]
    },
    {
      "field_name": "internal_categories",
      "label": (language-text),
      "form_snippet": "multiple_choice_checkboxes.html",
      "validators": "ignore_empty",
      "tag_vocabulary": "com.example.spatialx_categories",
      "choices": [
        {
          "label": (language-text),
          "value": "P",
        },
        {
          "label": (language-text),
          "value": "Q",
        },
        {
          "label": (language-text),
          "value": "R",
        }
      ]
    },
    {
      "field_name": "spatial",
      "label": (language-text),
      "form_snippet": "map_bbox_selection.html",
      "validators": "geojson_validator"
    }
  ]
}
```

In the example above `(language-text)` may be a plain string or an
object containing different language versions:

```json
{
  "eng": "Title",
  "fra": "Titre"
}
```

When using a plain string translations will be provided with gettext
instead.


dataset_type
------------

`dataset_type` is the "type" field stored in the dataset, which
CKAN uses to determines the schema.

This string should be unique in order to make sharing your schema easier.
Use of a domain name in reverse order at the beginning of this
string is encouraged.


about_url
---------

`about_url` is a Link to human-readable information about this schema.
Its use is optional but highly recommended.


dataset_fields
--------------

Fields are specified in the `dataset_fields` list in the order you
would like them to appear in the dataset editing form.

Fields you exclude will not be shown to the end user, and will not
be accepted when editing or updating a dataset.

FIXME: list special cases


### field_name

The `field_name` value is the name of an existing CKAN dataset field
or a new new extra or keyword vocabulary field. Existing field names
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


### label

The `label` value is a human-readable label for this field as
it will appear in the dataset editing form.
This label may be provided in multiple
languages, but only the correct version for the user's language
will be passed to the form snippet as `field.label`.


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
