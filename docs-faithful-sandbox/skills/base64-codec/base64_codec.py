"""
Base64 encode / decode.

Usage:
    echo "hello" | python base64_codec.py encode
    echo "aGVsbG8=" | python base64_codec.py decode
"""

import base64
import sys


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in {"encode", "decode"}:
        print("Usage: python base64_codec.py {encode|decode}", file=sys.stderr)
        return 2

    mode = sys.argv[1]
    data = sys.stdin.read().rstrip("\n").encode("utf-8")

    if mode == "encode":
        print(base64.b64encode(data).decode("ascii"))
    else:
        print(base64.b64decode(data).decode("utf-8", errors="replace"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
