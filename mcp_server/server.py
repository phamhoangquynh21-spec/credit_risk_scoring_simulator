"""FastMCP server exposing the credit-risk platform as read-only MCP tools.

Run over stdio (for Claude Desktop / MCP clients):
    python -m mcp_server.server

The `mcp` SDK is imported lazily inside `build_server()` so this module (and
`mcp_server.tools`) import without the SDK installed — the tool logic stays
unit-testable in the base environment. Install the SDK with:
    pip install -r requirements-mcp.txt
"""
from __future__ import annotations

from . import tools

# Every tool is read-only (no writes to the platform), non-destructive, and
# idempotent. The registry/monitoring tools read Supabase (an external system).
_READ_ONLY = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "idempotentHint": True,
}

# (mcp tool name, human title, implementation, hits an external system?)
_REGISTRY = [
    ("credit_risk_score_applicant", "Score a credit applicant", tools.score_applicant, False),
    ("credit_risk_explain_applicant", "Explain an applicant's score", tools.explain_applicant, False),
    ("credit_risk_generate_memo", "Generate a grounded credit memo", tools.generate_memo, False),
    ("credit_risk_get_champion", "Get the champion model version", tools.get_champion, True),
    ("credit_risk_get_model_card", "Get a model card", tools.get_model_card, True),
    ("credit_risk_recent_drift", "Read recent drift metrics", tools.recent_drift, True),
    ("credit_risk_list_data_sources", "List data-source connectors", tools.list_data_sources, False),
]


def build_server():
    """Construct and return the FastMCP server with all tools registered."""
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("credit_risk_mcp")
    for name, title, fn, open_world in _REGISTRY:
        annotations = {"title": title, "openWorldHint": open_world, **_READ_ONLY}
        mcp.tool(name=name, annotations=annotations)(fn)
    return mcp


def main() -> None:
    build_server().run()  # stdio transport by default


if __name__ == "__main__":
    main()
