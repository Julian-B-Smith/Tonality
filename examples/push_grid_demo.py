"""Push Grid demo showcasing layout variants, legends, and chord overlays."""

from __future__ import annotations

import sys
from pathlib import Path

# TODO: remove when package is installed in editable mode.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from mts.io.loaders import load_scales, load_chord_qualities
from mts.core.chord import Chord
from mts.core.enharmonics import pc_from_name
from mts.cli.push_grid import PushGrid


def _paint(text: str, *, fg: str | None = None, bold: bool = False, dim: bool = False) -> str:
    ansi = {
        "reset": "\x1b[0m",
        "bold": "\x1b[1m",
        "dim": "\x1b[2m",
        "fg_bright_magenta": "\x1b[95m",
        "fg_bright_cyan": "\x1b[96m",
        "fg_cyan": "\x1b[36m",
        "fg_bright_yellow": "\x1b[93m",
        "fg_bright_red": "\x1b[91m",
        "fg_yellow": "\x1b[33m",
        "fg_red": "\x1b[31m",
        "fg_white": "\x1b[37m",
        "fg_bright_black": "\x1b[90m",
    }
    parts: list[str] = []
    if bold:
        parts.append(ansi["bold"])
    if dim:
        parts.append(ansi["dim"])
    if fg:
        parts.append(ansi.get(fg, ""))
    if not parts:
        return text
    return "".join(parts) + text + ansi["reset"]


def format_legend(grid: PushGrid) -> str:
    use_color = grid.color_mode == "always" or (grid.color_mode == "auto" and sys.stdout.isatty())
    if use_color:
        return (
            "Legend: "
            + _paint("tonic + chord root", fg="fg_bright_magenta", bold=True) + ", "
            + _paint("tonic in chord", fg="fg_bright_cyan", bold=True) + ", "
            + _paint("tonic", fg="fg_cyan", bold=True) + ", "
            + _paint("chord root (in key)", fg="fg_bright_yellow", bold=True) + ", "
            + _paint("chord root (out of key)", fg="fg_bright_red", bold=True) + ", "
            + _paint("chord tone (in key)", fg="fg_yellow", bold=True) + ", "
            + _paint("chord tone (out of key)", fg="fg_red", bold=True) + ", "
            + _paint("in key", fg="fg_white") + ", "
            + _paint("out of key", fg="fg_bright_black", dim=True)
        )
    return (
        "Legend: tonic + chord root, tonic in chord, tonic, "
        "chord root (in key), chord root (out of key), chord tone (in key), "
        "chord tone (out of key), in key, out of key"
    )


def print_section(title: str) -> None:
    print("\n" + title)
    print("=" * len(title))


def show_grid(
    title: str,
    grid: PushGrid,
    *,
    chord_label: str | None = None,
    chord_intervals: str | None = None,
    cli_command: str | None = None,
    show_blocks: bool = False,
) -> None:
    print_section(title)
    if chord_label:
        descriptor = chord_label
        if chord_intervals:
            descriptor = f"{descriptor} (intervals: {chord_intervals})"
        print(f"Chord: {descriptor}")
    print(format_legend(grid))
    for line in grid.render_lines():
        print(line)
    if show_blocks:
        print("\nSymbol grid:")
        for line in grid.render_block_lines():
            print(line)
    if cli_command:
        print("\nCommand:")
        print(cli_command)


def describe_intervals(chord: Chord) -> str:
    return ", ".join(str(iv) for iv in chord.quality.intervals)


