# Tonality

**A deterministic music-theory engine for AI systems and the software that makes
music — one that *derives* its answers from first principles, returns every reading
the theory admits (ranked, with evidence), and refuses to guess when it doesn't
know.**

Tonality is a local-first reasoning core for twelve-tone equal temperament. It
exists to be **queried** — by generative sequencers, synthesizers, visualizers,
preference-learners, and LLM agents — and it rests on a single wager about how to
make machine reasoning over a hard domain *trustworthy*:

> Let deterministic code do the exact combinatorics, let the model do the fuzzy and
> creative part, and never let either pretend to be the other.

That wager is why the project exists. Large language models are unreliable at
precisely the things music theory is built from — interval-vector arithmetic,
exhaustive subset search, symmetry, voice-leading distance. Tonality does exactly
those, exactly, and hands back a result an agent can **cite** instead of
**hallucinate**. Everything else — taste, intent, interpretation-in-context — stays
with the caller. It is a foundation library, not an end-user app: pure Python, no
network, no external services; the catalogs are data you can read and edit, the
analysis is code you can audit.

---

## The epistemics

The design is an argument about trustworthy reasoning, expressed as four rules the
whole engine obeys. They are worth reading as a stance, not just an API.

**1 · Derive, never store.** Harmonic knowledge is *computed* from primitives and
explicit rules, never stored as answers the engine can't show its work for.
Functional roles, chord–scale compatibility, and modal borrowing fall out of
interval structure and scale definitions — the legacy static lookup tables were
deleted — so behind every result there is a derivation, and a self-check pass
cross-verifies the derived mappings against the raw scale masks. *Why it matters: a
system that can show its work can be audited; one that recites a table cannot.*

**2 · Error, don't guess.** An analysis that needs information it wasn't given
**raises** — it does not invent the missing piece. You cannot ask for a voicing's
inversion without giving real pitches; you cannot get a key without evidence for
one. The engine never fabricates register, or a tonal center, or a reading it has no
grounds for. *Why it matters: a confident answer to an unanswerable question is the
most dangerous output a reasoning system can produce; refusing is the honest move.*

**3 · Plural, ranked, evidenced.** Where the theory genuinely admits more than one
reading, the engine returns *all* of them — ordered by fit, each carrying the
evidence (interval-class fingerprint, pitch-class membership, functional role,
margin) that justifies its rank. A near-tie between relative keys is surfaced as a
near-tie, never silently collapsed. *Why it matters: calibration is architecture,
not a disclaimer — a surfaced uncertainty is strictly better than a hidden one.*
(Deterministic facts — a set-class fingerprint, a voice-leading distance — are
reported as the single values they are; it is *interpretation* that comes plural.)

**4 · Deterministic core, honest priors.** The parts that must be trusted are pure
and reproducible: no wall-clock reads, no unseeded randomness, same input → same
output, forever — a property enforced by a CI test, because it is load-bearing.
Where the engine leans on empirical judgment (key profiles, scoring weights,
smoothing constants), that judgment ships as a **versioned prior**, cited by version
in every result it touched, and theory sets are never fit to a copyrighted corpus.
Generative acts are labeled generative; analytical ones never quietly generate. *Why
it matters: reproducibility and provenance are what let a downstream tool — or a
reviewer — replay a result and trust it.*

The corollary of all four is a **division of labor**: precise combinatorics live in
the engine; interpretation, taste, and creation live in the caller. It is a small,
concrete model of how a language model and a deterministic tool can collaborate
without either one hallucinating on the other's behalf.

---

## Why it's useful

- **For AI agents** — a deterministic oracle for the exact music reasoning LLMs get
  wrong. An agent can analyze a progression, name a chord in context, or check a
  voice-leading rule and get an answer it can *quote with evidence*, not one it made
  up. The whole surface is exposed as tools an agent calls (below).
- **For music software** — one audited theory core, so every synth, sequencer, and
  visualizer stops reinventing (and quietly disagreeing about) the theory. Around a
  around ten consumer projects already share it through a versioned contract.
