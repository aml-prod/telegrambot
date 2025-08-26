from __future__ import annotations

import mimetypes
from pathlib import Path

from flask import Flask, abort, send_file

from .links import DATA_DIR, consume_view

app = Flask(__name__)


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v/<token>")
def view(token: str):
    link = consume_view(token)
    if not link:
        abort(410)  # Gone (нет больше просмотров или не найдено)

    path: Path = link.path
    if not path.exists():
        abort(404)

    mime, _ = mimetypes.guess_type(path.name)
    return send_file(
        path,
        as_attachment=False,
        mimetype=mime or "image/jpeg",
        download_name=path.name,
        max_age=0,
        conditional=True,
        etag=True,
        last_modified=path.stat().st_mtime,
    )


if __name__ == "__main__":
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    app.run(host="0.0.0.0", port=8080)
