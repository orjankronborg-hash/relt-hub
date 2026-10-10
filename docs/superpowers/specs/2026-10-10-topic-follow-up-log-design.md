# Topic-level follow-ups and the Action Log

**Date:** 2026-10-10
**Status:** Design approved, pending spec review

## Problem

A RELT topic gets discussed, something gets written into the minutes, and nothing
structurally carries it to the next session. Today only `Decision` topics have
anywhere to record a follow-up — the `nextSteps` and `responsible` fields in the
decision panel ([index.html:1842](../../../index.html)). A Discussion, Orientation
or Workshop topic has nowhere at all.

There is also no way to see what is outstanding across sessions, so preparing the
next agenda means re-reading old minutes.

## Intended outcome

Close the meeting loop. Every real agenda topic can produce trackable follow-ups
with an owner and a timeline; open follow-ups are visible in one place for agenda
prep, and are forced in front of the team at the start of the next session.

Success looks like: before setting an agenda, Ørjan opens one view and sees
everything still owed, by whom, and how overdue it is.

## Scope

### In

- A collapsed follow-up line on eligible topic types, activated by a checkbox.
- Structured follow-up rows: description, responsible, timeline, status.
- An Action Log view in the sidebar, with filters.
- An open-follow-ups block pinned to the next upcoming session.
- Splitting staging onto its own Firebase document (prerequisite, see below).

### Out

- No digest, copy-to-clipboard summary, Slack, or email.
- No Google Sheets export; `automation/*.gs` is not modified.
- No change to `Decision` topics or to the Decision Log.
- No migration of existing `nextSteps` / `responsible` data.

## Prerequisite: separate the staging document

Staging and production are byte-identical except for the page title and a badge,
and both read and write `DOC_ID = 'relt-hub-v2'`
([index.html:882](../../../index.html), [staging/index.html:883](../../../staging/index.html)).
Staging is therefore a visual preview, not a sandbox — anything typed there lands
in live team data.

This must be fixed **before** the feature work, because the feature has no test
suite and can only be verified by driving the real app.

```diff
  // staging/index.html
- const DOC_ID = 'relt-hub-v2';
+ const DOC_ID = 'relt-hub-staging';
```

Same Firebase project, same auth, no new infrastructure. On first load staging
seeds a fresh tree via the existing path in `initFirebase`
([index.html:2968](../../../index.html)).

## Data model

Two new fields on a topic. Nothing existing is renamed, moved, or removed.

```js
followUp: false,        // the checkbox — "this topic needs a follow-up"
actions: [
  { id:     '_x7k2m9',
    text:   'Validate elasticity with Analytics',
    owner:  'Kjersti Høklingen',
    due:    '2026-10-21',           // ISO date, may be empty
    status: 'Open' }                // 'Open' | 'Done' | 'Dropped'
]
```

`followUp` is kept separate from `actions.length` deliberately: during a live
meeting you often know a topic needs follow-up before you know who owns it. The
flag can be set first and the row filled in afterwards.

`due` is optional. An empty `due` sorts last and is never flagged overdue.

### Why no sync work is needed

`save()` ([index.html:985](../../../index.html)) writes the whole `S.sessions`
tree to Firebase, and `normalizeFbData` rehydrates nested arrays on read. New
nested fields ride along untouched. The Apps Script at
[automation/copy-prereads.gs:169](../../../automation/copy-prereads.gs) reads only
`t.owner` and `t.responsible`, so it is unaffected.

### Defaults

- Any signed-in user can add, edit, and close follow-ups. This matches how
  decision fields behave today; only session add/delete is gated by
  `isSessionAdmin()` ([index.html:968](../../../index.html)).
- `Done` and `Dropped` rows stay visible under their topic, so the record
  survives, but drop out of the carry-forward block and are filtered out of the
  Action Log by default.

## Surface 1: the follow-up line on a topic

### Eligibility

`detailHtml` ([index.html:1485](../../../index.html)) is called for *every* topic,
including Break and Lunch ([index.html:1480](../../../index.html)). The gate must
therefore live inside `detailHtml`.

| `t.type` | Follow-up line | Reason |
| --- | --- | --- |
| `''`, `Orientation`, `Discussion`, `Workshop` | yes | no way to capture follow-ups today |
| `Decision` | no | already served by the decision panel |
| `Break`, `Lunch` | no | not real agenda items |

Types come from `TYPES` at [index.html:1126](../../../index.html).

A topic switched to `Decision` after follow-ups were added keeps the data in
`actions` but stops rendering the line. Switching back reveals it unchanged —
`updType` ([index.html:1557](../../../index.html)) already re-renders the detail
panel on type change, so this falls out of the existing behaviour.

### Collapsed state

Rendered last in the detail panel, after Meeting Minutes:

```text
☐  FOLLOW-UP REQUIRED
```

