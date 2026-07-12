"""Gated DataSources — built to the interface, shipped DISABLED.

Each source is dark until BOTH its feature flag is switched on in Supabase AND
the required credentials are present in the environment. With the flag off
(the default), ``load()`` raises and names the external approval that must clear
first; with the flag on but creds missing, it fails loudly naming the missing
credential. No live network calls here — enabled+configured sources read a
provided fixture/extract path, keeping the contract testable offline.
"""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

from ...db import is_enabled
from ..base import DataSource


class _GatedSource(DataSource):
    """Shared flag + credential gate for the not-yet-licensed data feeds."""

    FLAG_KEY: str = ""
    REQUIRED_ENV: tuple[str, ...] = ()
    APPROVAL: str = ""  # the external gate that must clear to enable this

    def __init__(self, path: str | Path | None = None, flags_client=None):
        self.path = Path(path) if path is not None else None
        self._flags_client = flags_client

    def _check_gate(self) -> None:
        if not is_enabled(self.FLAG_KEY, client=self._flags_client):
            raise RuntimeError(
                f"{self.name} is disabled: feature flag '{self.FLAG_KEY}' is OFF. "
                f"Enabling it requires {self.APPROVAL} before any data is loaded."
            )
        missing = [v for v in self.REQUIRED_ENV if not os.environ.get(v)]
        if missing:
            raise RuntimeError(
                f"{self.name} flag '{self.FLAG_KEY}' is ON but credentials are "
                f"missing: set {', '.join(missing)} in the environment."
            )

    def load(self) -> pd.DataFrame:
        self._check_gate()
        if self.path is None or not self.path.exists():
            raise FileNotFoundError(
                f"{self.name}: enabled but no data extract at {self.path!r}")
        return pd.read_csv(self.path)


class FreddieMacSource(_GatedSource):
    name = "freddie_mac"
    description = "Freddie Mac single-family loan-level performance data."
    FLAG_KEY = "freddie_enabled"
    REQUIRED_ENV = ("FREDDIE_MAC_USERNAME", "FREDDIE_MAC_PASSWORD")
    APPROVAL = "Freddie Mac registration + dataset license verification"


class BureauSource(_GatedSource):
    name = "bureau"
    description = "Credit-bureau borrower files (Equifax/Experian/illion)."
    FLAG_KEY = "bureau_enabled"
    REQUIRED_ENV = ("BUREAU_API_KEY",)
    APPROVAL = "a signed commercial contract + legal/compliance approval"


class OpenBankingSource(_GatedSource):
    name = "open_banking"
    description = "Open-banking (CDR) transaction/affordability data."
    FLAG_KEY = "openbanking_enabled"
    REQUIRED_ENV = ("CDR_CLIENT_ID", "CDR_CLIENT_SECRET")
    APPROVAL = "CDR (Consumer Data Right) accreditation"
