r"""Measure what each trim candidate actually saves, by compiling the paper without it.

The repository's rule is that ``latex/main.pdf`` is authoritative and a page count modelled
from word counts is not.  So rather than estimating, this compiles a variant of the paper
for each candidate cut and reports the real body length.

"Body length" is the last page carrying body text, plus the fraction of the following page
above the point where the excluded matter starts.  The workshop's 6-8 page limit excludes
references *and* appendices, so the body ends at whichever of the two comes first, and
``BODY_ENDS_AT`` therefore carries both headings and ``body_pages`` takes the earlier page.

That ``min()`` is load-bearing, and which marker wins has changed once already.  The paper
now runs body, references, appendix, checklist -- the order the official ``neurips_2026.tex``
demonstrates -- so the bibliography is what ends the body.  Under the previous order
``main.tex`` emitted the bibliography after all of ``\input{body}``, appendix included, and
measuring to it counted the whole appendix as body and read five pages long; the appendix
heading was what had to be found.  Keeping both markers is what makes the measurement
survive a reordering like that, so do not prune either one.

Nothing here writes to ``PAPER.md`` or to ``latex/``: each variant is built in a scratch
directory and thrown away.  Run it, read the table, then make the cut by hand.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAPER = HERE / "PAPER.md"
LATEX = HERE / "latex"


class AlreadyApplied(Exception):
    """A candidate's marker is not in the paper because the cut has already been made."""


def _drop_block(text: str, start_marker: str, end_marker: str) -> str:
    """Remove from ``start_marker`` up to (not including) ``end_marker``."""
    if start_marker not in text:
        raise AlreadyApplied(start_marker)
    start = text.index(start_marker)
    if end_marker not in text[start:]:
        # The start marker survives but the block has moved out from in front of the end
        # marker -- Figure 3 is in the appendix now, behind section 6 rather than ahead of it.
        raise AlreadyApplied(end_marker)
    end = text.index(end_marker, start)
    return text[:start] + text[end:]


def variant_full(text: str) -> str:
    return text


def variant_no_table1(text: str) -> str:
    """Table 1 (the case-level operating point) to the appendix; Table A4 already carries it."""
    return _drop_block(
        text,
        "**Table 1 | Case-level operating point behind each reported lead time.**",
        "## 4.3 What these findings do and do not license",
    )


def variant_no_figure1(text: str) -> str:
    """Figure 1 (lead against observed window) to the appendix beside Figure A1."""
    return _drop_block(
        text,
        "![](figures/Figure_2_wide.png)",
        "# 4 Score behavior behind the reported lead",
    )


def variant_no_table1_no_figure1(text: str) -> str:
    return variant_no_figure1(variant_no_table1(text))


#: The body is at the 8-page ceiling, so these are the two remaining floats that could be
#: relocated if an edit pushes it over.  Both are load-bearing -- Table 1 answers the "it just
#: alerts constantly" objection and Figure 1 is the paper's signature exhibit -- so neither is a
#: cut anyone should make without reading what it costs first.  The earlier candidates (the path
#: decomposition table and the alert-composition figure) are already in the appendix.
VARIANTS = {
    "full draft": variant_full,
    "- Table 1": variant_no_table1,
    "- Figure 1": variant_no_figure1,
    "- Table 1 and Figure 1": variant_no_table1_no_figure1,
}


#: The appendix heading as it renders, and the bibliography heading as the fallback. Order
#: matters: whichever appears on the earlier page ends the body.
BODY_ENDS_AT = ("Methods and complete per-cell results", "References")


def body_pages(pdf: Path) -> tuple[float, int]:
    """(estimated body pages, total pages).  Body ends where the excluded matter starts."""
    from pypdf import PdfReader

    pages = [(page.extract_text() or "") for page in PdfReader(pdf).pages]
    total = len(pages)
    found = [
        (i, text.index(marker), text)
        for marker in BODY_ENDS_AT
        for i, text in enumerate(pages, 1)
        if marker in text
    ]
    if not found:
        return float(total), total
    page_number, offset, text = min(found)
    # Where the heading falls in the page's extracted text is a serviceable proxy for how far
    # down the page the excluded matter starts, and it is only used for the fraction.
    return (page_number - 1) + offset / max(len(text), 1), total


def build(markdown: str, work: Path) -> Path:
    shutil.copytree(LATEX, work / "latex")
    shutil.copytree(HERE / "figures", work / "figures")
    (work / "PAPER.md").write_text(markdown)
    # build_tex.py copies references.bib next to main.tex on every run, so the scratch tree
    # needs it at the same relative position PAPER.md sits in.
    shutil.copyfile(HERE / "references.bib", work / "references.bib")
    for name in ("body.tex", "main.pdf", "main.aux", "main.bbl", "main.out"):
        (work / "latex" / name).unlink(missing_ok=True)
    # pandoc lives in base. Never `conda run -n torch bash -lc`: the login shell re-runs
    # conda init and resolves python to base.
    env = {"PATH": "/opt/anaconda3/bin:/usr/bin:/bin:/usr/sbin:/sbin"}
    subprocess.run(
        ["conda", "run", "-n", "tex", "python", "build_tex.py"],
        cwd=work / "latex", check=True, capture_output=True, env=env, text=True,
    )
    subprocess.run(
        ["conda", "run", "-n", "tex", "tectonic", "-X", "compile", "main.tex"],
        cwd=work / "latex", check=True, capture_output=True, env=env, text=True,
    )
    return work / "latex" / "main.pdf"


def main() -> None:
    text = PAPER.read_text()
    rows: list[tuple[str, float, int]] = []
    for label, transform in VARIANTS.items():
        with tempfile.TemporaryDirectory() as scratch:
            try:
                pdf = build(transform(text), Path(scratch))
            except AlreadyApplied as marker:
                # These candidates were measured, then actually cut, and the entries were
                # left behind pointing at markers the paper no longer contains.
                print(f"  {label:<24} already cut, no longer a candidate ({marker})")
                continue
            except subprocess.CalledProcessError as error:
                print(f"  {label}: build failed\n{error.stderr}")
                raise
            body, total = body_pages(pdf)
            rows.append((label, body, total))
            print(f"  {label:<24} body {body:5.2f} pp   total {total} pp", flush=True)

    baseline = rows[0][1]
    print("\n| Variant | Body pages | Saves | Total pages |")
    print("|---|---:|---:|---:|")
    for label, body, total in rows:
        saved = "-" if label == "full draft" else f"{baseline - body:.2f} pp"
        print(f"| {label} | {body:.2f} | {saved} | {total} |")
    print(
        f"\nLimit is 6-8 body pages, references and appendix excluded. "
        f"Full draft is {baseline:.2f}."
    )


if __name__ == "__main__":
    main()