### Expanded state

```text
☑  FOLLOW-UP REQUIRED                                             1 open

   DESCRIPTION                      RESPONSIBLE     TIMELINE    STATUS
   ┌────────────────────────────┐  ┌───────────┐  ┌─────────┐  ┌──────┐
   │ Validate elasticity w/ Ana…│  │ Kjersti  ▾│  │ 21 Oct  │  │Open ▾│
   └────────────────────────────┘  └───────────┘  └─────────┘  └──────┘
   + Add follow-up
```

- Ticking the box creates one empty row and focuses the description field.
- `+ Add follow-up` appends a row. The common case stays a single line.
- **Responsible** is an `<input list="owner-list">`, reusing the datalist built
  from `OWNERS` ([index.html:2445](../../../index.html)) that already backs the
  topic Owner column. Off-roster names can still be typed.
- **Timeline** is `<input type="date">`, allowed to be empty.
- **Status** is a select: Open / Done / Dropped.

Unticking the box while rows still hold content prompts for confirmation; the
rows are retained in `actions`, not deleted, so a mis-click loses nothing.

Field edits call `saveLocal()`; status changes and row add/delete call `save()`.
This mirrors the existing split, where keystroke-level edits stay local and
structural changes push to Firebase.

## Surface 2: the Action Log

A new sidebar item under PLANNING, directly after Decision Log, built on the same
pattern as `renderDecisionLog` ([index.html:2013](../../../index.html)).

```text
ACTION LOG
Owner [All ▾]   Status [Open ▾]   [☑ Overdue only]
┌──────────────────────────────────────────────────────┐
│ OVERDUE                                              │
│  Validate elasticity with Analytics                  │
│  Kjersti · 21 Oct · Team augmentation pilot      →   │
├──────────────────────────────────────────────────────┤
│ THIS MONTH                                           │
│  Draft board summary                                 │
│  Ørjan · 4 Nov · Pricing model 2027              →   │
└──────────────────────────────────────────────────────┘
```

- Groups: Overdue → This month → Later → No timeline.
- Rows are editable in place and write through to the source topic, the same
  two-way sync the Decision Log already implements via `updDLField`
  ([index.html:2067](../../../index.html)).
- `→` deep-links to the originating topic using the existing `goToAgendaTopic`
  ([index.html:2049](../../../index.html)).
- The nav item carries a badge with the open count.
- Registration follows the existing pattern in `showTab`
  ([index.html:1906](../../../index.html)): a `#action-log-view` container, a
  display toggle, a breadcrumb name, and a `renderActionLog()` call.

## Surface 3: the carry-forward block

Pinned above the topic table of the **next upcoming session only** — the earliest
session whose `parseSessionDate` ([index.html:1147](../../../index.html)) value is
today or later.

```text
┌──────────────────────────────────────────────┐
│ ↺  OPEN FOLLOW-UPS                      3  ▾ │
├──────────────────────────────────────────────┤
│ ☐ Validate elasticity                        │
│   Kjersti · OVERDUE 21 Oct                   │
│   from: Team augmentation pilot · 10 Sep     │
│ ☐ Draft board summary                        │
│   Ørjan · due 4 Nov                          │
└──────────────────────────────────────────────┘
```

It collects every `Open` action from sessions dated earlier than that session.
Ticking an item sets its status to `Done` on the source action and removes it from
the block.

Collapsed by default, showing only the count; hidden entirely when the count is
zero, so it never pushes the agenda down for nothing.

**Why only the next session:** rendering it on every future session would show the
same stale items three meetings out, which trains people to ignore the block.

## Known consequence

Decision topics are excluded, so follow-ups arising from a decision stay as free
text in `nextSteps` and never reach the Action Log or the carry-forward block.
Agenda prep therefore requires two views: the Decision Log for what was decided,
the Action Log for what was promised elsewhere.

This is an accepted trade-off. If it proves limiting, Decision topics can be added
to the same follow-up line later without any data-model change, since the
structure would be identical.

## Verification

This repo has no test suite — it is a single HTML file deployed from `gh-pages`.
Verification is by driving the app in **staging**, after the `DOC_ID` split:

1. On a `Discussion` topic, tick FOLLOW-UP REQUIRED; confirm one empty row appears.
2. Fill description, responsible, timeline; reload; confirm it persisted via Firebase.
3. Confirm the line is absent on `Decision`, `Break`, and `Lunch` topics.
4. Switch the topic to `Decision` and back; confirm the data survives the round trip.
5. Confirm the row appears in the Action Log under the correct due-date group.
6. Edit the row in the Action Log; confirm the change reflects on the topic.
7. Back-date a session; confirm the item appears in the next session's block.
8. Tick it in the block; confirm it closes on the source topic and leaves the block.
9. Confirm the block is hidden when nothing is open.
