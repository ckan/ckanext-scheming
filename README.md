ckanext-customschema
====================

This extension provides a way to configure and share
CKAN schemas using a JSON schema description. Custom
validators and template snippets for editing are also
supported.

The schemas used are configured with a configuration option
similar to `licenses_group_url`, e.g.:

```ini
customschema.schema_urls = http://example.com/spatialx_schema.json
```

Paths relative to the configuration file may also be used:

```ini
customschema.schema_urls = ../ckanext/spatialx/customschema.json
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
      "tag_vocabulary": "spatialx_categories",
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

When using a plain string translations will be looked up with gettext.


dataset_type
------------

`dataset_type` is the "type" field stored in the dataset, which
determines the schema used.
This string should be unique to make sharing your schema easier,
use of a domain name in reverse order at the beginning of this
string is encouraged.


about_url
---------

A Link to human-readable information about this schema may be
provided in this field.


dataset_fields
--------------

Fields are specified in this list in the order you would like them
to appear in the dataset editing form.


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