- **For research & education** — the engine can **derive a style** from a corpus (or
  a person's playing) as an inspectable ruleset + a sampleable distribution, and
  **measure the distance** between one style and another as a number. That makes it
  a substrate for tools that analyze, teach, and give feedback on musical style —
  "how far is this from the target, on which dimensions" as an engine result, not a
  vibe.

---

## What it can do

Everything below is shipped and tested, reachable from Python, the MCP endpoint, or
as JSON. (Full capability schematic: **[INTEGRATION.md](INTEGRATION.md)**.)

**Functional harmony, derived.** Roles, chord–scale compatibility, and borrowing
computed from interval structure — multiple chord options per scale degree, each
with its stack; a non-diatonic chord names its candidate borrow-source and the exact
pitch classes it adds or removes.

**Set-class & harmonic color.** Normal order, Rahn prime form, Z-relations, interval
vectors, and a 6-D DFT "harmonic color" embedding (|f₅| ≈ diatonicity, |f₆| ≈
whole-tone-ness) — plus DFT phase and a signed **chirality** family that separates
major from minor where the interval vector alone cannot (a small research result
derived with a consumer project).

**Naming & contextual disambiguation.** Every valid `(root, quality)` reading of a
pitch-class set (C6 = Am7; dim7 names at four roots), then *the* chosen reading
inside a key with ranked alternatives and per-signal evidence — flagging augmented
sixths, secondary dominants, and Neapolitans rather than penalizing them. A
companion `scale_names` does the same for scales.

**Key induction & tracking.** Ranked key candidates with a top-two margin; windowed
local key tracking into modulation-aware regions; a tonicization-vs-modulation
structural reduction; opt-in continuity priors. Every empirical knob is versioned
and cited.

**Meter, rhythm & time.** Infer the time signature from note content (never
overriding the file), track it through meter changes, recover the downbeat phase of
an anacrusis; MIDI ingestion, harmonic segmentation, harmonic rhythm, voice-motion,
melodic and rhythmic atoms, swing/groove feel.

**Voice-leading & succession.** Exact minimal voice-leading distance between pc-sets
and over real voicings; next-chord recommendations tagged with functional,
voice-leading, and color evidence; cadence detection (authentic / plagal / half /
deceptive).

**Rulesets & style profiles** *(the newest layer).* A declarative rule language over
the analytical vocabulary; **rule induction** that mines a corpus for the
statistically significant rules it follows (Fisher's exact + false-discovery control
— significance, not vibes); **transition distributions** (a sampleable, Laplace-
smoothed, provenance-stamped model of harmonic motion); a **style-profile bundle**
that carries a ruleset + distributions + provenance as one versioned artifact; and
**held-out cross-entropy** to score how well a style predicts fresh music — the
metric that turns "this sounds like X" into a number.

**Representation as data.** Render-agnostic numeric descriptions a visualizer can
draw however it likes: keyboard, piano-roll, clock/bracelet, Tonnetz, chord-network
(a voice-leading graph), colour-content wheels, a tonal-orientation angle. The
library emits descriptions; pixels are the edge consumer's job.

---

## The MCP endpoint & the integration ecosystem

Tonality is built to be *consumed*. Three transports expose the **same 79 tools**
through **one data contract** — identical signatures, so a caller can move between
them without changing how it thinks:

| Transport | For | Entry point |
|---|---|---|
| **Python import** | scripting, embedding, lowest latency | `from mts.analysis import …` — pure functions over frozen dataclasses |
| **MCP server** | LLM agents (Claude & others) | `python -m mts.mcp` — 79 tools, one per analysis entry point |
| **HTTP bridge** | any language, out-of-process | `python -m mts.mcp.bridge` → loopback `:8012` (`GET /tools`, `POST /call/<tool>`) |

The MCP layer is deliberately thin — one tool per analysis entry point, pure and
SDK-free below the adapter line — so the intelligence stays in the engine and stays
fully testable. Every tool returns a typed structure with a `to_dict()`: a caller
gets JSON it can trust, with the evidence attached.

**The contract is enforced, not hoped for.** A **golden conformance harness** pins
every tool's full output (at least one deterministic call per tool, float-tolerant,
language-neutral by construction); any output change fails CI until the golden is
regenerated in the same change, so drift is always reviewable. A separate **port
pin** fingerprints the surface a C++ re-implementation must reproduce, and a
**freezability** test keeps the core reproducible. Empirical priors and catalogs are
versioned JSON that ship to every implementation verbatim. (Over 1,200 tests gate
the whole thing.)

