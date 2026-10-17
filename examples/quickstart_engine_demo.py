"""Quickstart: the engine's Python door in five calls.

Run from the repo root after `pip install -e .`:

    python examples/quickstart_engine_demo.py

Each call returns a typed result with a `to_dict()` JSON form; everything is
pitch-class arithmetic (C = 0). Spelling note names is a display concern, so the
output below prints numbers. tests/test_examples.py runs this file, so the
README's first command cannot silently break again (it did: the old demo
imported a helper removed as dead code in RE-6e).
"""

from __future__ import annotations

from mts.analysis import infer_key, interpret_chord, name_chord, voice_leading
from mts.analysis.pcset_math import set_class_data
from mts.core.bitmask import mask_from_pcs

C_MAJ7 = [0, 4, 7, 11]
A_MIN7 = [9, 0, 4, 7]   # the same pitch classes as C6: one set, several names


def main() -> None:
    sc = set_class_data(mask_from_pcs(C_MAJ7)).to_dict()
    print(f"set class of Cmaj7: prime form {sc['prime_form']}, |f5| (diatonicity) {sc['dft_magnitudes'][4]:.3f}")

    readings = interpret_chord(A_MIN7).to_dict()["interpretations"]
    print("every reading of {9,0,4,7}: " + ", ".join(f"{r['quality']} on pc {r['root_pc']}" for r in readings))

    chosen = name_chord([2, 5, 9, 0], context=None).to_dict()["chosen"]
    print(f"chosen naming of {{2,5,9,0}} with no key given: {chosen['interpretation']['quality']} "
          f"on pc {chosen['interpretation']['root_pc']}, evidence {[e['signal'] for e in chosen['evidence']]}")

    # Duration-weighted pitch-class content of a C-major passage (index = pc).
    weights = [4, 0, 2, 0, 3, 1, 0, 4, 0, 2, 0, 1]
    key = infer_key(weights).to_dict()
    top = key["candidates"][0]
    print(f"key: tonic pc {top['tonic_pc']} {top['mode']}, margin {key['margin']:.3f} ({key['profile_version']})")

    vl = voice_leading([0, 4, 7], [5, 9, 0]).to_dict()
    print(f"voice leading C → F: distance {vl['distance']}, mapping {vl['mapping']}")


if __name__ == "__main__":
    main()
