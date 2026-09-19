import argparse
import os

from .api_adapter import O32APIAdapter
from .auth import build_default_production_authenticator
from .http_server import O32HTTPServer
from .service import ApplicationService


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=int(os.getenv("AI_OS_API_PORT", "8080")))
    parser.add_argument("--db", default=os.getenv("AI_OS_JOBS_DB_PATH", "./data/jobs.sqlite3"))
    args = parser.parse_args()

    production = os.getenv("AI_OS_ENV", "local").strip().lower() in {"prod", "production"}
    host = args.host or ("127.0.0.1" if production else "127.0.0.1")

    authenticator = None
    if production:
        authenticator, _identity = build_default_production_authenticator()

    service = ApplicationService(db_path=args.db, authenticator=authenticator)
    api = O32APIAdapter(service)
    server = O32HTTPServer(api, host, args.port, require_auth=production)
    try:
        server.start()
    finally:
        server.shutdown()
        service.close()


if __name__ == "__main__":
    main()
