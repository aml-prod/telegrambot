from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENV = ROOT / ".env"
OUT = ROOT / "bot" / "_embedded_env.py"


def main() -> None:
    token = ""
    if ENV.exists():
        content = ENV.read_text(encoding="utf-8", errors="ignore").splitlines()
        for line in content:
            m = re.match(r"^BOT_TOKEN=(.*)$", line.strip())
            if m:
                token = m.group(1).strip()
                break

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        f"EMBEDDED_BOT_TOKEN = {token!r}\n",
        encoding="utf-8",
    )
    print(f"Embedded token written to {OUT}")


if __name__ == "__main__":
    main()
