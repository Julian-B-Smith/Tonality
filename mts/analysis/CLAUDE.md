# mts/analysis — Enrichment engine

Turns identities into contextualized analysis. Pure functions over `core` objects;
no session state here (that lives in `workspace`/`SessionCatalog`).

- `mts/notation.py` (moved below this layer, RE-6b — was `analysis/specs.py`) — the
  multi-notation parser (intervals, degrees, note names, MIDI, catalog names).
  This *is* the "various timeless notations" feature. It sits **below `io/`** so
  `io/loaders` can consume it without an import cycle; it is re-exported from
  `mts.analysis` for compatibility. Its `scope` literal (abstract/note/absolute)
  is an additive compat alias over the `core/spec_level.py` lattice:
  `from_scope`/`to_scope` bridge the two, and `ChordSpec.spec_level` /
  `ChordParseResult.to_realization()` expose the lattice view. `scope` is a
  *diagonal* — it cannot express the registered+rootless cell.
- `errors.py` — `SpecificationError` + `require_realization`, the guard for the
  cardinal rule. Register-dependent analysis calls the guard and **errors** when
  handed a register-less identity instead of inventing a voicing.
- `voicings.py` — `suggest_voicings`: **generative**, not analysis. It invents
  register from an identity; kept out of the analysis path deliberately. An
  extensible registry (`_VOICING_BUILDERS`) produces a named vocabulary
  (closed, drop-2/3, rootless, shell, …); `voicing_shapes` exposes those spacings
  as the single source of truth shared with recognition.
- `equivalence.py` — `interpret_chord`: identity-level analysis enumerating every
  valid `(root, quality)` naming of a PC set (symmetric chords name at several
  roots; ambiguous sets name as several qualities, e.g. C6 = Am7).
- `containment.py` — `find_containers`: the gap-8 catalog containment query —
  every catalog scale/quality containing a pc set, at which roots (the reverse
  of compatibility: the container transposes, the query stays absolute).
  Tightest-first ordering, exact matches flagged; symmetric containers report
  every valid root. Takes explicit catalog mappings for session-catalog views.
- `analytical_context.py` — `AnalyticalContext` (tonal center + optional key) and
  `contextualize_chord` → `ChordInKey` (scale-degree placement, diatonic vs
  chromatic). The **analytical** frame; the counterpart to the display-edge
  `DisplayContext` in `mts/context/`. Numeric only; foundation for context-sensitive
  naming + dataset records.
- `key_induction.py` — `infer_key`: the upstream **producer** for the
  `AnalyticalContext` seam (Phase 3.5b). Global-key v1: profile correlation over
  duration-weighted PC content; returns *all* ranked `KeyCandidate`s + the
  top-two margin (Decision 7 — relative-key near-ties are surfaced, never
  collapsed). Profiles are versioned priors from `data/key_profiles.json`;
  results cite the version. Accepts a 12-vector or anything with
  `pc_weights()` (duck-typed so `temporal.Sequence` works without an upward
  import). `candidate_context` realizes a candidate as an `AnalyticalContext`.
