# County Profiles Configuration

`profiles.json` defines per-county field mapping profiles used by `Get_Recent_Edits.py` to run ArcGIS Pro's **Detect Feature Changes** tool between two versions of a county road centerline dataset.

Each key in the JSON object is a county identifier (e.g. `"grand"`, `"davis"`). The script resolves the correct profile at runtime using the `--county` argument.

---

## Fields Reference

### `aliases`

**Type:** `string[]` | **Required**

A list of strings that the `--county` argument will accept to select this profile. The profile key itself is always implicitly included as an alias.

```json
"aliases": ["boxelder", "box elder"]
```

### `display_name`

**Type:** `string` | **Required**

Human-readable county name used in log output during a run.

---

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

**Type:** `string` | **Required**

A semicolon-delimited list of `update_field base_field` pairs passed to the `compare_fields` parameter of `DetectFeatureChanges`. These are the attribute fields checked for changes after two segments are matched.

A segment is included in the output recents layer if any of these fields differ between the update and base datasets, or if the geometry changed.

```json
"compare_fields": "PREDIR PREDIR; STREETNAME STREETNAME; L_F_ADD L_F_ADD; L_T_ADD L_T_ADD"
```

Fields that don't exist in one or both datasets are silently dropped before the tool runs, with a warning logged.

---

### `text_fields`

**Type:** `string[]` | **Required**

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

**Type:** `string[]` | **Required**

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
  "aliases": ["example"],
  "display_name": "Example County",
  "match_fields": "STREETNAME STREETNAME",
  "compare_fields": "PREDIR PREDIR; STREETNAME STREETNAME; STREETTYPE STREETTYPE; L_F_ADD L_F_ADD; L_T_ADD L_T_ADD; R_F_ADD R_F_ADD; R_T_ADD R_T_ADD",
  "text_fields": ["PREDIR", "STREETNAME", "STREETTYPE"],
  "numeric_fields": ["L_F_ADD", "L_T_ADD", "R_F_ADD", "R_T_ADD"]
}
```

## CLI Overrides

Most profile values can be overridden at runtime without editing `profiles.json`:

| Profile field      | CLI argument          |
|--------------------|-----------------------|
| `match_fields`     | `--match-fields`      |
| `compare_fields`   | `--compare-fields`    |
| `dfc_output_name`  | `--dfc-output-name`   |
| `stats_table_name` | `--stats-table-name`  |
| `recents_name`     | `--recents-name`      |
