# Spec: notification click-through (amended for macOS 13 — no brew, no Xcode)

**Status:** team-directed 2026-09-09, small. Notifications currently carry a
one-line summary and vanish; clicking does nothing. This adds click-to-open
on the day's relevant log, with a graceful fallback that still says where to
look.
**Branch:** `feat/notify-click-through`. Merge held for team review.

## 1. terminal-notifier from the prebuilt official release

Verified against the GitHub API at build time (2026-09-09), repo
`julienXX/terminal-notifier` (the official project; bundle id
`fr.julienxx.oss.terminal-notifier`):

- Version: **3.1.0** (tag `3.1.0`, published 2026-08-30T13:06:57Z)
- URL: https://github.com/julienXX/terminal-notifier/releases/download/3.1.0/terminal-notifier-3.1.0.zip
- SHA-256: `e969d4ae20287da1ba55495ae31dcedd8e9069deb8ce4eed24f6561a5fc3e4d5`
  (400,096 bytes)
- Installed to `~/Applications/terminal-notifier.app`; binary referenced at
  `~/Applications/terminal-notifier.app/Contents/MacOS/terminal-notifier`.
  Universal (x86_64 + arm64), adhoc-signed.

**One-time approvals, observed at build:** the curl download carried no
quarantine attribute, so the Gatekeeper "Open Anyway" step was never
triggered — the binary ran directly. What DID trigger is macOS 13's
notification authorization: the first post blocks until the user answers
the "terminal-notifier would like to send notifications" dialog (or enables
it under System Settings → Notifications → terminal-notifier). Until that
approval is given, the helper's watchdog (below) kills the hung attempt and
falls back to osascript — **no scheduled run can hang on a permission
dialog**.

## 2. One notify function, sourced by every wrapper

`scripts/notify.sh` defines `notify <SUBTITLE> <MESSAGE> <LOG-RELPATH>`:

- Message always gets the pointer appended: `<message> → logs/<file>` — so
  the osascript fallback (which cannot open anything) still tells you where
  to look.
- When the binary exists: `terminal-notifier -title "Intelligence
  Framework" -subtitle <CATEGORY> -message <text> -open file://<abs log
  path, space %20-encoded>`, run under a bounded watchdog
  (`NOTIFY_WATCHDOG_SECS`, default 15): if the notifier hangs
  (unauthorized) or exits nonzero, the same message goes out via the
  osascript fallback instead — a notification is never silently lost.
- When the binary is absent: osascript `display notification` with the
  same title/subtitle/message.

Categories and their logs:

| Caller | Category | -open target |
|---|---|---|
| brief wrapper, watched-condition flips | ALERT | logs/brief_<date>.log |
| brief wrapper, tradeable decision | DECISION | logs/brief_<date>.log |
| brief wrapper, shadow fire | SHADOW | logs/brief_<date>.log |
| both wrappers, health failure | ALERT | that wrapper's day log |
| both wrappers, recovery | RECOVERED | that wrapper's day log |
| outcomes wrapper, shadow graded | SHADOW | logs/outcomes_<date>.log |
| weekly heartbeat | HEARTBEAT | logs/heartbeat_<date>.log |

Notification behavior is otherwise unchanged: same firing conditions, same
one-line texts, exit-0 discipline intact (`notify` always returns 0).

## 3. Gates

- **Gate 1:** helper pinned via bash-under-pytest with a fake `$HOME`
  binary that records its argv: correct title/subtitle/-open URL
  (%20-encoded), pointer appended, osascript NOT called on success;
  binary missing → osascript path with pointer; binary hanging → watchdog
  fires and the osascript fallback carries the message; binary exiting
  nonzero → same. Wrapper category routing pinned.
- **Gate 2 (REALITY):** real notification sent through the installed
  binary; the exact `-open` URL proven to open the log in the default text
  app; fallback exercised for real with the binary temporarily renamed
  (and restored). Any one-time approval encountered is flagged in the run
  report.
- **Gate 3 (pending):** a human clicks a real notification and the log
  opens — the click itself cannot be automated from here.
