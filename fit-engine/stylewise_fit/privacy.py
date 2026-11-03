"""Remove personal details from chat text before it leaves the server for the Meta Model API.

Measurements such as "165 cm" or "bust 92" are kept: they are what the user asked about, and the
caller decides separately (consent) whether they may be sent. Patterns are deliberately broad.
"""
import re

_PATTERNS = [
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[email]"),
    (re.compile(r"https?://\S+|www\.\S+"), "[link]"),
    (re.compile(r"\b(?:\d[ -]?){13,19}\b"), "[card number]"),
    (re.compile(r"(?<![\d.])\+?\d[\d ()-]{7,}\d(?![\d.]*\s*(?:cm|in|inch|kg)\b)"), "[phone]"),
    (re.compile(r"(?i)\b(my name is|i am called|i'm called|call me|this is)\s+[A-Z][\w'-]*(\s+[A-Z][\w'-]*)?"),
     r"\1 [name]"),
    (re.compile(r"(?i)\b(i live (?:at|in|on)|my address is|address:)\s+[^.,\n]+"), r"\1 [address]"),
    (re.compile(r"(?i)\b(singapore|india|pin(?:code)?)\s*\d{6}\b"), r"\1 [postcode]"),
]


def scrub(text: str) -> str:
    for pattern, replacement in _PATTERNS:
        text = pattern.sub(replacement, text)
    return text
