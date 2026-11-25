"""Test-only localhost app with the real routes and an isolated Supabase stand-in."""

import os
from unittest.mock import patch

import uvicorn

from tests.fakes import FakeDB


def main() -> None:
    os.environ.update(
        PYTHON_DOTENV_DISABLED="1",
        LANGSMITH_TRACING="false",
        DATABASE_URL="",
        GROQ_API_KEY="browser-test",
        TAVILY_API_KEY="browser-test",
        SUPABASE_URL="http://127.0.0.1:1",
        SUPABASE_KEY="browser-test",
        SECRET_KEY="browser-test-secret-do-not-use-in-production",
    )

    from api.index import app, deps

    store = FakeDB()

    def request(method, table, query=None, payload=None, prefer=None, **_):
        return store.handle(method, [table], query=query, payload=payload, prefer=prefer)

    with patch.object(deps.db, "_supabase_rest_request", side_effect=request):
        uvicorn.run(app, host="127.0.0.1", port=8769)


if __name__ == "__main__":
    main()
