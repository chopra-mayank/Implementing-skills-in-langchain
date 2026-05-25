"""
Deterministic text statistics. Reads text from stdin, writes JSON to stdout.

Usage:
    echo "your text" | python text_stats.py
"""

import json
import re
import sys
from collections import Counter


def analyze(text: str) -> dict:
    words = re.findall(r"\w+", text.lower())
    sentences = [s for s in re.split(r"[.!?]+", text) if s.strip()]
    return {
        "char_count":     len(text),
        "word_count":     len(words),
        "unique_words":   len(set(words)),
        "sentence_count": len(sentences),
        "top_5":          Counter(words).most_common(5),
    }


if __name__ == "__main__":
    text = sys.stdin.read()
    print(json.dumps(analyze(text), indent=2))