def main() -> None:
    scales = load_scales()
    qualities = load_chord_qualities()

    ionian = scales["Ionian"]
    dorian = scales["Dorian"]

    cmaj7 = Chord.from_quality(pc_from_name("C"), qualities["maj7"])
    g7_dominant = Chord.from_quality(pc_from_name("G"), qualities["7"])
    fmaj7 = Chord.from_quality(pc_from_name("F"), qualities["maj7"])
    dmin7_g = Chord.from_quality(pc_from_name("D"), qualities["min7"])

    base_grid = PushGrid(
        preset="fourths",
        anchor="fixed_C",
        origin="lower",
        tonic_pc=pc_from_name("C"),
        scale_degrees_rel=list(ionian.degrees),
        chord_pcs_abs=list(cmaj7.pcs),
        layout_mode="chromatic",
        degree_style="names",
        spelling="auto",
        key_signature=0,
    )
    base_grid.color_mode = "always"
    base_grid.tonic_mode = "distinct"
    base_grid.chord_root_pc = pc_from_name("C")

    show_grid(
        "C Ionian • Chromatic • Fixed C • Fourths • Names",
        base_grid,
        chord_label="Cmaj7",
        chord_intervals=describe_intervals(cmaj7),
        cli_command="python -m mts.cli.push --key C --scale Ionian --chord C:maj7 --preset fourths --mode chromatic --color always",
        show_blocks=True,
    )

    dominant_grid = PushGrid(
        preset="fourths",
        anchor="fixed_C",
        origin="lower",
        tonic_pc=pc_from_name("C"),
        scale_degrees_rel=list(ionian.degrees),
        chord_pcs_abs=list(g7_dominant.pcs),
        layout_mode="chromatic",
        degree_style="names",
        spelling="auto",
        key_signature=0,
    )
    dominant_grid.color_mode = "auto"
    dominant_grid.tonic_mode = "distinct"
    dominant_grid.chord_root_pc = pc_from_name("G")

    show_grid(
        "C Ionian • Chromatic • Dominant overlay (root at V)",
        dominant_grid,
        chord_label="G7 (root at V)",
        chord_intervals=describe_intervals(g7_dominant),
        cli_command="python -m mts.cli.push --key C --scale Ionian --chord G:7 --preset fourths --mode chromatic",
    )

    subdominant_grid = PushGrid(
        preset="fourths",
        anchor="fixed_root",
        root_pc=pc_from_name("C"),
        origin="lower",
        tonic_pc=pc_from_name("C"),
        scale_degrees_rel=list(ionian.degrees),
        chord_pcs_abs=list(fmaj7.pcs),
        layout_mode="in_scale",
        hide_out_of_key=True,
        degree_style="degrees",
        spelling="flats",
        key_signature=-1,
    )
    subdominant_grid.color_mode = "auto"
    subdominant_grid.chord_root_pc = pc_from_name("F")

    show_grid(
        "Ionian • In-Scale • Fixed Root • Degrees (flats) • Hidden out-of-key",
        subdominant_grid,
        chord_label="Fmaj7 at IV (contains tonic)",
        chord_intervals=describe_intervals(fmaj7),
        cli_command="python -m mts.cli.push --key C --scale Ionian --chord F:maj7 --degrees --hide-ook --spelling flats",
    )

    g_tonic_grid = PushGrid(
        preset="thirds",
        anchor="fixed_C",
        origin="upper",
        tonic_pc=pc_from_name("G"),
        scale_degrees_rel=list(dorian.degrees),
        chord_pcs_abs=list(dmin7_g.pcs),
        layout_mode="chromatic",
        degree_style="names",
        spelling="auto",
        key_signature=1,
    )
    g_tonic_grid.color_mode = "always"
    g_tonic_grid.tonic_mode = "blend"
    g_tonic_grid.chord_root_pc = pc_from_name("D")

    show_grid(
        "G Dorian • Chromatic • Fixed C • Thirds • Names • tonic_mode=blend",
        g_tonic_grid,
        chord_label="Dmin7 at II",
        chord_intervals=describe_intervals(dmin7_g),
        cli_command="python -m mts.cli.push --key G --scale Dorian --chord D:min7 --preset thirds --origin upper --color always",
        show_blocks=True,
    )

    base_grid.set_chord(None)
    base_grid.chord_root_pc = None
    print_section("Chord cleared (no highlights)")
    print(format_legend(base_grid))
    for line in base_grid.render_lines():
        print(line)

    print_section("Additional CLI examples")
    print("python -m mts.cli.push --key C --scale Ionian --list-functions --functions-mode both --functions-feature altered_dominant")


if __name__ == "__main__":
    main()
