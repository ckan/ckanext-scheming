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
  "dataset_type": "spatialx",
  "about_url": "http://example.com/the-spatialx-schema",
  "dataset_fields": [
    {
      "field": "title",
      "lable": (language-text),
      "form_snippet": "large_text.html",
      "validators": "if_empty_same_as(name)"
    },
    {
      "field": "name",
      "label": (language-text),
      "form_snippet": "autofill_from_title.html",
      "validators": "not_empty name_validator package_name_validator"
    },
    {
      "field": "internal_flag",
      "lable": (language-text),
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
      "field": "internal_categories",
      "lable": (language-text),
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
      "field": "spatial",
      "lable": (language-text),
      "form_snippet": "map_bbox_selection.html",
      "validators": "geojson_validator"
    }
  ]
}
```

`dataset_type` is the package_type stored in the Package model and
returned from the plugin's `package_types()` method. This should be
unique if you are sharing your schema.

language-text
-------------

`(language-text)` in the example above may be a plain string or an
object containing different language versions:

```json
{
  "eng": "Title",
  "fra": "Titre"
}
```

When using a plain string translations will be looked up with gettext.


