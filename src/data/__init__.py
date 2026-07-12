"""Stage 6 data layer: a raw-UCI ``DataSource`` interface plus macro/gated
connectors. Importing ``src.data`` is cheap — heavy/network deps (requests) are
imported lazily inside the connectors' ``fetch()`` calls only.
"""
from .base import RAW_COLUMNS, DataSource, validate_raw_schema
from .sources import CsvSource, SyntheticSource

__all__ = [
    "DataSource",
    "RAW_COLUMNS",
    "validate_raw_schema",
    "SyntheticSource",
    "CsvSource",
]
