"""Prohibited phrasing, with the required replacement for each.

Two kinds of entry live here.

**Carried over** from an earlier phrase table, because the same terminology
decisions apply: `alarm` -> `alert`, `justify` -> `provides an empirical basis for`,
`prospective validation` -> `retrospective forward-running simulation`, `online simulation`
-> `deployment simulation`.

**Specific to this paper.**

* `faithfulness` is banned as a bare word, not merely in the bigram it usually appears in.
  The construct is not needed for this argument and is avoided throughout. Banning
  the bare word rather than the two-word phrase matters because a line break between the two
  words would defeat a bigram pattern.
* Claims that the score anticipates or tracks physiology are banned outright. The outcome is
  a sustained excursion of mean arterial pressure and mean arterial pressure is one of the
  model's input channels, so the model reads the quantity the label is computed from. No
  result here licenses a statement about anticipating a physiological process.
* Recommending suppression of the warm-up window is banned. It was tested and it fails --
  3.6 to 6.8 points of sensitivity for 0 to 3.2 points of specificity -- and the paper
  reports that as a result rather than proposing it as a remedy.

Three things this file cannot check, and a human must read for:

1. whether the plateau is *described* as a defect of one architecture, which is a claim
   rather than a string;
2. whether suppression is recommended by implication rather than by the word;
3. whether any citation is phrased in a way the reference list does not support.

Exit status is 1 if anything outside the allowlist matches, so this can gate a commit.
"""

from __future__ import annotations

import re
from pathlib import Path

HERE = Path(__file__).resolve().parent

PROHIBITED: dict[str, str] = {
    r"\bfaithfulness\b": (
        "name the property directly -- 'discrimination rises toward onset' -- and do not "
        "use the construct in this paper"
    ),
    r"\balarms?\b": "alert",
    r"\bjustif(?:y|ies|ied)\b": "provides an empirical basis for",
    r"prospective validation": "retrospective forward-running simulation",
    r"online simulation": "deployment simulation",
    r"anticipat(?:e|es|ed|ing)\s+(?:the\s+)?(?:patho)?physiolog": (
        "the outcome is defined on MAP and MAP is an input channel; say what was measured"
    ),
    r"learn(?:s|ed|ing)?\s+(?:the\s+)?(?:patho)?physiolog": (
        "the outcome is defined on MAP and MAP is an input channel; say what was measured"
    ),
    r"track(?:s|ed|ing)?\s+the\s+(?:underlying\s+)?(?:patho)?physiolog": (
        "the outcome is defined on MAP and MAP is an input channel; say what was measured"
    ),
    r"predicts?\s+deterioration\s+before": (
        "state the measured quantity, not an inferred physiological precedence"
    ),
    r"(?:recommend|propose|suggest)\w*\s+(?:\w+\s+){0,3}suppress": (
        "B1b tested warm-up suppression and it fails; report it, never recommend it"
    ),
    r"we\s+previously\s+(?:show|propos|report|develop)": (
        "third person -- the prior work is cited, never claimed"
    ),
    r"our\s+(?:previous|earlier|prior)\s+(?:study|work|paper|model)": (
        "third person -- the prior work is cited, never claimed"
    ),
}

#: Each entry is (file suffix, regex that must match the *line*, why it stands).
#: Deliberately narrow. If new documentation needs to discuss a banned term, reword it
#: rather than widening this list, or a real hit will hide behind the exemption.
ALLOWLIST: list[tuple[str, str, str]] = [
    (
        "check_phrases.py",
        r".",
        "This file necessarily contains the patterns it searches for.",
    ),
    (
        "references.bib",
        r"physiologic monitor alarm characteristics",
        "Paine 2016's published title. A title is quoted, never edited.",
    ),
]

SEARCH_SUFFIXES = {".md", ".bib", ".py"}
SKIP_DIRS = {"figures", "tables", "latex", "__pycache__"}

#: Generated composites are skipped, not allowlisted.  REVIEW.md embeds this file's own
#: docstring and every other script's, so scanning it would report this file's patterns a
#: second time under a different path -- and worse, a real hit inside it is already caught at
#: its source, since every part of it is generated from a file that IS scanned.
#: PAPER_REVIEW.md is PAPER.md with citations resolved, so the same argument applies.
#: references_unused.bib holds entries the paper does not cite, kept for reuse; no build
#: reads it, so a prohibited word inside a published title there cannot reach the paper.
#: The moment such an entry is cited it moves into references.bib, which IS scanned.
SKIP_FILES = {"REVIEW.md", "PAPER_REVIEW.md", "references_unused.bib"}


def allowed(path: Path, line: str) -> str | None:
    for suffix, pattern, reason in ALLOWLIST:
        if path.name.endswith(suffix) and re.search(pattern, line, re.IGNORECASE):
            return reason
    return None


def main() -> int:
    hits: list[str] = []
    allowed_hits = 0
    files = [
        path
        for path in sorted(HERE.rglob("*"))
        if path.suffix in SEARCH_SUFFIXES
        and path.name not in SKIP_FILES
        and not any(part in SKIP_DIRS for part in path.relative_to(HERE).parts)
    ]
    for path in files:
        for number, line in enumerate(path.read_text().splitlines(), 1):
            for pattern, replacement in PROHIBITED.items():
                if re.search(pattern, line, re.IGNORECASE):
                    reason = allowed(path, line)
                    if reason:
                        allowed_hits += 1
                        continue
                    hits.append(
                        f"{path.relative_to(HERE)}:{number}\n"
                        f"    matched: {pattern}\n"
                        f"    use instead: {replacement}\n"
                        f"    line: {line.strip()[:110]}"
                    )
    if hits:
        print(f"{len(hits)} prohibited phrase(s) found\n")
        for hit in hits:
            print(hit + "\n")
        return 1
    print(
        f"clean — no prohibited phrasing across {len(files)} file(s) "
        f"({allowed_hits} allowlisted hit(s) skipped)"
    )
    print(
        "\nStill needs a human read: is the plateau described as a defect of one "
        "architecture? is suppression recommended by implication? is any citation phrased in a way the reference list does not support, in "
        "the first person?"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
