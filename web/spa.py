"""Static React delivery, registered after every API route."""

import os

from fastapi import HTTPException, Response
from fastapi.responses import FileResponse


def register_spa(app, frontend_dist: str) -> None:
    frontend_dist = os.path.realpath(frontend_dist)
    if not os.path.exists(frontend_dist):
        return

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        if full_path == "api" or full_path.startswith("api/"):
            # An unknown API path is a JSON 404, never the HTML app shell.
            raise HTTPException(status_code=404, detail="Not found")
        # Resolve the real path and refuse anything outside dist: an encoded
        # "../" (e.g. /..%2F..%2F.env) must never reach source files or secrets.
        file = os.path.realpath(os.path.join(frontend_dist, full_path))
        if file.startswith(frontend_dist + os.sep) and os.path.isfile(file):
            if full_path.startswith("assets/"):
                # Vite names bundles by content hash, so they never change.
                return FileResponse(
                    file,
                    headers={"Cache-Control": "public, max-age=31536000, immutable"},
                )
            return FileResponse(file)
        if full_path.startswith("assets/"):
            # A bundle from an earlier deploy: a 404, not the HTML shell, which
            # the browser would try to run as JavaScript.
            raise HTTPException(status_code=404, detail="Not found")
        # The app shell must be re-fetched after every deploy. Deployed files all
        # share one timestamp, so FileResponse's ETag never changed and browsers
        # kept an old index.html pointing at bundles that no longer exist.
        with open(os.path.join(frontend_dist, "index.html"), "rb") as stream:
            shell = stream.read()
        return Response(
            shell,
            media_type="text/html; charset=utf-8",
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
        )
