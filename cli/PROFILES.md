# County Profiles Configuration

`profiles.json` defines flat, per-county settings shared by UTRANS commands. `get-recent-edits` uses its field-mapping settings to run ArcGIS Pro's **Detect Feature Changes** tool between two versions of a county road centerline dataset. `etl` uses the same county key and its `fips` setting to select the matching county transformation.

Each key in the JSON object is a county identifier (e.g. `"grand"`, `"davis"`). The script resolves the correct profile at runtime using the `--county` argument.

`saltlake` is the Salt Lake County identifier for every command. The former `vecc` identifier is not supported.

## Shared ETL Field

### `fips`

**Type:** `string` | **Required by `etl`**

The county's five-digit FIPS code written to `COUNTY_L` and `COUNTY_R` during ETL.

### `field_mappings`

**Type:** `string` | **Required by `etl`**

A semicolon-delimited list of `UTRANS_FIELD=COUNTY_FIELD` assignments. These map
county source fields into the target schema after colliding source fields have been
renamed with an underscore. When the UTRANS destination has a coded-value domain,
valid aliases are converted to coded values. Invalid values are preserved and
appended to `UTRANS_NOTES` in all cases. An invalid value is also copied to the
destination field when it fits within that field's length; otherwise the destination
field is left at its default value. Values that exceed the destination field length
are reported with the field and value.

```json
"field_mappings": "FROMADDR_L=L_F_ADD; TOADDR_L=L_T_ADD; NAME=STREETNAME"
```

### `value_mappings`

**Type:** `object` | **Optional** — defaults to `{}`

Per-target mappings for source values that do not match a UTRANS coded-value
domain code or description. Each target field contains an object mapping the
source value to the desired target value. Field names and source values are
matched case-insensitively after surrounding whitespace is removed. The mapped
target value is then resolved against the destination coded-value domain, so it
can be either a coded value or a domain description.

```json
"value_mappings": {
  "ONEWAY": {
    "ONE DIRECTION": "Y",
    "TWO WAY": "N"
  },
  "DOT_CLASS": {
    "LOCAL ROAD": "L"
  }
}
```

Mappings run after `field_mappings` selects a source field and before normal
destination-domain matching. If no configured mapping or valid domain match is
found, the original source value is handled as an invalid value: it is appended
to `UTRANS_NOTES` and copied only when it fits the target field length.

### `rules`

**Type:** `string[]` | **Optional** — defaults to `[]`

An ordered list of supported post-mapping transformations. Rules run after field
and full-address mappings, but before the feature is normalized and appended. Unknown
or duplicate names are rejected.

```json
"rules": ["remove_postdir_if_alpha", "remove_posttype_if_numeric"]
```

Supported rules:

- `remove_postdir_if_alpha`: clears `POSTDIR` when `NAME` begins with a letter.
- `remove_posttype_if_numeric`: clears `POSTTYPE` when `NAME` begins with a digit.

### `custom_handler`

**Type:** `string` | **Optional**

Selects a built-in, county-specific transformation for behavior that requires
multiple fields or conditional assignments. Handler names are resolved from the
CLI's fixed registry; profile files cannot name Python modules or functions.
Unknown handler names are rejected before ETL updates begin.

```json
"custom_handler": "utah_road_names"
```

Currently supported handlers:

- `utah_road_names`: preserves Utah County's legacy handling of numeric primary
  and alternate road names ending in a cardinal direction.
- `davis_alias`: parses Davis County's `RoadAliasName` into alpha or numeric
  aliases while ignoring compound names.
- `washington_postdir_and_aliases`: selects Washington County's primary or
  suffix direction and removes aliases duplicated by the numeric alias.
- `weber_alias`: parses Weber County's alpha and numeric alias conventions.
- `summit_names`: prefixes Summit County highway names and conditionally parses
  its alternate road name.
- `tooele_numeric_name`: parses numeric Tooele County primary names.
- `emery_compact_aliases`: recognizes Emery County compact numeric aliases such
  as `100N`.
- `grand_numeric_acs_name`: retains Grand County's ACS name only when numeric.
- `kane_alias_cleanup`: removes Kane County's invalid `K`-prefixed aliases.
- `sevier_postdir_fallback`: uses Sevier County's suffix direction when address
  parsing did not produce one.
- `uintah_exclusion_note`: records Uintah County's excluded features in notes.
- `wayne_acs_alias`: parses Wayne County's ACS alias.

### `parse_sources`

**Type:** `string` | **Optional**

A semicolon-delimited list of `COUNTY_FIELD=TARGET` values used to parse full street
names. `TARGET` is `PRIMARY`, `A1`, or `A2`.

### `translate_vertical_levels`

**Type:** `boolean` | **Optional** — defaults to `false`

When `true`, legacy vertical values `1`, `2`, and `3` are translated to `0`, `1`,
and `2` before domain-value matching. Invalid values are still preserved when they
fit within the destination field length and are always appended to `UTRANS_NOTES`.

### `exclude_if_any`

**Type:** `string` | **Optional**

