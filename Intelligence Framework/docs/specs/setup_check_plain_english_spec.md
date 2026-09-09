# Spec: setup_check plain-English rewrite (display layer only)

**Status:** team-directed 2026-09-09. `setup_check.py` is PROTECTED (listed
2026-09-09) — spec first, branch, both gates, merge held.
**Contract:** every rendered line reads as a colleague explaining, not a
field dump — same plain-English rules and banned-token enforcement as
`decision_brief`. **Journal schema unchanged** (the 21 columns of
`pre_trade_journal.csv` stay byte-identical in name and order); what changes
is the sentences stored in the free-text columns, which have always held the
rendered lines. Decision logic, soft-gate semantics (always logs, never
blocks), markers, and the read-only stance are untouched.

## The six lines (templates; live values interpolated)

- **BIAS** — "The weekly chart shows <plain weekly>. The daily chart
  <hasn't picked a direction yet | is trending up/down | is moving
  sideways> (trend strength N/100)." Exhaustion subtypes render with the
  overextension phrase, same as decision_brief (the subtype fields are
  already in the regime dict — no re-derivation).
- **REGIME** — "The 4-hour chart is <quiet and sideways | trending … |
  choppy with no clear direction | overextension phrase>. <delta sentence>.
  The framework itself says: <don't trade right now | trade LONG/SHORT>
  (rating X)." When against the framework's read: "You'd be trading against
  its read — allowed, but know why you disagree before you act."
  **Bug fixed here:** the session delta already begins "Since …:", and the
  old line prepended "since last run:" — producing "since last run: Since
  44min ago: …". New rendering uses the delta's parts directly: unchanged →
  "Nothing has changed since the last read 44 minutes ago."; changed →
  "Since the last read 44 minutes ago: <plain change>."
- **PLAY** — suggested: "This looks like a <first pullback after a break |
  break of a tight coil | push through the range edge | fade of the 4-hour
  trend at a level> — <why>. Agree?" · none: "This doesn't match any play
  in the playbook (base break, coil break, first pullback, retest fade).
  If you can't name it, it's a feeling, not a trade."
- **CLOCK** — "No major economic release in the next 2 hours." / "<event>
  in <1h 40m> — stand aside until after." / calendar unavailable → "The
  news calendar is out of date — event risk is unchecked." Intervention
  watch (GBP/JPY) appends its warning as today.
- **FUEL** — stale: "This week's storyline for this pair is out of date
  (last approved <date>) so it can't count as evidence. Refresh it in the
  Sunday session." · agrees: "Your direction AGREES with the week's
  storyline: <legs>." · conflicts: "CONFLICTS with the storyline: <legs and
  what the trade needs>." · neutral/missing keep their meaning in plain
  words. **Parser note (additive):** `parse_storylines` also accepts
  `approved YYYY-MM-DD` as the dated header — the live storylines.md has
  always used "(approved <date>)" while the parser only matched
  "updated:", so the real file was treated as undated. Existing "updated:"
  fixtures keep working; this makes "last approved <date>" printable.
- **RISK** — found stop: "The nearest level that would prove this trade
  wrong is <price> — <N> pips <above|below> price." plus:
  - **NOISE FLAG (new):** when the stop distance is closer than
    `MIN_STOP_ATR_MULTIPLE` × daily ATR — constant lives in
    `setup_check.py`, **INFORMED PRIOR, start 0.3**, exhibit: Episode 1
    (33-pip stop, 809.2-pip MFE, validation_log 2026-09-09) — render: "At
    today's volatility (<ATR>-pip daily range) that's inside normal noise:
    it would get hit by accident, not by being wrong. Wait for the market
    to give you a real invalidation level." (the word "invalidation"
    appears ONLY inside this directed template sentence — see banned list
    note below; implemented as "…a real level that means something" to
    keep the ban absolute).
  - wide-stop breach keeps its warning in plain words.
  - with `--target`: "The target pays <R> times what you risk (<R> after
    the spread)."; if the stop is inside noise: "That ratio is flattering
    only because the stop is fake."
  - no stop found: "No clean level on the hourly or daily would prove this
    trade wrong — define your stop by hand before trading."

## Prompts

"PLAY — does that match what you see? [Enter]=agree o=write your own read
b=leave it blank (blank is an honest answer):" — `o` now actually captures
the typed read into the line's column (marker `overridden`); previously the
override text was lost. Same for FUEL.

## VERDICT (advisory — soft gate, never blocks)

Rendered as the last line and appended to the journal's `risk` column after
" | " — **the explicit schema-unchanged compromise, flagged for review**:
the 21 columns stay; the verdict travels in the stack's synthesis line.

- Negative — any blank line, stop inside noise, or fuel CONFLICTS:
  "VERDICT: <the weaknesses present, enumerated — N blank line(s) / stop
  inside noise / against the storyline / against the framework's read>.
  Nothing here says NOW."
- Positive — no blanks, fuel AGREES, a found stop that is neither noise
  nor breach, clock clear, not against the framework, play named:
  "VERDICT: Every line supports this. Size per your rules."
- Otherwise: "VERDICT: Mixed — <the weak lines named>."

Computed AFTER the confirm prompts (blanks count).

## Banned tokens (test-enforced on rendered output)

Existing set (ADX / HH-HL / LH-LL / pivot / ATR-ratio) plus, for
setup_check: `invalidation`, `none-named`, `structural`, bare `regime` and
bare `stack` inside sentence bodies. The six section labels
BIAS/REGIME/PLAY/CLOCK/FUEL/RISK are labels and exempt; the header renames
PRE-TRADE STACK → **PRE-TRADE CHECK** and the footer reword drops bare
"stack" ("recorded → pre_trade_journal.csv (id …)"). Because
`invalidation` is banned, the RISK noise sentence closes with "a real level
that means something" rather than the directive's literal "…real
invalidation level" — same meaning, ban kept absolute; flagged here so
review sees the substitution.

## Gates

- **Gate 1:** pinned tests for every line variant (BIAS trending/sideways/
  undecided/exhaustion; REGIME unchanged-delta / changed-delta / agree /
  against; PLAY all five; CLOCK clear/gating/unavailable/intervention;
  FUEL stale-with-date/agrees/conflicts/neutral/missing; RISK found/noise/
  breach/target/fake-ratio/no-stop) and all three verdicts; banned-token
  test extended per above; journal round-trip shows verdict in the risk
  column and 21 unchanged headers.
- **Gate 2 (REALITY):** today's live GBP/AUD SHORT rendered in full — with
  the live state (framework says don't trade; storyline stale; nearest
  level ~25 pips inside an 83-pip range) it must end with the "Nothing
  here says NOW." verdict, and the journal row written.