- `naming.py` — `name_chord`: the disambiguator (Phase 3 final slice). Ranks
  every `interpret_chord` candidate inside an `AnalyticalContext` with scored,
  inspectable evidence; weights are a versioned prior
  (`data/naming_weights.json`). `context=None` → intrinsic-only ranking
  (never fabricates a key — the key-side don't-guess rule). Special-function
  seam flags aug-6/secondary-dominant/Neapolitan instead of penalizing their
  chromaticism. `name_chord_across_keys` maps it over ranked `infer_key`
  candidates: per-key conditional namings + key-weighted combined view.
- `cadence.py` — `detect_cadences`: cadential **formulas** (authentic, plagal,
  deceptive, half) in a named progression, each an evidenced event. Formula, not a
  confirmed cadence: without timing, `is_final` is the strongest signal.
- `succession.py` — `recommend_next_chord`: ranked, tagged next-chord candidates
  (gap 14) under the versioned `succession.1` scoring prior, with the raw axes
  exposed so callers can re-rank; `tag_transition` annotates one transition.
- `meter_estimation.py` — `infer_meter`: ranked time signatures from note
  content (gap 11). It evidences against the file's declared meter and never
  overrides it.
- `tendency.py` — `melodic_tendency`: ranked note-to-note resolutions + the
  12-pc stability landing table (gap 19, A9 Wend — the melodic sibling of
  `next_chord`). Anchoring attraction `(s_q/s_p)/d²` (Lerdahl) over a
  **versioned prior** (`data/melodic_tendency.json`, stabilities frozen from
  kk-1982.1 — never read live). Target policy is a caller parameter
  (`diatonic_steps` default, `chromatic_steps` opt-in); chord context boosts
  chord-tone stability (both roles, cited factor). Major/minor only; the
  caller owns the snap policy (margin-as-signal seam).
- `voice_leading.py` — `voice_leading`: minimal voice-leading distance between
  two pc-set identities (total circular motion under the optimal non-crossing
  assignment; exact, brute-force-verified in tests). **Analytical** — measures,
  never realizes register (Phase 7 consumes it). The unequal-cardinality
  convention is a named, cited policy (`doubling.1`); results carry the optimal
  mapping as evidence. `voice_leading_realized` is the register-required
  sibling over voiced chords (actual semitones, octaves cost 12, doublings are
  voices; raises on `None` per the cardinal rule) — linear pitch space, so
  optimal pairing is sorted index-wise / contiguous blocks, also exact.
- `results.py` — **typed result dataclasses**. All analysis returns these, never
  raw dicts. Top-level results expose `to_dict()` (JSON/MCP output). Add new
  result fields here, not as ad-hoc dict keys. **Numeric/PC only** — no spelled
  `note_names`, no styled interval labels, no enharmonic spellings (those are a
  display concern; render at the edge via `mts/context/result_format.py` from a
  `DisplayContext`). Litmus test: if a value changes when you flip sharps↔flats
  or numeric↔classical, it's display and does **not** belong here.
- `scale_analysis.py`, `chord_analysis.py` — request in, typed result out. Private
  helpers return typed sub-objects, not dicts. Requests carry **no display params**
  (spelling/key-signature/label-style live on the `DisplayContext`). `analyze_chord`
  is **pure-identity** (numeric only; `Inversion`s carry figured-bass — structural,
  not spelling); `analyze_voicing` is the register-required sibling that reads a
  `Realization`, errors without one, and *recognizes* the actual bass inversion +
  voicing type (matched against `voicing_shapes`).
- `mts/context/result_format.py` (display edge, not this layer) — renders numeric
  results into spelled/labeled views from a `DisplayContext`
  (`format_chord_analysis`, `format_scale_analysis`, `name_interpretations`,
  `spell_voicing`). Display imports analysis; analysis never imports display.
- `pcset_math.py` — shared PC-set math (interval vector, reflection axes,
  compatibility roots) used by the chord/scale/comparison modules. Helpers are
  cached over the 4096-mask space; add new mask-keyed math here instead of
  duplicating it per module.
- `comparisons.py`, `summaries.py` — cross-object compatibility and compact briefs.
- `mts/session.py` (moved below this layer, RE-6b — was `analysis/builders.py`) —
  `SessionCatalog` + manual scale/chord registration. **No module-level mutable
  state** — sessions are instances, and the module-level default session was
  *retired* (RE-6b): `register_scale`/`register_chord` require an explicit
  `session=`. It sits below `io/` (which merges a session's catalogs on request);
  re-exported from `mts.analysis` for compatibility.
  Temporal code lives in the `mts/temporal/` package (Phase 2) — build it there,
  not here. (The old `timeline.py` stub + `workspace.analyze_timeline` path were
  removed 2026-06-29.)

**When adding analysis:** declare the specification level it needs (PC-set vs.
realization). Register-dependent analysis must **error** on a register-less
identity, not guess a voicing. See root CLAUDE.md.

Planned work for this layer is tracked in [ROADMAP.md](../../ROADMAP.md) (the
single source of truth for direction) — link phases from here; don't record
plans here.