A semicolon-delimited list of `COUNTY_FIELD=VALUE,VALUE` exclusions. A feature is
removed when any configured field contains a listed value.

County selection is strict:

- `--county` must exactly match a top-level key in the active profiles file
- By default, the active profiles file is `cli/profiles.json`
- Use `--profiles <path-to-json>` to supply a custom profiles file
- Matching is case-sensitive
- Aliases and spaced variants are not supported

---

## Fields Reference

### `match_fields`

**Type:** `string` | **Required**

A space-separated field pair (`update_field base_field`) used to confirm that two spatially proximate road segments are the **same road** across the two datasets. This is passed directly to the `match_field` parameter of `DetectFeatureChanges`.

The tool first finds candidate matches within `--search-distance`, then uses this field to disambiguate — e.g. confirming two nearby segments share the same street name before treating them as the same feature.

```json
"match_fields": "STREETNAME STREETNAME"
```

When both datasets use the same schema, the field name is repeated. If the schemas differ, the two names can be different (e.g. `"S_NAME STREETNAME"`).

> **Note:** The specific field chosen per county was determined during original script development and reflects the primary name field in that county's road schema.

---

### `compare_fields`

**Type:** `string` | **Optional in profile**

A semicolon-delimited list of `update_field base_field` pairs passed to the `compare_fields` parameter of `DetectFeatureChanges`. These are the attribute fields checked for changes after two segments are matched.

A segment is included in the output recents layer if any of these fields differ between the update and base datasets, or if the geometry changed.

```json
"compare_fields": "PREDIR PREDIR; STREETNAME STREETNAME; L_F_ADD L_F_ADD; L_T_ADD L_T_ADD"
```

Fields that don't exist in one or both datasets are silently dropped before the tool runs, with a warning logged.

If omitted from the profile, it must be provided via `--compare-fields` at runtime.

---

### `text_fields`

**Type:** `string[]` | **Optional** — defaults to `[]`

Fields that will be text-normalized before change detection runs. Normalization:

- Collapses internal whitespace to single spaces
- Trims leading/trailing whitespace
- Converts `None`, `NULL`, and blank values to empty string `""`

This prevents false positives caused by whitespace or null inconsistencies between datasets.

```json
"text_fields": ["PREDIR", "STREETNAME", "STREETTYPE", "SUFDIR"]
```

---

### `numeric_fields`

**Type:** `string[]` | **Optional** — defaults to `[]`

Fields that will be numeric-normalized before change detection runs. Normalization:

- Converts `None`, `NULL`, and blank values to `0`

This prevents false positives caused by null vs. zero inconsistencies in address range fields.

```json
"numeric_fields": ["L_F_ADD", "L_T_ADD", "R_F_ADD", "R_T_ADD"]
```

---

### `uppercase_normalize_fields`

**Type:** `string[]` | **Optional** — defaults to `[]`

A subset of `text_fields` whose values will also be uppercased during normalization. Use this when a county's data may have mixed case values that should compare as equal.

```json
"uppercase_normalize_fields": ["STREETNAME", "STREETTYPE", "ACSALIAS"]
```

---

### `required_fields`

**Type:** `string[]` | **Optional** — defaults to `[]`

Fields that must exist in **both** the update and base feature classes. If any are missing, the script raises an error before doing any work. Useful for counties whose schemas are known to be strict or whose pipelines depend on specific fields being present.

```json
"required_fields": ["RoadName", "LeftFrom", "LeftTo", "RightFrom", "RightTo"]
```

---

### `dfc_output_name`

**Type:** `string` | **Optional** — defaults to `"DFC_CountyToCounty"`

Name of the output feature class written by `DetectFeatureChanges`. Output is placed in the same workspace as the update feature class.

---

### `stats_table_name`

**Type:** `string` | **Optional** — defaults to `"stats_county_to_county"`

Name of the statistics table written by `DetectFeatureChanges`.

---

### `recents_name`

**Type:** `string` | **Optional** — defaults to `"RoadCenterline_Recents"`

Name of the final output feature class containing only roads that changed (i.e. those where `CHANGE_TYPE <> 'NC'`). This is the primary deliverable of the script.

---

## Minimal Profile Example

```json
"example": {
  "match_fields": "STREETNAME STREETNAME",
  "compare_fields": "PREDIR PREDIR; STREETNAME STREETNAME; STREETTYPE STREETTYPE; L_F_ADD L_F_ADD; L_T_ADD L_T_ADD; R_F_ADD R_F_ADD; R_T_ADD R_T_ADD",
  "text_fields": ["PREDIR", "STREETNAME", "STREETTYPE"],
  "numeric_fields": ["L_F_ADD", "L_T_ADD", "R_F_ADD", "R_T_ADD"]
}
```

## CLI Overrides

Most profile values can be overridden at runtime without editing `profiles.json`:

| Profile field      | CLI argument         |
| ------------------ | -------------------- |
| `match_fields`     | `--match-fields`     |
| `compare_fields`   | `--compare-fields`   |
| `dfc_output_name`  | `--dfc-output-name`  |
| `stats_table_name` | `--stats-table-name` |
| `recents_name`     | `--recents-name`     |
