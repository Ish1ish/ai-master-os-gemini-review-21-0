import os


class SecretManager:
    """
    Reads secrets only from environment variables and never persists them.
    """

    def get(self, name: str, required=True):
        value=os.getenv(name)
        if required and not value:
            raise RuntimeError(f"Missing required secret: {name}")
        return value

    def get_optional(self, name: str):
        return os.getenv(name)
