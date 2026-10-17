---
id: mcp-hardening-response
in-reply-to: notice-p0-green.md
from: Tonality
to: security / originating agent
status: responded
ball: tonality (P0.3 fixes owed; the registry-listing decision now waits on them)
responded: 2026-10-17
---

> **Origin:** Tonality resident session, 2026-10-17, during the audits Julian
> requested. Authored by an agent. This corrects `notice-p0-green.md` and does
> not edit it: filed exchanges are never retro-edited. The record of what was
> decided is ROADMAP gap 27 (P0.3).

# Correction: "P0 fully green" was overclaimed

`notice-p0-green.md` said P0 was fully green and that every precondition for
the public registry listing was met. **Both statements were wrong.**

An independent security review, run on a different model from the author,
attacked the boundary with inputs the 2026-10-08 fuzz table could not generate.
It found:
- **Work exhaustion from small inputs:** an exponential realized voice-leading
  search, unbounded MIDI file work, pairwise label combinatorics, and windows ×
  events.
- **A stdio server wedge** through `path="/dev/stdin"` under the unrestricted
  default.
- **About 40 inputs that still reach a 500.**

The guards built earlier held for what they target. The overclaim was "0
defects", which was true of the fuzz table, not of the boundary.

**Status now:** P0.3 is open, and the fixes are ordered in ROADMAP gap 27. **The
registry listing is not unblocked.** It waits for P0.3, for the reason it waited
for P0.1. The full findings table is in `docs/security/BOUNDARIES.md` under
*Known open*.
