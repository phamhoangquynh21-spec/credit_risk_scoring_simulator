# Credit Risk MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io) server that exposes the
credit-risk platform's capabilities as **read-only tools** an LLM client (Claude
Desktop, etc.) can call. It wraps the tested `src/` ML core directly — no model
logic is re-implemented, and no tool writes to the platform.

## Tools

| Tool | What it does | Needs Supabase? |
|---|---|---|
| `credit_risk_score_applicant` | Probability, 0–100 risk score, band; threshold + approve/decline recommendation when the registry is reachable | no (registry enriches) |
| `credit_risk_explain_applicant` | SHAP top factors → analyst reason codes + "contribution, not causation" disclaimer | no |
| `credit_risk_generate_memo` | Grounded credit memo (LLM when configured, else deterministic template) | no |
| `credit_risk_get_champion` | The current champion model version | yes |
| `credit_risk_get_model_card` | Markdown model card (identity, metrics, fairness vs the 0.8 rule) | yes |
| `credit_risk_recent_drift` | Recent points for a drift/quality metric | yes |
| `credit_risk_list_data_sources` | The connector registry (live-and-free vs gated) | no |

Every tool is annotated `readOnlyHint: true`. Scoring/explain/memo run offline from
the committed `models/model.pkl`. Registry/monitoring tools return a clear,
actionable message when Supabase credentials are absent (they never crash).

## Install & run

```bash
# from the repo root, in the project virtualenv
pip install -r requirements-mcp.txt          # the mcp SDK (server-only)
python -m mcp_server.server                   # runs over stdio
```

Registry/monitoring tools read Supabase via the same `.env` the rest of the
platform uses (`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`). The LLM memo tool
uses a deterministic template unless `ANTHROPIC_API_KEY` is set and the `anthropic`
SDK is installed (see `requirements-llm.txt`).

## Claude Desktop configuration

Add to `claude_desktop_config.json` (`command` points at the project venv Python so
`src/` and the model load correctly):

```json
{
  "mcpServers": {
    "credit_risk": {
      "command": "C:\\Users\\Gamer\\Documents\\credit_risk_scoring_simulator\\.venv\\Scripts\\python.exe",
      "args": ["-m", "mcp_server.server"],
      "cwd": "C:\\Users\\Gamer\\Documents\\credit_risk_scoring_simulator"
    }
  }
}
```

## Design notes

- **`mcp_server/tools.py`** holds the tool logic as plain functions with Pydantic
  input models — unit-testable without the `mcp` SDK (`tests/mcp/test_tools.py`).
- **`mcp_server/server.py`** wires those functions into a `FastMCP` server and
  imports the SDK lazily, so importing the package never requires `mcp`.
- Read-only by design: the server surfaces scoring, explanation, memos, and
  governance/monitoring reads. It does not promote models, write predictions, or
  mutate any platform state — those remain governed actions behind the API.
