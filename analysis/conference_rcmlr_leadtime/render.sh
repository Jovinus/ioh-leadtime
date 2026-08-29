#!/usr/bin/env bash
# Render PAPER.md -> PAPER.docx for review.
#
# PAPER.md is the single source of truth. Nobody edits the DOCX; comments come
# back against it and are applied to the markdown, then this is re-run.
#
# NOTE ON THE READER. A --from=gfm build will NOT work here. pandoc 2.12's gfm reader
# has no citation support at all -- neither `gfm+citations` nor
# `gfm+yaml_metadata_block` is accepted -- so every [@key] passes through as
# literal text and the reference list comes out empty. A manuscript whose references
# are typed inline as numbered markdown never hits this.
# Since this paper uses [@key] so that the LaTeX port can hand them to natbib
# untouched, it needs pandoc's own `markdown` reader.
#
# pandoc lives in the base environment, not on the torch PATH.
set -euo pipefail

cd "$(dirname "$0")"
export PATH="$PATH:/opt/anaconda3/bin"

pandoc PAPER.md \
  --from=markdown \
  --to=docx \
  --citeproc \
  --bibliography=references.bib \
  --resource-path=".:figures" \
  --output PAPER.docx

# `|| true` because grep exits 1 when it finds nothing, which is the success
# case here and would otherwise trip `set -e` via pipefail.
unresolved=$( { pandoc PAPER.docx -t plain | grep -coE '\[@[a-z0-9]+'; } || true )
if [ "$unresolved" != "0" ]; then
  echo "ERROR: $unresolved unresolved citation key(s) in PAPER.docx" >&2
  exit 1
fi

# Review copy in markdown with citations resolved, for reading without Word.
pandoc PAPER.md --from=markdown --to=gfm --citeproc --bibliography=references.bib \
  --wrap=none --output PAPER_REVIEW.md
python3 - <<'HDR'
import pathlib
p = pathlib.Path("PAPER_REVIEW.md")
p.write_text(
    "<!-- GENERATED - do not edit. Source of truth is PAPER.md; regenerate with ./render.sh -->\n\n"
    "> **Review copy.** Citations resolved to author-year for reading; the submission uses\n"
    "> numbered citations from the venue's style. Figures are linked relative to `figures/`.\n"
    "> Anonymised: no author, institution, or first-person self-reference.\n\n"
    + p.read_text()
)
HDR

echo "PAPER_REVIEW.md written"
echo "PAPER.docx written ($(wc -c < PAPER.docx | tr -d ' ') bytes), all citations resolved"
