"""Minimal offline fake Supabase client (mirrors tests/db/test_repos_unit.py).

Records every .table(...) chain; each .execute() pops the next queued result.
Used so src.data connectors/gated sources can be tested with no network/DB.
"""
from __future__ import annotations


class _Result:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    def __init__(self, client, table):
        self._client = client
        self.table = table
        self.ops = []  # [(method, args, kwargs)]

    def __getattr__(self, name):
        def op(*args, **kwargs):
            self.ops.append((name, args, kwargs))
            return self
        return op

    def execute(self):
        self._client.calls.append(self)
        return _Result(self._client.results.pop(0) if self._client.results else [])

    def arg(self, method):
        return next(a[0] for n, a, _ in self.ops if n == method)


class FakeClient:
    def __init__(self, results=None):
        self.results = list(results or [])
        self.calls = []

    def table(self, name):
        return _FakeQuery(self, name)
