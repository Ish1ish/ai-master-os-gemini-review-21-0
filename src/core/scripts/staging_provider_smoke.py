import os
import sys

from src.live_providers import model_provider, search_provider, provider_configuration_status


def main():
    cfg = provider_configuration_status()
    if cfg["status"] != "CONFIGURED":
        print("STAGING_PROVIDER_SMOKE_NOT_RUN")
        print("missing=" + ",".join(cfg["missing"]))
        return 2
    # The actual request uses externally injected credentials and the configured endpoint URLs.
    # No credentials are printed or persisted by this script.
    model = model_provider("Reply with the single word READY.")
    search = search_provider("AI Master OS staging provider connectivity")
    print({"model": {"provider": model.get("provider"), "model": model.get("model"), "text_present": bool(model.get("text"))}, "search_results": len(search.get("results", []))})
    print("STAGING_PROVIDER_SMOKE_PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
