"""Development entry point: ``python -m liveask.run --port 8000``.

On Windows, uvicorn insists on the Proactor event loop, which psycopg's async mode cannot
use. This runs uvicorn on the selector loop instead. In Docker/Kubernetes (Linux) the
plain ``uvicorn liveask.main:app`` command is used and none of this is needed.
"""

from __future__ import annotations

import argparse
import asyncio
import sys

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    server = uvicorn.Server(uvicorn.Config("liveask.main:app", host=args.host, port=args.port))
    asyncio.run(server.serve())


if __name__ == "__main__":
    main()
