# Data sources & connectors (Stage 6)

The **training-data** sources (`SyntheticSource`, `CsvSource` / real UCI in
`src/data/sources.py`) return the **raw UCI schema** (`src.data.RAW_COLUMNS`) so
the existing `src.preprocessing` chain consumes them unchanged. The **gated /
external** sources in `src/data/connectors/gated.py` return their
**provider-native** extract as-is (bureau and open-banking schemas differ per
provider and are not coerced into `RAW_COLUMNS`). Macro connectors
(`src/data/connectors/{rba,abs,apra}.py`) write to the `macro_indicators` table
via `src.db.upsert_indicators`. Gated sources ship **disabled** and fail loudly
until their flag is switched on in `feature_flags` **and** credentials are set.

| Connector | Data | License / attribution | Cost | External gate | Env / flag |
|---|---|---|---|---|---|
| `SyntheticSource` | Synthetic UCI-shaped credit rows | n/a (generated) | Free | none | `DATASOURCE=synthetic` |
| `CsvSource` / UCI file | Credit-card default (Taiwan 2005) | UCI ML Repository — public/academic; cite source | Free | none (download) | `DATASOURCE=uci` |
| `connectors/rba.py` | AU macro/credit statistics | Attribution: Reserve Bank of Australia | Free | none | `RBA_ENABLED=1` |
| `connectors/abs.py` | AU labour/income/demographics | ABS Data API terms of use | Free (key) | free API registration | `ABS_API_KEY`, `ABS_ENABLED=1` |
| `connectors/apra.py` | AU banking-system statistics | Attribution: APRA | Free | none | `APRA_ENABLED=1` |
| `connectors/hmda.py` | US mortgage fair-lending (LAR) | HMDA / FFIEC / CFPB — public | Free | public-data ToS | `HMDA_ENABLED=1` |
| `gated.FreddieMacSource` | Mortgage loan-level performance | Freddie Mac dataset license | Free w/ registration | **registration + license verification** | `FREDDIE_MAC_USERNAME`, `FREDDIE_MAC_PASSWORD`; flag `freddie_enabled` (OFF) |
| `gated.BureauSource` | Credit-bureau borrower files (Equifax/Experian/illion) | Commercial | **Paid contract** | **commercial contract + legal/compliance approval** | `BUREAU_API_KEY`; flag `bureau_enabled` (OFF) |
| `gated.OpenBankingSource` | Open-banking (CDR) transactions/affordability | CDR regime | Paid / partner | **CDR accreditation** | `CDR_CLIENT_ID`, `CDR_CLIENT_SECRET`; flag `openbanking_enabled` (OFF) |

## Gate behaviour (gated connectors)

- **Flag OFF (default):** `load()` raises naming the flag and the external
  approval required — no data is touched.
- **Flag ON, credentials missing:** `load()` raises naming the missing env var(s).
- **Flag ON + credentials present:** `load()` reads the configured extract.

Flags are read through `src.db.is_enabled`; an absent flag row reads as **OFF**
(default deny). Enabling a gate is a configuration change (flag + creds), not a
code change — see Master Plan Part D/E.
