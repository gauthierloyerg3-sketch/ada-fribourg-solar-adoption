"""Checks on the paper skeleton in paper/. The text is the author's own; these guard the wiring.

Drafted with an AI assistant, see docs/ai_log.md.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"
FIGURES = ROOT / "figures"

# Set to False when the author starts writing text in main.tex: the guard below would fail
# on his own paragraphs.
ENFORCE_NO_PROSE = True

# Outputs listed in figures/README.md that are deliberately not in the paper (give a reason per
# entry). Empty today: every .tex table and .pdf figure is used. CSV files are not floats.
NOT_IN_PAPER: set[str] = set()

REQUIRED_HEADINGS = [
    r"\begin{abstract}",
    r"\section{Introduction}",
    r"\section{Research question and literature}",
    r"\section{Methodology}",
    r"\section{Data set (source and cleaning)}",
    r"\section{Implementation}",
    r"\section{Results}",
    r"\section{Conclusion}",
    r"\appendix",
    r"\section{Declaration of tools}",
]


def strip_comments(text):
    return "\n".join(re.sub(r"(?<!\\)%.*", "", line) for line in text.splitlines())


def main_code():
    return strip_comments((PAPER / "main.tex").read_text())


def referenced_paths():
    out = []
    for tex in sorted(PAPER.glob("*.tex")):
        code = strip_comments(tex.read_text())
        for m in re.finditer(
            r"\\(?:input|include|includegraphics)(?:\[[^\]]*\])?\{([^}]+)\}", code
        ):
            out.append((tex.name, m.group(1)))
    return out


def test_every_referenced_path_exists():
    refs = referenced_paths()
    assert refs, "main.tex references no figure or table"
    for tex, ref in refs:
        assert (PAPER / ref).is_file(), f"{tex}: {ref} does not exist"


def listed_outputs():
    text = (FIGURES / "README.md").read_text()
    names = re.findall(r"^\| `([^`]+)`", text, flags=re.M)
    return [n for n in names if n.endswith((".tex", ".pdf"))]


def test_every_listed_output_is_in_the_paper_or_excused():
    used = {Path(ref).name for _, ref in referenced_paths()}
    listed = listed_outputs()
    assert listed
    missing = [n for n in listed if n not in used and n not in NOT_IN_PAPER]
    assert not missing, f"not in paper/main.tex and not in NOT_IN_PAPER: {missing}"
    assert NOT_IN_PAPER <= set(listed), "NOT_IN_PAPER names a file that is not in figures/README.md"


def test_section_headings_in_course_order():
    code = main_code()
    positions = []
    for heading in REQUIRED_HEADINGS:
        assert code.count(heading) == 1, f"{heading} must appear exactly once"
        positions.append(code.index(heading))
    assert positions == sorted(positions)


def test_no_prose_in_main_tex():
    """Guard against AI-written paper text: outside float environments, main.tex may hold only
    LaTeX commands (lines starting with a backslash), comments and blank lines; no line is over
    200 characters.
    Captions are lines inside floats and stay short placeholders."""
    if not ENFORCE_NO_PROSE:
        return
    body = main_code().split(r"\begin{document}", 1)[1]
    depth = 0
    for line in body.splitlines():
        assert len(line) <= 200, f"long line (prose?): {line[:60]}..."
        stripped = line.strip()
        if re.match(r"\\begin\{(table|figure)", stripped):
            depth += 1
        elif re.match(r"\\end\{(table|figure)", stripped):
            depth -= 1
        elif depth == 0 and stripped and not stripped.startswith("\\"):
            raise AssertionError(f"text outside a float (prose?): {stripped[:60]}")
