from __future__ import annotations

import os

import uvicorn


def main() -> None:
    port = int(os.getenv("AI_TRIAGE_PORT", "8000"))
    uvicorn.run(
        "ai_bug_triage.web:app",
        host="127.0.0.1",
        port=port,
        reload=False,
        access_log=False,
    )


if __name__ == "__main__":
    main()
