"""Version the CLI's JSON contract independently from the toolkit release."""
from __future__ import annotations

import re

from . import __version__


SCHEMA_VERSION = "1.0"


def report(result: dict, operation: str) -> dict:
    return {**result, "schema_version": SCHEMA_VERSION,
            "toolkit_version": __version__, "operation": operation}


def check_inventory_version(document: dict) -> None:
    """Accept legacy inventories and additive revisions of the current major."""
    if "schema_version" not in document:
        return
    version = document["schema_version"]
    if not isinstance(version, str) or not re.fullmatch(r"[1-9][0-9]*\.[0-9]+", version):
        raise ValueError("Inventory schema_version must be a major.minor string.")
    if version.split(".")[0] != SCHEMA_VERSION.split(".")[0]:
        raise ValueError(f"Unsupported inventory schema version: {version}.")
    if document.get("operation") != "inventory":
        raise ValueError("A versioned inventory must have operation='inventory'.")
