#!/usr/bin/env python3
"""Sentence length in the PROSE of a Markdown file, for Simplified Technical English.

STE asks for one idea per sentence and twenty words or fewer. That is a rule
nobody applies from memory, so this measures it. Every public project in this
estate is held to STE, and a convention that is not measured is applied when
somebody remembers rather than when it matters.

WHAT COUNTS AS PROSE, stated so it can be argued with rather than discovered.
These are SKIPPED, because a word limit does not describe them:

  - fenced code blocks, everything between ``` markers
  - ATX headings, a line starting with #
  - table rows, a line starting with |
  - list markers and blockquote markers, stripped before the words are counted

An inline code span counts as ONE word. `consent.cookieName` is one term, and
splitting it on punctuation would inflate every sentence that names a field.

THERE IS NO IGNORE LIST and there will not be one. A scanner that can be told
to skip a line stops being a denominator: the entries get added, nobody
re-reads them, and the report goes green over prose it has quietly stopped
covering. Every sentence outside the skipped BLOCK TYPES above is counted, and
the report prints the count so a reader can see the denominator move.

Usage, status and output both meaningful:

    python3 tests/ste_lint.py README.md
    python3 tests/ste_lint.py --self-test
"""

from __future__ import annotations

import re
import sys

LIMIT = 20

FENCE = re.compile(r"^\s*```")
HEADING = re.compile(r"^\s*#")
TABLE_ROW = re.compile(r"^\s*\|")
LIST_MARKER = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+")
QUOTE_MARKER = re.compile(r"^\s*>\s?")
CODE_SPAN = re.compile(r"`[^`]*`")
LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")

#: Abbreviations whose full stop does not end a sentence.
ABBREV = ("e.g.", "i.e.", "etc.", "vs.", "cf.", "Mr.", "Dr.", "No.", "approx.")

#: A full stop, question mark or exclamation mark, then any CLOSING emphasis
#: or quote marks, then whitespace, then the start of the next sentence.
#: Requiring that next character bounds the split, so `v0.1.0` and `8.3` do
#: not read as two sentences.
#:
#: The closing-marker group is not decoration. Markdown bold puts the marker
#: AFTER the full stop, as in `end.** Next`, and without it the two sentences
#: merge into one and the merged length is reported against the first. That
#: made three sentences in this repo's own README look over the limit when
#: they were not, which is a linter inventing work rather than measuring it.
SENTENCE_END = re.compile(r"(?<=[.!?])[*_\"')\]]*\s+(?=[*_`\"(\[A-Z])")


def prose_lines(text: str) -> list[tuple[int, str]]:
    """(line_number, prose) for every line that carries countable prose."""
    out: list[tuple[int, str]] = []
    in_fence = False
    for n, raw in enumerate(text.splitlines(), start=1):
        if FENCE.match(raw):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if HEADING.match(raw) or TABLE_ROW.match(raw):
            continue
        line = QUOTE_MARKER.sub("", raw)
        line = LIST_MARKER.sub("", line)
        if not line.strip():
            continue
        out.append((n, line.strip()))
    return out


def paragraphs(text: str) -> list[tuple[int, str]]:
    """Join consecutive prose lines, keeping the line the paragraph starts on."""
    out: list[tuple[int, str]] = []
    start = 0
    buf: list[str] = []
    previous = None
    for n, line in prose_lines(text):
        if previous is not None and n != previous + 1:
            out.append((start, " ".join(buf)))
            buf = []
        if not buf:
            start = n
        buf.append(line)
        previous = n
    if buf:
        out.append((start, " ".join(buf)))
    return out


def count_words(sentence: str) -> int:
    """Words in a sentence, with each code span counted as one."""
    s = LINK.sub(r"\1", sentence)
    s = CODE_SPAN.sub(" CODESPAN ", s)
    return len([w for w in s.split() if any(c.isalnum() for c in w)])


def sentences(paragraph: str) -> list[str]:
    guarded = paragraph
    for i, a in enumerate(ABBREV):
        guarded = guarded.replace(a, "\x00%d\x00" % i)
    parts = SENTENCE_END.split(guarded)
    out = []
    for p in parts:
        for i, a in enumerate(ABBREV):
            p = p.replace("\x00%d\x00" % i, a)
        if p.strip():
            out.append(p.strip())
    return out


