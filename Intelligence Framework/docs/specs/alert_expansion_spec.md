# SPEC: alert expansion — watched-condition flips to phone (team approved 2026-07-31)

> Review record. Saved verbatim from the team's approval before building,
> per AGENTS.md: protected-path specs become repo artifacts first.

Route watched-condition flips to phone notifications. All
three classes: (a) regime change / filter flip (session_memory
already detects — "CONDITIONS IMPROVED/DETERIORATED"),
(b) EXIT-IF condition newly satisfied vs prior run,
(c) shadow fires (already wired — verify only).
Implementation confined to the scheduled wrapper layer +
a small check in decision_brief's session-delta path exposing
a machine-readable flip flag. No decision-logic changes.
Notification text plain-English, one line, actionable.
Tests: flip → notify; no flip → silent; stand-aside days with
no changes stay silent (zero-noise rule).
