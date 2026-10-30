"""Small shared utilities for UTRANS commands."""

import os

import arcpy


def log(message: str) -> None:
    """Write a command message to standard output."""
    print(message)


def ensure_feature_class(path: str, option: str) -> None:
    """Validate an input feature class and identify its CLI option on failure."""
    try:
        exists = arcpy.Exists(path)
        description = arcpy.Describe(path) if exists else None
    except (OSError, RuntimeError, arcpy.ExecuteError) as exc:
        raise RuntimeError(
            f"Invalid {option} path '{path}': could not read the dataset. "
            f"Provide an accessible feature class path. ArcGIS reported: {exc}"
        ) from exc

    if description is None:
        raise RuntimeError(
            f"Invalid {option} path '{path}': dataset does not exist or is not accessible. "
            "Check the path and permissions, and include the feature class name "
            r"(for example, C:\data\roads.gdb\Roads)."
        )
    if description.dataType != "FeatureClass":
        raise RuntimeError(
            f"Invalid {option} path '{path}': expected a feature class, "
            f"but found {description.dataType}. "
            "Provide the full path including the feature class name, "
            "not just a geodatabase or feature dataset "
            r"(for example, C:\data\roads.gdb\Roads)."
        )


def get_output_workspace(feature_class: str) -> str:
    """Return the containing geodatabase for a feature class."""
    dirname = os.path.dirname(arcpy.Describe(feature_class).catalogPath)
    desc = arcpy.Describe(dirname)
    if hasattr(desc, "datasetType") and desc.datasetType == "FeatureDataset":
        dirname = os.path.dirname(dirname)
    return dirname
