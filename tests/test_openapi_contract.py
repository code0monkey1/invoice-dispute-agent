"""The published API description, pinned while routes move into web/routers/.

Operation ids, parameters, request bodies, response models and the route
docstrings (shown on /docs) must survive a move unchanged. A deliberate API
change regenerates the snapshot:

    python -c "import json,api.index as a; s=a.app.openapi(); s['paths'].pop('/{full_path}',None); \
open('tests/contract/openapi.json','w').write(json.dumps(s,indent=1,sort_keys=True)+'\\n')"
"""
import json
from pathlib import Path

SNAPSHOT = Path(__file__).parent / "contract" / "openapi.json"


def current_schema() -> dict:
    from api.index import app
    schema = json.loads(json.dumps(app.openapi(), sort_keys=True))
    schema["paths"].pop("/{full_path}", None)  # the SPA catch-all exists only when frontend/dist is built
    return schema


def test_the_openapi_schema_matches_the_snapshot():
    expected = json.loads(SNAPSHOT.read_text())
    actual = current_schema()
    assert sorted(actual["paths"]) == sorted(expected["paths"])
    for path in expected["paths"]:
        assert actual["paths"][path] == expected["paths"][path], path
    assert actual == expected