def measure(text: str, limit: int = LIMIT) -> tuple[int, list[tuple[int, int, str]]]:
    """Return (sentences_counted, [(line, words, sentence), ...] over the limit)."""
    counted = 0
    over: list[tuple[int, int, str]] = []
    for line, para in paragraphs(text):
        for s in sentences(para):
            counted += 1
            w = count_words(s)
            if w > limit:
                over.append((line, w, s))
    return counted, over


def self_test() -> int:
    """Controls in BOTH directions, because a linter nobody has seen fail is
    decoration. The negative cases matter most: a checker that skips too much
    reports zero for the same reason a clean file does."""
    long_sentence = " ".join("word%d" % i for i in range(25)) + "."
    cases = [
        ("a short sentence passes", "This is short.", 1, 0),
        ("a 25 word sentence is caught", long_sentence, 1, 1),
        (
            "a fenced block is not prose",
            "```\n%s\n```\n" % long_sentence,
            0,
            0,
        ),
        ("a heading is not prose", "# %s" % long_sentence, 0, 0),
        ("a table row is not prose", "| %s |" % long_sentence, 0, 0),
        (
            "a list item IS prose",
            "- %s" % long_sentence,
            1,
            1,
        ),
        (
            "a blockquote IS prose",
            "> %s" % long_sentence,
            1,
            1,
        ),
        (
            "a version number does not end a sentence",
            "The tag is v0.1.0 and it matches the header exactly today.",
            1,
            0,
        ),
        (
            "e.g. does not end a sentence",
            "Use a ref, e.g. origin/main, rather than a sha.",
            1,
            0,
        ),
        (
            "two sentences are counted separately",
            "This is one. This is two.",
            2,
            0,
        ),
        (
            "a code span counts as one word",
            "`a.b.c.d.e.f.g.h` is one term here.",
            1,
            0,
        ),
        (
            "a long sentence made of code spans is still caught",
            " ".join("`c%d`" % i for i in range(25)) + " end.",
            1,
            1,
        ),
        # The bold-marker shapes. Each of these merged into one sentence before
        # the closing-marker group was added, and the merged count was then
        # reported as an over-limit finding against prose that was fine.
        (
            "a sentence ending in bold splits from the next",
            "**This is bold.** This is after it.",
            2,
            0,
        ),
        (
            "a sentence followed by a bold one splits",
            "Plain first. **Bold second.**",
            2,
            0,
        ),
        (
            "a sentence followed by a quotation splits",
            'He said this. "Then a quotation follows here."',
            2,
            0,
        ),
        (
            "bold on both sides still splits",
            "**One.** **Two.**",
            2,
            0,
        ),
    ]
    failures = 0
    for name, text, want_counted, want_over in cases:
        counted, over = measure(text)
        ok = counted == want_counted and len(over) == want_over
        failures += not ok
        print(
            "  %-52s counted=%d/%d over=%d/%d %s"
            % (name, counted, want_counted, len(over), want_over, "ok" if ok else "FAIL")
        )
    print("cases_run=%d failed=%d" % (len(cases), failures))
    if failures:
        print("ste_lint self-test: FAILED")
        return 1
    print("ste_lint self-test: COMPLETE")
    return 0


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return self_test()
    if not argv:
        print("usage: ste_lint.py <file.md> [more.md ...]", file=sys.stderr)
        return 2
    total = 0
    bad = 0
    for path in argv:
        with open(path, encoding="utf-8") as handle:
            counted, over = measure(handle.read())
        total += counted
        bad += len(over)
        print("%s: %d sentences, %d over %d words" % (path, counted, len(over), LIMIT))
        for line, words, sentence in over:
            print("  %s:%d  %d words" % (path, line, words))
            print("    %s" % (sentence[:140] + ("..." if len(sentence) > 140 else "")))
    print("TOTAL: %d sentences, %d over %d words" % (total, bad, LIMIT))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
