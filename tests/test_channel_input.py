"""Unit tests for the channel-id input parser (admin kanal qo'shish).

Verifies the accepted formats:
  * @username
  * https://t.me/username  (and t.me/username without scheme, with query/trailing slashes)
  * numeric ids (positive digits -> -100 prefix added automatically)
and that every other input raises ValueError.

Run with::

    python tests/test_channel_input.py
"""
from __future__ import annotations

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ["BOT_TOKEN"] = "1111111110:TEST-TOKEN"
os.environ["ADMIN_IDS"] = "111111,222222"

from handlers.admin import _canonical_channel_input  # noqa: E402


def check(value: str, expected: str) -> None:
    got = _canonical_channel_input(value)
    assert got == expected, f"{value!r}: expected {expected!r}, got {got!r}"
    print(f"[ OK ] {value!r} -> {got!r}")


def should_fail(value: str) -> None:
    try:
        _canonical_channel_input(value)
        raise AssertionError(f"{value!r} should have raised ValueError")
    except ValueError:
        print(f"[ OK ] {value!r} -> rejected")


def main() -> None:
    # --- accepted -------------------------------------------------------
    check("@vento_news", "@vento_news")
    check("https://t.me/vento_news", "@vento_news")
    check("https://t.me/vento_news/", "@vento_news")           # trailing slash
    check("https://t.me/vento_news?start=1", "@vento_news")    # query string
    check("t.me/vento_news", "@vento_news")                    # no scheme
    check("1234567890", "-1001234567890")                      # auto -100
    check("-1001234567890", "-1001234567890")                  # already prefixed
    check("-12345", "-12345")                                  # plain group id
    check("   @kanalnomi   ", "@kanalnomi")                    # whitespace trimmed

    # --- rejected -------------------------------------------------------
    should_fail("")
    should_fail("   ")
    should_fail("https://t.me/+abc123xyz")                     # invite link
    should_fail("vento_news")                                  # bare username
    should_fail("abc")
    should_fail("-abc")
    should_fail("12abc")


if __name__ == "__main__":
    main()
    print("\nALL CHANNEL INPUT TESTS PASSED ✔")