from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class ReleaseManifest:
    product: str
    release: str
    channel: str
    built_at: str
    minimum_python: str
    entrypoint: str
    release_gate: str
    notes: str

    def to_dict(self):
        return asdict(self)

    def write(self, path):
        Path(path).write_text(
            __import__("json").dumps(self.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


def create_manifest():
    return ReleaseManifest(
        product="AI Master OS",
        release="O38-v1.4.0",
        channel="production-hardening-candidate",
        built_at=datetime.now(timezone.utc).isoformat(),
        minimum_python="3.10+",
        entrypoint="python -m src.cli",
        release_gate="O38 PRODUCTION SECURITY + LIVE DEPLOYMENT HARDENING",
        notes="Fail-closed production authentication, mandatory identity secret, loopback deployment, TLS edge topology, live-provider adapters, durable SQLite backup/restore controls, exact canonical handoff identity binding, bounded semantic fields, raw evidence isolation, prompt-injection boundary checks, offline failure-injection gates, idempotent memory writes, and evaluation lifecycle isolation.",
    )
