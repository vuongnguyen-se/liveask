# UI design plan (taste-skill 2.5.1)

Decisions: D-016 (scope), D-017 (self-hosted fonts), D-018 (vendored kit). Tasks: `TASKS.md`, UI-00 to UI-07. Copy: [`landing-copy.md`](landing-copy.md).

## Plan line 1: the kind

**software** (page type `software`, site-kind `software`, kind `software`): an app whose product is a window. The page is the landing page `/`. The audience, host and screen views are app screens and take the design system only (D-016).

- **What is sold:** live Q&A and polls for presenters (nothing is charged; there is no price on the page).
- **Who uses it:** presenters (host), their audience on phones, the projector screen.
- **The one main action:** **Create a room**. It reads the same in the nav, the hero and the close, and is the only filled button.
- **Second action:** **Join a room** (the audience's way in when they type a code).

## Fact sheet (every fact is in the repo docs or the shipped app)

| Field | Content | Source |
|---|---|---|
| What it is | Real-time Q&A and polls for presentations | `PROJECT_REQUIREMENTS.md` 1 |
| For whom | Presenters running a class presentation, club meeting or small event. Not for: events that need accounts, sign-in or saved history | 1, 2 |
| What they do today instead | The audience rarely asks out loud; the presenter has no quick way to run a poll | 1 |
| The true difference | No sign-up; QR code; every change reaches phones, host and projector live, whichever server each is connected to | 1, `ARCHITECTURE.md` 2 |
| Numbers | 6-character code; 280 characters per question; 5 questions a minute per phone; 2 to 6 poll options; 6 top questions on the screen; rooms expire after 24 hours | FR-1 to FR-8, shipped app |
| A limit (the page's one admission) | The host link is shown once and only its hash is stored, so it cannot be shown again | `SECURITY_AND_COST.md` 1 |
| An enemy | Questions nobody asks out loud | 1 |
| The offer | Free to use; one title and one click | (no price in the brief: none shown) |
| Proof | None in the brief: no quotes, customers or figures, so none on the page | |

## Voice card (one line)

Product as the hero (register 11) with one move from technical-dry (2): the product is the subject, the mechanism in verb-led steps, real values in the sentences. Full card at the top of `landing-copy.md`.

## The page as screens

Kind software, deal below. The first screen holds the hero alone; every section is one screen at 1440x900 (`--h: 1`) unless stated. Words per screen outside UI mocks: 60 to 80.

| # | id | One idea | Its picture (kind) | Screens | Holds |
|---|---|---|---|---|---|
| 0 | `top` (nav) | The name, four nouns, the one button | the mark (initial) | fixed | `nav-split` |
| 1 | `hero` | What it is, who for, the action | the **app-frame**: LiveAsk's own audience view with a live poll, as live HTML (use) | 1 | `centred` hero, hero entrance |
| 2 | `console` | The presenter runs the room from one page | the **app-frame** at size: console list beside the open question (object) | 1 | |
| 3 | `questions` | Questions rise by votes | three UI fragments on cards (parts) | 1 | features layout A |
| 4 | `polls` | A poll with live results | the poll fragment in a split, text left (use) | 1 | features layout B |
| 5 | `screen` | A screen for the projector | the screen view with the QR code (use) | 1 | features layout C |
| 6 | `sync` | Every server hears every change | a **diagram card**: phones, server A, server B, PostgreSQL, projector, with pulses along the lines | 1 | `dark-band` |
| 7 | `formats` | Made for classes, clubs and events | type | 1 | the dealt moment `marquee-row` |
| 8 | `faq` | Five plain answers | none (FAQ is allowed picture-less once) | 1 | calm section before the close |
| 9 | `footer.closing` | Create your first room | the big button (close-type) | 1 | `close-type`, `footer-statement` |

Object lines (the app-frame whole): hero, `console` and `screen` = 3, the allowed maximum. Layouts A, B, C differ (three cards, split, bento); no layout is used more than twice.

## The deal (printed by the dealers, never chosen by taste)

| Part | Result | Command | Why it fits |
|---|---|---|---|
| Hero | **centred** | `deal.mjs --type software --has ui` | The product is one window (a live question list), the case this hero is for. Its 36-character h1 limit holds: "Live Q&A and polls for presenters" is 33 |
| Palette | **cool-white-slate** "Frost and slate" (bg `#f7f9fa`, surface `#ecf0f2`, ink `#1f3038`, accent `#0d7480`) | `start.mjs deal --page software` (first of three) | An off-white ground and one teal accent keep a projector view calm and readable, and teal is clear of violet. The accent is the primary button, links and the focus ring only |
| Type | **host**: Host Grotesk (display 500, text 400/500) + JetBrains Mono | same deal (first of three) | An even neo-grotesk for questions people read at a distance; the mono is for the room code |
| Radius | **round** (10/16/24) | rule: round for consumer apps | The audience uses it on phones with large tap targets |
| Nav | **nav-split** | re-dealt (see below) | Words left, name in the middle, no photograph panel needed |
| Footer | **footer-statement** | dealt | The lit ground, allowed on tech |
| Close | **close-type** | dealt | The h2, one line and the big button |
| Rhythm | **dark-band** | dealt | One dark section holds the strongest visual: the `sync` diagram |
| Buttons | **tonal** | dealt | one filled primary, one tonal secondary |
| Mark | **initial** ("L") | dealt | |
| Moment | **marquee-row** | `moments.mjs pick --page software --count 1` | One row of formats moves slowly, pauses on hover and has a pause button; it sits in its own section |

**Re-deal, with its reason:** `nav-cards` was dealt first. It needs picture cards, and the page has no photographs (the product is its own UI), so the rules say to deal again from `nav-split` and `nav-centre`: `nav-split` came up.

**Effect and scene:** the software kind may carry one shader effect. This plan takes **none**: a WebGL ground costs battery on the phones the audience holds and adds nothing to a page that is already one live window, one diagram and one moment. The checker accepts a software page without one; if it does not, the effect is dealt in UI-03 and the reason is recorded here.

## The tokens (kept exactly as `start.mjs css --page software --palette cool-white-slate --type host --radius round` prints them)

```css
:root {
  --p-bg: #f7f9fa; --p-surface: #ecf0f2; --p-ink: #1f3038; --p-muted: #5d6b72;
  --p-accent: #0d7480; --p-accent-ink: #ffffff; --p-action: #0d7480; --p-action-ink: #ffffff;
  --p-inv-bg: #1f3038; --p-inv-surface: #2c3c44; --p-inv-ink: #f7f9fa; --p-inv-muted: #9ea7ab;
  --p-inv-accent: #f7f9fa; --p-inv-accent-ink: #1f3038; --p-inv-action: #f7f9fa; --p-inv-action-ink: #1f3038;
  --font-display: "Host Grotesk", system-ui, sans-serif;
  --font-text: "Host Grotesk", system-ui, sans-serif;
  --font-mono: "JetBrains Mono", ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace;
  --display-weight: 500;
  --display-tracking: -0.035em;
  --display-tracking-xl: -0.04em;
}
```

`<html lang="en" data-type="software" data-radius="round" data-buttons="tonal" data-motion>` plus the three metas (`page-type`, `site-kind` = software).

## How it reaches the app views (D-016)

The audience, host and screen pages use the same tokens, the same two faces, the same radius and the same button and card recipes, and follow the skill's accessibility rules. They do not use its section, hero or moment rules. The footer and nav of the landing page are not repeated on them.

## Decisions taken while planning, and open points for UI-03

1. **Fonts (D-017):** the dealer prints a Google Fonts link. We download the Host Grotesk and JetBrains Mono woff2 files once (SIL Open Font License), commit them, and write `@font-face` ourselves. At most four font files.
2. **Create a room.** The main action goes "where it is done": `#create`, a one-field form (title) in the closing section; the nav and hero buttons link there. The form must work with the page's own code (it posts `/api/rooms` and moves to the host page). The skill's form recipe and `system.js` also handle forms: UI-03 checks that they do not both act on this form.
3. **Join a room.** Hero button and footer link go to `#join`, a one-field form (code) in the footer. It works without JavaScript through a new `GET /join?code=` route that answers `303` to `/r/CODE` (and back to the form with an error for a malformed code). This is the only server change in the UI track and gets a test.
4. **Real icons.** The `sync` diagram may show the PostgreSQL icon in its own colours (`icons.mjs`, may need the network once; the file is then kept locally). If it cannot be fetched, the diagram uses labels only, never a drawn look-alike.
5. **Legal row:** brand, year, "Source code" (the public repository). Privacy and Terms are left out (no page to link, the skill allows leaving them out). No credits line: no photographs and the fonts need none.
6. **Not on the page:** pricing, customers, quotes, counts of users, a phone number, an email, a map.

## What I could not check yet

- That `consistency.mjs`, `check.mjs` and `gate.mjs` run on this machine (they need Chrome or Edge via their own scripts).
- That self-hosted faces pass the skill's `font-load` check.
- The word count per screen (it is counted on the built page, `copy-lint` and the checker).
- Whether the software kind insists on one effect.

## Self-check of the copy (copy-voice.md section 6)

- **Lint:** 0 FAIL, 0 WARN.
- **Rival's name test:** the h1 names a category ("Live Q&A and polls for presenters"), as copy.md rule 1 asks for an unknown brand, so a rival could use it. The specifics sit in the lines under it (QR code, phones, projector, 24 hours) and in the FAQ's admission.
- **Over-correction:** no heading is a question and none is two fragments; the only list of three is the verbs of the console line and the marquee words.
- **Read aloud:** each line is one a presenter could say about the product.
