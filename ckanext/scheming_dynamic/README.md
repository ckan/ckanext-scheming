# scheming_dynamic

Store your ckanext-scheming schemas (for datasets, groups and organizations)
in the database instead of static config files, so admins can create and edit
them from the CKAN admin UI — no server restart, no deploy.

## Setup

```sh
pip install ckanext-scheming[dynamic]
```

```ini
ckan.plugins = scheming_datasets scheming_dynamic
# let scheming handle dataset types CKAN didn't know about at startup
scheming.dataset_fallback = true
```

Apply the migration:

```sh
ckan db upgrade -p scheming_dynamic
```

### Adding this to a portal that already has data

If you already have datasets/groups/organizations of a type defined in a
config file, import that schema into the database and pin the existing
entities to it. This keeps them validating against the exact schema they were
created with, even after you edit it later.

```sh
ckan scheming-dynamic sync --type dataset SCHEMA_TYPE
ckan scheming-dynamic pin --type dataset SCHEMA_TYPE
```

`sync` copies the file-based schema into the database as version 1. `pin`
locks every not-yet-pinned entity of that type to a version. See
[CLI](#cli) below for all the options.

## Using the admin UI

Sysadmins get a **Scheming** tab under `/ckan-admin/`, with four sub-tabs:

- **Schemas** — every dynamic schema, dataset/group/organization together in
  one table (an *Entity type* column tells them apart). Create, edit, view
  history, or delete from here. Since a new schema still needs to know which
  entity type it's for, **Add schema** is a dropdown: Dataset, Group or
  Organization.
- **Presets** — reusable field definitions you can plug into any schema.
- **Migrations** — move entities from an old schema version onto a newer
  one. See [Migrations](#migrations) below.
- **History** — every create/update/delete ever recorded for a schema type,
  including deleted ones.

Editing a schema, you get a choice: paste/edit the raw JSON, or use the
generated form (add/remove fields, reorder them, pick presets). A **Preview**
button renders the definition with the real dataset/resource form snippets,
so you can catch a broken schema before saving it. Dataset schemas use the
usual `dataset_fields`/`resource_fields` shape; group and organization
schemas use a single flat `fields` list instead, since they have no
resources.

A database schema or preset with the same type/name as one defined in a
config file always wins.

Groups and organizations can have more than one schema type each, exactly
like datasets — but most sites only need one (the built-in `group`/
`organization` type). That's the easy path: give your schema that same type
name and it becomes the default form.

## API

All actions are sysadmin-only. `entity_type` defaults to `"dataset"` (also
accepts `"group"` or `"organization"`).

**Schemas**
- `scheming_schema_create(definition, entity_type="dataset")` — the schema's
  type name comes from the definition itself (`dataset_type`/`group_type`/
  `organization_type`)
- `scheming_schema_update(schema_type, definition, entity_type="dataset")`
- `scheming_schema_delete(schema_type, entity_type="dataset")` — refuses
  while any entity still uses that type

**Presets**
- `scheming_preset_create(preset_name, values)` — `values` is the attribute
  bag a field using the preset inherits (the same keys a schema field takes)
- `scheming_preset_update(preset_name, values)` — replaces the stored `values`
- `scheming_preset_delete(preset_name)` — refuses while any schema field
  still uses it

**Migrations** (see [Migrations](#migrations))
- `scheming_migration_status(entity_type="dataset", schema_type=None)` — how
  far each schema type lags behind its live version
- `scheming_migration_mapping_show(schema_type, from_version, to_version)`
- `scheming_migration_mapping_update(schema_type, from_version, to_version, mapping)`
- `scheming_migration_mapping_delete(schema_type, from_version, to_version)`
- `scheming_migration_apply(schema_type, from_version, to_version, id=None, values=None, dry_run=False)`
  — pass `id` to migrate one entity right away; omit it to queue a
  background run over everything still on `from_version`
- `scheming_migration_run_list(entity_type="dataset", schema_type=None, limit=20, offset=0)`
- `scheming_migration_run_show(id)`
- `scheming_migration_run_cancel(id)`

Definitions are validated the same way whether you go through the API, CLI
or admin UI.

## CLI

- `ckan scheming-dynamic validation-schema --type dataset|group|organization`
  — print the JSON Schema a definition must satisfy
- `ckan scheming-dynamic validate --type dataset schema.yaml [more.json ...]`
  — validate file(s) against it
- `ckan scheming-dynamic sync --type dataset SCHEMA_TYPE` — import a
  file-based schema into the database
- `ckan scheming-dynamic pin --type dataset SCHEMA_TYPE [-v VERSION] [--no-validate] [--dry-run]`
  — pin every not-yet-pinned entity of that type to a version (default: the
  current live one)
- `ckan scheming-dynamic migration status --type dataset [SCHEMA_TYPE]`
- `ckan scheming-dynamic migration mapping --type dataset SCHEMA_TYPE FROM TO [--json]`
- `ckan scheming-dynamic migration apply --type dataset SCHEMA_TYPE FROM TO [--dry-run]`
  — runs inline with a progress bar, so it works even without a background
  job worker
- `ckan scheming-dynamic migration runs --type dataset [RUN_ID]`
- `ckan scheming-dynamic migration cancel RUN_ID`
- `ckan scheming-dynamic migration prune --older-than DAYS` — clean up old
  migration history (keeps the outcome, drops the recorded values)

## Migrations

Every dataset, group and organization stays pinned to the schema version it
was created under. Edit the schema, and older entities keep using their old
version until you migrate them forward.

A migration always moves entities between two versions of **the same schema
type** — it can't change what type something is.

### How a migration decides what to do with each field

Comparing the old and new version tells you, for every field:

| Situation | What happens |
|---|---|
| Unchanged, or made less strict | copied automatically |
| Made stricter (e.g. a new validator) | copied, but flagged for review |
| A choice that existing data uses was removed | needs a replacement value |
| Field became required | needs an answer |
| New optional field, or one with a default | filled in automatically |
| New required field, no default | needs an answer |
| Field removed | needs explicit confirmation that its data is being dropped |
| Looks like it was renamed | suggested, but never applied without confirming |

Renames are never guessed silently, even on an exact match — a wrong guess
moves data into the wrong field with nothing to catch it later.

Anything that needs a decision is either answered once for everyone (as part
of the mapping), or left to a guided per-entity form when it genuinely
depends on the entity.

### Running one

Migrating a single entity happens immediately. Migrating many queues a
background job (or runs inline with a progress bar via the CLI, if you have
no job worker). Either way you get a *run*: a record of what happened to
each entity — ok, failed, or skipped — plus before/after values for anything
that changed.

If an entity's new data fails validation, nothing about it is changed — it's
recorded as failed and the run moves on. Re-running a migration is safe:
anything already on the target version is just skipped.

### Data safety

There's no built-in "undo". Use the mapping preview and `--dry-run` to catch
mistakes before they're written — that's what they're for.

The one action that's genuinely irreversible is dropping a field's data,
which is why it always needs an explicit confirmation. Even then, the
before/after values are kept in the run's history until you run
`migration prune` — nothing is thrown away automatically.

## Known limitations

- Changing a schema doesn't update the search index by itself — run
  `ckan search-index rebuild` after a change that affects search, including
  after a migration.
- Only pinned entities can be migrated. Anything created before pinning was
  turned on needs `pin` first.
- Presets aren't versioned — editing one changes what every schema that uses
  it resolves to, even schemas already locked to an older version.
