# County Profiles Configuration

`profiles.json` defines flat, per-county settings shared by UTRANS commands. `etl` uses the transformation settings to convert county roads into the UTRANS schema. `get-recent-edits` uses its change-detection settings to run ArcGIS Pro's **Detect Feature Changes** tool between two versions of a county road centerline dataset. `detect-changes` uses only `fips` from the profile; its DFC match and comparison fields are fixed by the command.

Each key in the JSON object is a county identifier (e.g. `"grand"`, `"davis"`). The script resolves the correct profile at runtime using the `--county` argument.

`saltlake` is the Salt Lake County identifier for every command. The former `vecc` identifier is not supported.

## Profile Fields

### `fips`

**Type:** `string` | **Required by:** `etl`, `detect-changes`

**Used by:** `etl`, `detect-changes`

The county's five-digit FIPS code plus the name written to `COUNTY_L` and `COUNTY_R` during ETL. For example, `"49035 - Salt Lake"`.

### `field_mappings`

**Type:** `string` | **Required by `etl`**

**Used by:** `etl`

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

**Type:** `object` | **Optional** - defaults to `{}`

**Used by:** `etl`

Per-destination-field mappings for county source values that do not match a
UTRANS coded-value domain code or description. The outer field name is the
destination field name in the UTRANS output data. Each inner mapping uses this form:

```text
"county source value": "value written to the UTRANS output field"
```

The inner key on the left is the value read from the county source field. The
inner value on the right is the value written to the destination UTRANS field
after it is resolved against that field's coded-value domain. Field names,
source keys, and source values are matched case-insensitively after surrounding
whitespace is removed. The mapping value should be a valid destination domain
code or description, and mapping entries should represent translations rather
than identity mappings.

```json
"value_mappings": {
  "DOT_SRFTYP": {
    "PAVED ASPHALT": "P-ASP"
  },
  "DOT_CLASS": {
    "LOCAL ROAD": "L"
  }
}
```

In this example, `DOT_SRFTYP` and `DOT_CLASS` are UTRANS destination fields. A
county value of `PAVED ASPHALT` is written as `P-ASP` to the output
`DOT_SRFTYP` field, and a county value of `LOCAL ROAD` is written as `L` to the
output `DOT_CLASS` field.
The mapped value is resolved against the destination coded-value domain. Values
that remain invalid are recorded in `UTRANS_NOTES`.

---

### `rules`

**Type:** `string[]` | **Optional** — defaults to `[]`

**Used by:** `etl`

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

**Used by:** `etl`

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

**Used by:** `etl`

A semicolon-delimited list of `COUNTY_FIELD=TARGET` values used to parse full street
names. `TARGET` is `PRIMARY`, `A1`, or `A2`.

### `exclude_if_any`

**Type:** `string` or `object` | **Optional** - defaults to no exclusions

**Used by:** `etl`

Excludes a staged feature when any configured field contains one of the listed
case-insensitive values. The string form uses semicolon-delimited `FIELD=VALUE1,VALUE2`
pairs. The object form maps field names to arrays of values.

```json
"exclude_if_any": "S_SURF=400,410,420,430,440"
```

---

### `compare_fields`

**Type:** `string` | **Required**

**Used by:** `get-recent-edits`

A semicolon-delimited list of `update_field base_field` pairs passed to the `compare_fields` parameter of `DetectFeatureChanges`. These are the attribute fields checked for changes after two segments are matched.

A segment is included in the output recents layer if any of these fields differ between the update and base datasets, or if the geometry changed.

```json
"compare_fields": "PREDIR PREDIR; STREETNAME STREETNAME; L_F_ADD L_F_ADD; L_T_ADD L_T_ADD"
```

Fields that don't exist in one or both datasets are silently dropped before the tool runs, with a warning logged.

Every active county profile must provide this setting.

---

### `match_fields`

**Type:** `string` | **Required**

**Used by:** `get-recent-edits`

A space-separated `update_field base_field` pair used to confirm that two
spatially proximate road segments are the same road across the two datasets.
When both datasets use the same schema, the field name is repeated. If the
schemas differ, the two names can be different.

```json
"match_fields": "STREETNAME STREETNAME"
```

The specific field is selected per county because source schemas differ.

---

### `uppercase_normalize_fields`

**Type:** `string[]` | **Optional** — defaults to `[]`

**Used by:** `get-recent-edits`

A list of string fields whose values will also be uppercased during normalization.
Use this when a county's data may have mixed case values that should compare as equal.

```json
"uppercase_normalize_fields": ["STREETNAME", "STREETTYPE", "ACSALIAS"]
```

---

## Minimal Profile Example

```json
"example": {
  "fips": "49000 - Example",
  "field_mappings": "NAME=STREETNAME",
  "match_fields": "STREETNAME STREETNAME",
  "compare_fields": "PREDIR PREDIR; STREETNAME STREETNAME; STREETTYPE STREETTYPE; L_F_ADD L_F_ADD; L_T_ADD L_T_ADD; R_F_ADD R_F_ADD; R_T_ADD R_T_ADD"
}
```
