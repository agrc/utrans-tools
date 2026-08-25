"""Small shared utilities for UTRANS commands."""

import os

import arcpy


def log(message: str) -> None:
    """Write a command message to standard output."""
    print(message)


def get_output_workspace(feature_class: str) -> str:
    """Return the containing geodatabase for a feature class."""
    dirname = os.path.dirname(arcpy.Describe(feature_class).catalogPath)
    desc = arcpy.Describe(dirname)
    if hasattr(desc, "datasetType") and desc.datasetType == "FeatureDataset":
        dirname = os.path.dirname(dirname)
    return dirname
