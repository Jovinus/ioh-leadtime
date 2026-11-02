"""Convert PAPER.md into a NeurIPS-style LaTeX body.

PAPER.md stays the single source of truth; this is a build step, not a fork.
Run it again after any edit to the markdown.

Two things pandoc does not do for us:

1. **Unicode.** The style file sets Times via ``\\rmdefault{ptm}``, a Type 1 font
   with no Greek and no maths glyphs, so a bare τ or ρ silently drops out or
   errors even under XeTeX. Every such character is mapped into maths mode.
2. **Figure floats.** pandoc emits a bare ``\\includegraphics`` followed by the
   caption as an ordinary bold paragraph. Each is wrapped into a ``figure[!tb]``
   with a real ``\\caption`` so LaTeX can place and number it.  ``[t]`` alone left the body
   figure stranded on a page that then carried only 28 of its ~48 lines; allowing the bottom
   and overriding the float-fraction limits recovers that page without shrinking anything.

Tables are left as ``longtable``. Table 1 is 21 data rows across two blocks and
a non-floating environment that can break across a page boundary is easier to
fit than a float that must be placed whole.

Run:
    export PATH="$PATH:/opt/anaconda3/bin"
    conda run -n tex python build_tex.py
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAPER = HERE.parent / "PAPER.md"

# Greek, maths and typographic characters that ptm cannot set.
#: Placement for every figure this script emits.  ``H`` from the float package pins the float
#: exactly where its source sits, which is what both halves of the paper need: in the body it
#: keeps Figure 1 from splitting the sentence that introduces it, and in the appendix it keeps
#: each figure inside the subsection that introduces it.  ``[t]`` stranded a body page at 28 of
#: its ~48 lines, and ``[!tb]`` let floats drift past the heading of the following subsection.
FIGURE_PLACEMENT = "[H]"

UNICODE_MATH = {
    "τ": r"$\tau$",
    "ρ": r"$\rho$",
    "Δ": r"$\Delta$",
    "α": r"$\alpha$",
    "×": r"$\times$",
    "≥": r"$\ge$",
    "≤": r"$\le$",
    "−": "$-$",
    "±": r"$\pm$",
    "→": r"$\rightarrow$",
    "§": r"\S",
    "⁻": "^-",
    "⁰": "$^{0}$",
    "¹": "$^{1}$",
    "²": "$^{2}$",
    "³": "$^{3}$",
    "⁴": "$^{4}$",
    "⁵": "$^{5}$",
    "⭐": "",
    "⚠": "",
    "⛔": "",
}

# "1.5 × 10⁻⁵" survives the per-character map as "$\times$ 10^-$^{5}$", which is
# wrong. Catch the whole construct first.
SCI_NOTATION = re.compile(r"(\d(?:\.\d+)?)\s*×\s*10⁻([⁰¹²³⁴⁵⁶⁷⁸⁹]+)")
SUPERSCRIPT_DIGITS = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")


def fix_unicode(text: str) -> str:
    text = SCI_NOTATION.sub(
        lambda m: rf"${m.group(1)} \times 10^{{-{m.group(2).translate(SUPERSCRIPT_DIGITS)}}}$",
        text,
    )
    for char, replacement in UNICODE_MATH.items():
        text = text.replace(char, replacement)
    return text


# The caption's label and the filename's number are deliberately decoupled: the filename is
# an artefact path fixed by whichever script produced the figure, while the label is
# editorial and changes when a figure moves between the body and the appendix (Figure 3 ->
# Figure 2). Requiring them to match, as an earlier version did with a backreference,
# silently stopped wrapping the figure the moment it was renumbered.
FIGURE_BLOCK = re.compile(
    r"\\includegraphics(?:\[[^\]]*\])?\{(?P<path>[^}]*Figure_[^}]*\.png)\}"
    r"\s*\n\s*\n"
    # pandoc renders the caption's "|" separator as \textbar{}.
    r"(?P<caption>\\textbf\{Figure\s*(?P<num>A?\d+)\s*\\textbar\{\}.*?)(?=\n\n)",
    re.DOTALL,
)


def _vector(path: str) -> str:
    """Point the LaTeX build at the figure's PDF rather than its PNG.

    ``PAPER.md`` references the PNGs because ``render.sh`` produces a DOCX and Word cannot
    embed a PDF image.  LaTeX has no such limit, and the vector files are both better and far
    cheaper: the six figures are 280 KB as PDF against 1.8 MB as 500-dpi PNG.  That mattered
    once the bundle went to Overleaf, whose free tier killed the compile on the timeout while
    pdfTeX was decoding the rasters.  The inch dimensions are identical -- both come from the
    same ``savefig`` call -- so the layout does not move.
    """
    return path[: -len(".png")] + ".pdf" if path.endswith(".png") else path


def wrap_figures(text: str) -> str:
    def repl(match: re.Match) -> str:
        caption = " ".join(match.group("caption").split())
        # LaTeX supplies "Figure N:" itself; leaving the markdown's own
        # "Figure N |" prefix in place renders "Figure 1: Figure 1 | ...".
        caption = re.sub(
            r"^\\textbf\{Figure\s*A?\d+\s*\\textbar\{\}\s*", r"\\textbf{", caption
        )
        return (
            f"\\begin{{figure}}{FIGURE_PLACEMENT}\n"
            "  \\centering\n"
            f"  \\includegraphics[width=\\linewidth]{{{_vector(match.group('path'))}}}\n"
            f"  \\caption{{{caption}}}\n"
            f"  \\label{{fig:{match.group('num')}}}\n"
            "\\end{figure}"
        )

    expected = len(re.findall(r"^!\[\]\(", PAPER.read_text(), flags=re.MULTILINE))
    text, n = FIGURE_BLOCK.subn(repl, text)
    # Derived from the markdown rather than hardcoded: a figure whose caption paragraph
    # does not immediately follow its image is silently left unwrapped by the pattern, and
    # a fixed count would only catch that while the paper happened to have that many
    # figures.
    if n != expected:
        raise AssertionError(
            f"PAPER.md has {expected} image(s) but {n} were wrapped into figure floats; "
            "check that each image is followed directly by its bold caption paragraph"
        )
    return text


#: An appendix table as pandoc leaves it: the bold caption paragraph, a blank line, then the
#: longtable. Both go into one minipage so a page break cannot fall between them.
APPENDIX_TABLE = re.compile(
    r"^(?P<caption>\\textbf\{Table A\d+ \\textbar\{\}.*?)\n\n"
    r"(?P<table>\\begin\{longtable\}.*?\\end\{longtable\})",
    re.DOTALL | re.MULTILINE,
)


#: A table with more row breaks than this cannot fit a page, so it must stay a ``longtable``
#: and break across pages.  Table A3 is 51 rows; forcing it into an unbreakable ``tabular``
#: inside a minipage produced a 923pt overfull vbox, which shipped an empty page before it and
#: then ran the table off the bottom of the next one.  Every other appendix table is 14 to 16
#: rows and fits comfortably.
MAX_ROWS_FOR_TABULAR = 30

#: Natural ``l``/``r`` column widths only help a table whose cells are short labels and
#: numbers.  Table A10's cells are sentences, and swapping pandoc's ``p{...}`` widths for
#: natural ones stopped them wrapping and pushed a line 651pt past the right margin.
MAX_CELL_FOR_NATURAL_WIDTHS = 40


def _longest_cell(table: str) -> int:
    """The longest cell in the table body, in characters, ignoring the column preamble."""
    body = table[table.index("\\toprule"):] if "\\toprule" in table else table
    widest = 0
    for line in body.splitlines():
        if "&" not in line:
            continue
        for cell in line.split("&"):
            widest = max(widest, len(cell.strip().rstrip("\\\\").strip()))
    return widest


def _anchor_appendix_exhibits(text: str) -> tuple[str, int]:
    """Pin appendix tables and figures in place. Returns (text, exhibits changed)."""
    marker = "\\appendix"
    if marker not in text:
        return text, 0
    head, tail = text.split(marker, 1)

    def repl(match: "re.Match[str]") -> str:
        table = match.group("table")
        # A table too tall for a page has to keep longtable's page-breaking machinery, and it
        # must not go into a minipage either, because a minipage cannot break at all.  Leave
        # the caption paragraph in front of it and let it flow.
        if table.count("\\\\\n") > MAX_ROWS_FOR_TABULAR:
            return match.group("caption").strip() + "\n\n" + table
        # longtable's page-breaking machinery is what split Table A5 and repeated its header;
        # a tabular cannot split at all.
        table = table.replace("\\begin{longtable}[]", "\\begin{tabular}", 1)
        table = table.replace("\\end{longtable}", "\\end{tabular}", 1)
        table = re.sub(r"\n\\end(?:head|firsthead|lastfoot|foot)\n", "\n", table)
        # pandoc sizes columns from content length, which wraps every label cell and makes
        # each row double height. Table A5 is narrow enough to take natural widths, which
        # give single-line rows. The wider two keep pandoc's widths: natural widths put
        # Table A4 291pt past the text block, and widening its label columns out of the
        # numeric ones only moved the wrapping into the confidence intervals, which made the
        # table taller rather than shorter.
        # Measure data rows only: pandoc 3 sets header cells in minipages, whose markup lines
        # would otherwise count as 60-character "cells" and block natural widths everywhere.
        data_rows = table[table.index("\\midrule"):] if "\\midrule" in table else table
        if (
            table.count("arraybackslash") <= 6
            and _longest_cell(data_rows) <= MAX_CELL_FOR_NATURAL_WIDTHS
        ):
            table = re.sub(
                r"\\begin\{minipage\}\[b\]\{\\linewidth\}\\(?:raggedright|raggedleft)\s*(.*?)\s*\\end\{minipage\}",
                r"\1", table, flags=re.DOTALL,
            )
            table = re.sub(
                r"\n?\s*>\{\\raggedright\\arraybackslash\}p\{[^{}]*\{[^{}]*\}[^{}]*\}",
                "l",
                table,
            )
            table = re.sub(
                r"\n?\s*>\{\\raggedleft\\arraybackslash\}p\{[^{}]*\{[^{}]*\}[^{}]*\}",
                "r",
                table,
            )
        return (
            "\\begin{minipage}{\\linewidth}\n"
            + match.group("caption").strip()
            + "\n\n\\vspace{0.5em}\n\\centering\\footnotesize\n"
            + table
            + "\n\\end{minipage}\n\n\\vspace{0.8em}"
        )

    tail, n_tables = APPENDIX_TABLE.subn(repl, tail)
    # [H] pins the figure exactly where its subsection puts it, which is the requirement
    # here: nearly every appendix subsection is a heading plus one exhibit, and the exhibit
    # has to appear before the next heading. [!ht] packed the pages better but let a figure
    # drift past the following heading, which put two consecutive subsections on the page as bare titles.
    # The cost is slack at the foot of a page, which \raggedbottom collects. [H] needs the
    # float package, loaded in main.tex. Body figures keep [t]: the body is against the page
    # limit and its pagination must not move.
    # Figures are already emitted with FIGURE_PLACEMENT, so nothing is rewritten here; the
    # count is kept so the caller's "exhibits changed" total still reports the tables.
    n_figs = 0
    return head + marker + tail, n_tables + n_figs

def main() -> None:
    raw = subprocess.run(
        [
            "pandoc",
            str(PAPER),
            "--from=markdown",
            "--to=latex",
            "--natbib",
            "--wrap=preserve",
            "--top-level-division=section",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    # pandoc wraps every heading in \hypertarget{..}{% \section{..}\label{..}}.
    # The wrapper defeats any pattern that expects \section at the start of a
    # line -- which is why the abstract conversion below silently did nothing and
    # Abstract came out as section 1, shifting every later number by one.
    raw = re.sub(
        r"\\hypertarget\{[^}]*\}\{%\s*\n(\\(?:sub)*section\{.*?\}\{[^}]*\})\}",
        r"\1",
        raw,
    )
    raw = re.sub(
        r"\\hypertarget\{[^}]*\}\{%\s*\n(\\(?:sub)*section\{[^}]*\}\\label\{[^}]*\})\}",
        r"\1",
        raw,
    )

    # pandoc 3.x wraps every image as \pandocbounded{\includegraphics[keepaspectratio]{..}};
    # 2.12 emitted the bare \includegraphics the figure pattern expects. Unwrap so both work.
    # (Base's pandoc 2.12 is x86_64 and no longer runs on this machine; the build now uses an
    # arm64 pandoc 3.8 -- see README.)
    raw = re.sub(
        r"\\pandocbounded\{(\\includegraphics(?:\[[^\]]*\])?\{[^}]*\})\}", r"\1", raw
    )
    # pandoc 3.x longtables carry a separate first head and a foot (\endfirsthead ...
    # \endlastfoot) with the \bottomrule up front; 2.12 emitted one \endhead and put the
    # \bottomrule last. Everything below (and the tabular conversion of appendix tables) was
    # written for the 2.12 shape, so normalise to it.
    raw = re.sub(r"\\endfirsthead\n.*?\\endlastfoot\n", "\\\\endhead\n", raw, flags=re.DOTALL)
    raw = re.sub(r"\n\\end\{longtable\}", "\n\\\\bottomrule\\\\noalign{}\n\\\\end{longtable}", raw)
    body = wrap_figures(fix_unicode(raw))

    # A source path inside \texttt cannot hyphenate, and the longest of them overflowed the
    # text block by 13pt. Allow a break after each separator; \allowbreak adds no glyph.
    def _breakable(match: "re.Match[str]") -> str:
        inner = match.group(1)
        inner = inner.replace("/", "/\\allowbreak{}").replace("\\_", "\\_\\allowbreak{}")
        return "\\texttt{" + inner + "}"

    body = re.sub(r"\\texttt\{([^{}]*)\}", _breakable, body)

    # pandoc sizes longtable columns by content length, which on the nine-column Table A4
    # left the model column too narrow for "Transformer" and pushed the row 9.5pt past the
    # text block. Widen the label column out of the two widest columns, which hold five
    # characters each and have width to spare. Narrower tables are left alone.
    def _rebalance(match: "re.Match[str]") -> str:
        table = match.group(0)
        head = table[: table.index("\\toprule")]
        widths = [float(w) for w in re.findall(r"\\real\{([\d.]+)\}", head)]
        if len(widths) < 8:
            return table
        donors = sorted(range(len(widths)), key=lambda i: -widths[i])[:2]
        widths[0] += 0.03
        for i in donors:
            widths[i] -= 0.015
        out, seen = [], iter(widths)
        new_head = re.sub(
            r"\\real\{[\d.]+\}", lambda _: f"\\real{{{next(seen):.3f}}}", head
        )
        return new_head + table[table.index("\\toprule"):]

    body = re.sub(
        r"\\begin\{longtable\}.*?\\end\{longtable\}", _rebalance, body, flags=re.DOTALL
    )

    # Body tables of short numeric cells (Table 2) get natural column widths: pandoc's p{}
    # widths wrapped every row of it onto two lines. Tables of sentences (Tables 1 and 3) keep
    # pandoc's widths. Only the body is touched here; the appendix has its own handling below.
    def _natural(match: "re.Match[str]") -> str:
        table = match.group(0)
        # Data rows only: longtable repeats its minipage header after each \\midrule.
        rows = table[table.index("\\endlastfoot"):] if "\\endlastfoot" in table else table
        if _longest_cell(rows) > 30:
            return table
        table = re.sub(r"\n?\s*>\{\\raggedright\\arraybackslash\}p\{[^{}]*\{[^{}]*\}[^{}]*\}", "l", table)
        table = re.sub(r"\n?\s*>\{\\raggedleft\\arraybackslash\}p\{[^{}]*\{[^{}]*\}[^{}]*\}", "r", table)
        # Header cells were wrapped in minipages sized to the old p{} widths.
        table = re.sub(r"\\begin\{minipage\}\[b\]\{\\linewidth\}\\(?:raggedright|raggedleft)\s*(.*?)\s*\\end\{minipage\}", r"\1", table, flags=re.DOTALL)
        return table

    if "\\section{Appendix A:" in body:
        _head, _tail = body.split("\\section{Appendix A:", 1)
        _head = re.sub(r"\\begin\{longtable\}.*?\\end\{longtable\}", _natural, _head, flags=re.DOTALL)
        # Body tables are short (4 to 15 rows), so each becomes an unsplittable tabular in a
        # minipage with its caption: as a longtable, Table 2's caption stranded at the foot of
        # one page with the rows on the next.
        def _keep_with_caption(m: "re.Match[str]") -> str:
            table = m.group("table")
            table = table.replace("\\begin{longtable}[]", "\\begin{tabular}", 1)
            table = table.replace("\\end{longtable}", "\\end{tabular}", 1)
            table = re.sub(r"\n\\end(?:head|firsthead|lastfoot|foot)\n", "\n", table)
            return ("\\begin{table}[t]\n" + m.group("caption").strip()
                    + "\n\n\\vspace{0.4em}\n\\centering\\footnotesize\n" + table
                    + "\n\\end{table}")
        _head, n_body_tables = re.subn(
            r"^(?P<caption>\\textbf\{Table \d+ \\textbar\{\}.*?)\n\n"
            r"(?P<table>\\begin\{longtable\}.*?\\end\{longtable\})",
            _keep_with_caption, _head, flags=re.DOTALL | re.MULTILINE,
        )
        if n_body_tables != 3:
            raise AssertionError(f"expected 3 body tables, wrapped {n_body_tables}")
        body = _head + "\\section{Appendix A:" + _tail

    # The markdown abstract is a section; LaTeX wants the abstract environment.
    body = re.sub(
        r"\\section\{Abstract\}(?:\\label\{[^}]*\})?\s*\n+(.*?)(?=\n\\section\{)",
        lambda m: "\\begin{abstract}\n" + m.group(1).strip() + "\n\\end{abstract}\n",
        body,
        count=1,
        flags=re.DOTALL,
    )
    # Camera-ready: the acknowledgments section becomes the style file's `ack` environment,
    # which prints the official unnumbered "Acknowledgments and Disclosure of Funding" heading.
    body, n_ack = re.subn(
        r"\\section\{Acknowledgments and Disclosure of Funding\}(?:\\label\{[^}]*\})?\s*\n+(.*?)(?=\n\\section\{|\Z)",
        lambda m: "\\begin{ack}\n" + m.group(1).strip() + "\n\\end{ack}\n\n",
        body,
        count=1,
        flags=re.DOTALL,
    )
    if n_ack != 1:
        raise AssertionError("acknowledgments section not converted to the ack environment")
    # Section numbers come from LaTeX, so strip the ones carried in the headings.
    body = re.sub(r"\\section\{(\d+)\s+", r"\\section{", body)
    body = re.sub(r"\\subsection\{(\d+\.\d+)\s+", r"\\subsection{", body)
    # pandoc renders the empty "References" heading; natbib emits the real one.
    body = re.sub(r"\\section\{References\}\s*", "", body)
    # The appendix gets LaTeX's appendix numbering, and its figures get A-numbers.
    #
    # This was a literal string match on the *shelved* module's appendix title
    # ("complete horizon grid") for as long as this module has existed, so it never fired:
    # the appendix rendered as a numbered section with "Appendix A:" also spelled out in the
    # heading, and -- because \appendix alone does not touch the figure counter -- the
    # appendix figures continued the body's sequence and came out as "Figure 3" and
    # "Figure 4" where the markdown calls them A1 and A2. Matched on the pattern and
    # asserted now, so retitling the appendix cannot silently reintroduce it.
    body, appendices = re.subn(
        r"\\section\{Appendix A: (?P<title>[^}]*)\}(?:\\label\{[^}]*\})?",
        lambda m: (
            # The appendix starts on a fresh page rather than partway down the last body
            # page, which also flushes any body float still pending ahead of it.
            "\\clearpage\n"
            "\\appendix\n"
            # Exhibits are pinned in the appendix, so what is left over is genuine slack at
            # the foot of a page. \raggedbottom puts it there instead of stretching the gaps
            # between paragraphs. Set after \appendix so the body, which is against the page
            # limit, keeps \flushbottom and its current pagination.
            "\\raggedbottom\n"
            # The submitted PDF concatenates body, appendix and checklist, so the appendix
            # heading says so instead of relying on the reader to read a bare "A" as
            # "Appendix A". \thesubsection has to be reset too: article derives it from
            # \thesection, which would otherwise give "Appendix A.1" on every subsection.
            "\\renewcommand{\\thesection}{Appendix \\Alph{section}}\n"
            "\\renewcommand{\\thesubsection}{\\Alph{section}.\\arabic{subsection}}\n"
            # \appendix renumbers sections only. Without these two the appendix figures
            # keep counting on from the body and no A-prefix appears.
            "\\setcounter{figure}{0}\n"
            "\\renewcommand{\\thefigure}{A\\arabic{figure}}\n"
            # hyperref names its anchors from \\theH<counter>, which resetting the visible
            # counter does not touch, so body Figure 2 and appendix Figure A2 would both
            # claim the "figure.2" anchor ("Object @figure.2 already defined").
            "\\renewcommand{\\theHfigure}{A\\arabic{figure}}\n"
            f"\\section{{{m.group('title')[:1].upper()}{m.group('title')[1:]}}}"
        ),
        body,
        count=1,
    )
    if appendices != 1:
        raise AssertionError(
            "the appendix heading was not matched, so \\appendix was not emitted; "
            "PAPER.md's appendix must start with a '# Appendix A: <title>' heading"
        )

    # Nearly every appendix subsection is a heading plus one exhibit, so the exhibits must
    # stay where their headings are. Two earlier attempts failed on that: a forced page break
    # before each longtable left 288pt blank on one page, and moving the tables into floats
    # emptied six consecutive subsections, which rendered as a stack of bare headings on one
    # page while their tables sat elsewhere. So the tables are anchored, and only made
    # unsplittable: a tabular inside a minipage with its caption, which page-breaks before
    # itself rather than through itself. Appendix figures are pinned with [H] for the same
    # reason.
    body, anchored = _anchor_appendix_exhibits(body)
    if anchored == 0:
        raise AssertionError("no appendix exhibits were anchored")

    leftover = sorted({c for c in body if ord(c) > 0x2010 and c not in "‘’“”–—…"})
    if leftover:
        print(f"  ⚠ unmapped non-ASCII still present: {leftover}")

    # One bibliography, copied rather than referenced: BibTeX does not resolve
    # \bibliography{../references} reliably and fails by emitting an empty
    # reference list, with no error. The copy is gitignored so ../references.bib
    # stays the only tracked source.
    shutil.copyfile(PAPER.parent / "references.bib", HERE / "references.bib")

    # Two files, split at the appendix boundary, because the submitted PDF runs
    # body -> references -> appendix -> checklist. That is the order the official
    # neurips_2026.tex demonstrates (\section*{References} then \appendix) and the order
    # the venue's checklist guidelines imply when they say the checklist follows "the
    # submission's references and the (optional) supplemental material". main.tex puts the
    # bibliography between the two \input{}s, so the split has to happen here rather than
    # there. Everything above has already run on the combined text, which is what
    # _anchor_appendix_exhibits needs.
    marker = "\\clearpage\n\\appendix\n"
    if body.count(marker) != 1:
        raise AssertionError(
            f"expected exactly one appendix boundary {marker!r}, found "
            f"{body.count(marker)}; the emission above is what writes it"
        )
    main_body, appendix = body.split(marker)
    appendix = marker + appendix

    (HERE / "body.tex").write_text(main_body, encoding="utf-8")
    (HERE / "appendix.tex").write_text(appendix, encoding="utf-8")
    print(
        f"body.tex written ({len(main_body.splitlines())} lines), "
        f"appendix.tex written ({len(appendix.splitlines())} lines)"
    )


if __name__ == "__main__":
    main()