**The ecosystem is real and coordinated.** Around ten consumer projects — synths,
generative sequencers, visualizers, a preference-learner, a C++ performance port —
build on the engine, and they coordinate through a lightweight **integrations
protocol** in [`integrations/`](integrations/): a consumer files a *brief* (what it
needs), the engine triages it against the actual code and replies with a *response*
(shipped / documented / a recorded gap / a boundary ruling), and durable decisions
land in the roadmap. It keeps a shared core honest across many callers without any
of them reaching into each other's internals — a small, working model of
multi-project coordination around a trusted engine.

---

## Quickstart

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .            # MIDI parsing (mido) included; add ".[mcp]" for the MCP server
python examples/quickstart_engine_demo.py
```

Analyze a chord from the terminal:

```bash
python scripts/analyze_chord.py C maj7 --tonic C --json
```

`scripts/` bundles terminal tools over the analysis layer (`analyze_scale.py`,
`analyze_chord.py`, `check_chord_scale_compat.py`, `build_scale_or_chord.py`,
`export_versioned_data.py`); each self-documents via `-h`. The terminal tools are a
window onto the engine, not the point of it.

---

## The core data model

Two structures, and one rule that ties the epistemics to the type system:

- an **identity key** — a pitch-class set as a 12-bit bitmask; what you *match, name,
  and catalog* on;
- an optional **realization** — the actual pitches; what *voicing, inversion, and
  register* analysis read.

You can always **reduce** a realization to a key; you can never **invent** register
from a key without choosing a voicing — and choosing is a *generative* act, not an
analytical one. Analysis that needs register and isn't given it errors (rule 2). The
type system makes the honest thing the easy thing.

---

## Data & customization

Reference material is versioned JSON under `mts/data/` — scales (modal/ethnic sets
with aliases), chord qualities (triads through altered 13ths), functional-harmony
tables, and key/meter/scoring/smoothing priors. Empirical values are versioned and
cited; theory sets are never corpus-fit. Edit the JSON, reload via `mts.io.loaders`,
and the engine picks up the change. `mts/theory/functions.py` derives functional
mappings procedurally from template rules.

*(A legacy terminal Ableton-Push grid lives at `mts/cli/push.py` — the project's
first visualization surface, kept as an example consumer. Live Push visualization is
now owned by consumer projects; Tonality supplies the analysis, the consumer owns
the surface.)*

---

## Where to go next

- **[ROADMAP.md](ROADMAP.md)** — the single source of truth for direction: build
  sequence, architecture decisions, target applications, what's deferred, and a
  *Horizon* section for speculative cross-project ideas. Any forward-looking claim
  (including this README) defers to it.
- **[INTEGRATION.md](INTEGRATION.md)** — the capability schematic for consumers:
  every shipped capability, the four doors in, the contracts to design around.
- **[CLAUDE.md](CLAUDE.md)** — contributor & agent workflow, the architecture
  layers, and the conventions.
- **[`integrations/`](integrations/)** — the cross-project exchange channel: the
  briefs and responses that keep the engine and its consumers speaking one language.
- **[SECURITY.md](SECURITY.md)** — how to report a vulnerability and how to harden
  a deployment (the MIDI path allowlist, hash-pinned installs, the bridge).

---

**Last verified 2026-08-27** against `d3110b6` — 79 MCP tools, 1217 tests green on
Python 3.10 + 3.13 (`./verify fast`; `./verify full` adds the audit invariants and
reproduces both CI legs). The tool count above is gate-enforced, not maintained by
hand: `tests/test_tool_manifest_pin.py` fails if this file and the live surface
disagree. A dated line beats silent rot — if this date is old, treat the prose as
unverified rather than assuming it still holds.

---

## License

Tonality is released under the **[PolyForm Noncommercial License 1.0.0](LICENSE.md)** —
© 2026 Julian Smith ([Lifted-Truck](https://github.com/Lifted-Truck)). It is
*source-available*: you may use, modify, and distribute it freely for any
**noncommercial** purpose — research, teaching, personal and hobby projects, and
use by nonprofit, educational, government, or public-research organizations.
**Commercial use requires a separate license from the author.** See
[LICENSE.md](LICENSE.md) for the terms; consumer projects that build on Tonality
inherit this noncommercial boundary.
