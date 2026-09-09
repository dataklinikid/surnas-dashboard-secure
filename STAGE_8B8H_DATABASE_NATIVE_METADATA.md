# Stage 8B8H — Database-native production metadata

## Outcome

Event onboarding now builds canonical metadata directly from the selected production reporting database. Operators no longer upload a local DCF or canonical JSON file.

## Locked source contract

- `cspro_meta.dictionary` is the production CSPro dictionary.
- `information_schema.COLUMNS` is the reporting-schema source.
- `h0` is read only for an exact row count; no respondent rows are exported or stored.
- The selected catalog connection remains read-only.
- The canonical payload, its SHA-256, the raw dictionary SHA-256, CSPro version, and source timestamps are stored as onboarding provenance.

## Admin workflow

1. Scan the CSWeb reporting catalog.
2. Select a database that has both `h0` and `cspro_meta`.
3. Complete event identity, program, region, modules, and source-column mapping.
4. Open **Metadata & connection**.
5. Click **Ambil dari database, periksa, dan simpan**.
6. Continue to final validation only when the metadata/schema check passes.

## Read-only query budget

Metadata onboarding executes exactly three `SELECT` queries:

1. latest `cspro_meta` dictionary and provenance;
2. `information_schema.COLUMNS` for the selected reporting table;
3. exact `COUNT(*)` for the reporting table.

## Validation gates

- production dictionary must exist and be parseable;
- dictionary questionnaire identity must be present and cannot be active on another event;
- event code and source table in canonical metadata must match the draft event;
- all metadata, identity, latest-id, and valid-filter columns must exist in the reporting table;
- `aggregate_only=true` and `contains_respondent_rows=false` are mandatory;
- failed validation does not save metadata or activate the event.

## Compatibility

The ZIP/folder parser remains available for controlled legacy recovery, but it is not exposed as the normal event-administration workflow.

## Verification

```text
python manage.py test --settings=config.settings.test
Found 142 tests
OK
```
