from pathlib import Path

from jwt import jwk_from_pem

from settings import config


class _Keys:
    def __init__(self) -> None:
        with open(Path(config.PRIVATE_KEY_PATH), "rb") as f:
            self.private_key = jwk_from_pem(f.read())

        with open(Path(config.PUBLIC_KEY_PATH), "rb") as f:
            self.public_key = jwk_from_pem(f.read())


keys = _Keys()
