import re


NAME_VALIDITY_PATTERN = re.compile(
    r"""
    ^(?=.{3,32}$)               # length
    [A-Za-z0-9]                 # first char
    (?:                         # middle
        [A-Za-z0-9]
        |
        [_-][A-Za-z0-9]
    )*
    [_-]?$                      # optional trailing underscore/dash
    """,
    re.VERBOSE,
)


def name_ok(nick: str) -> bool:
    return NAME_VALIDITY_PATTERN.fullmatch(nick) is not None
