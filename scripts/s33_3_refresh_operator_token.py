from pathlib import Path
from core.src.auth import build_default_production_authenticator

root = Path(__file__).resolve().parents[1]
token_path = root / "staging" / "operator_token.txt"

auth, identity = build_default_production_authenticator()
result = identity.issue_token("operator-01")

token_path.parent.mkdir(parents=True, exist_ok=True)
with token_path.open("w", encoding="utf-8") as f:
    f.write(result["token"])

print("S33_3_TOKEN_REFRESHED")
