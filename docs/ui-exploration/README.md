# UI direction prototypes - deal pipeline

**The question:** what should AuraOS look like? Three radically different visual directions for the deal pipeline screen, switchable with the floating bar at the bottom of each page (or the left/right arrow keys).

Throwaway code. Static, self-contained HTML - no build step, no server, no dependency on the live app. Nothing under `frontend/` was touched.

## Run it

Copies are served on the LAN by the existing `aura-board-http.service` (port 8200), so open them from any machine on the network:

| Key | Direction | LAN link | File |
| --- | --- | --- | --- |
| A | Call sheet | http://192.168.1.94:8200/pipeline-call-sheet.html | `pipeline-call-sheet.html` |
| B | Grading suite | http://192.168.1.94:8200/pipeline-grading-suite.html | `pipeline-grading-suite.html` |
| C | Studio brand | http://192.168.1.94:8200/pipeline-studio-brand.html | `pipeline-studio-brand.html` |

The files in this directory are the originals; `/var/lib/aura-board/` holds serving copies. Re-copy after editing, and delete them from there once the direction is picked (`rm /var/lib/aura-board/pipeline-*.html`) - that directory otherwise belongs to the board.

The bottom bar cycles between them. It is deliberately ugly - it is a tool, not part of any design being judged.

## What is fixed and what varies

Every direction renders the **same eight deals across the same seven stages**, so the only variable is the design. The fixture data, the rules each design must express, and the three direction briefs all live in `claude-prototype-prompt.md` (wayfinder ticket #77).

## Measured at 1440px wide

All three render correctly, show all 8 deals with full figures (`850,000,000 VND`, never abbreviated), and set Vietnamese diacritics in faces that support them. Where they differ is how much board fits on screen:

| Direction | Board width at 1440px | Reaching Won / Lost |
| --- | --- | --- |
| A - Call sheet | 1440px, fits | Visible without scrolling |
| B - Grading suite | 1710px | Short scroll; terminal panel is pinned right |
| C - Studio brand | 2463px | Needs ~1.7 screens of scroll |

That is the central tradeoff on the table: C buys its presence with oversize stage headers and pays in scroll, A fits everything and pays in warmth. Each direction's author also flagged an honest weakness - C's mobile height (about 7,000px at 3x cards), B's Negotiation column falling off-screen below 1700px, A's money line having only ~10px slack at its minimum column width.

## How to judge

React in front of the pages, not from memory. Which one would you want to open every morning? The useful answer is often "the stage headers from C with the money treatment from A" - a mix is a legitimate result.

Two things the founder scans for, so test both: **total value per stage**, and **anything stalled**.

## Other documents here

- `design-agent-prompt.md` - the full 22-surface brief for whoever designs the rest of the app.
- `claude-prototype-prompt.md` - the master prompt and direction briefs these pages were generated from.

## After the pick

Fold the winning direction into the real Vue frontend, then move these files onto a `prototype/ui-directions` branch out of main and point at it from the implementation issue. Do not promote this HTML directly - it was written under prototype constraints.
