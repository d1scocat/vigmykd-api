import hashlib
import httpx


def pwd_ok(pwd: str) -> bool:
    return (
        8 <= len(pwd) <= 2048
        and any(c.isalpha() for c in pwd)
        and any(c.isdigit() for c in pwd)
    )


async def pwd_is_pwned(pwd: str) -> bool:
    sha1 = hashlib.sha1(pwd.encode("utf-8")).hexdigest().upper()
    prefix = sha1[:5]
    suffix = sha1[5:]

    async with httpx.AsyncClient() as client:
        response = await client.get(
            url=f"https://api.pwnedpasswords.com/range/{prefix}",
            headers={
                "Add-Padding": "true",
                "User-Agent": "vigmykd-api"
            },
            timeout=5
        )

    response.raise_for_status()
    for line in response.text.splitlines():
        hash_suffix, _ = line.split(":")
        if hash_suffix == suffix:
            return True

    return False
