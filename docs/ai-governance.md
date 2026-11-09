# AI governance notes

A short record of how the AI in this app is used and kept in check. It is written the way I would want one written for any AI tool that feeds a leadership or board report.

## Intended use

- Read weekly free-text program updates and report the status they support, with the risks and decisions they mention.
- Draft a one-page weekly brief for the founder and board.

## Not intended for

- Making decisions. The AI reports; people decide.
- Judging individual performance. Status is about programs, not people.
- Anything sent outside the company without a named person approving it.

## Controls

| Risk | Control | Where |
|---|---|---|
| The AI invents facts | Every status, risk and decision must carry an exact quote from the update. Quotes are checked in code. Failed items are flagged and blocked from the brief until reviewed. | `pulse/grounding.py`, Program detail page |
| Malformed or unexpected output | Forced tool call with a fixed schema, then Pydantic validation. | `pulse/ai.py`, `pulse/models.py` |
| AI text reaches the board unchecked | Every brief line needs Approve, Edit or Reject. Only approved and edited lines are exported. | `pulse/brief.py`, Weekly brief page |
| Optimistic self-reporting hides problems | The AI status is shown next to the owner's color, and a rule flags green reports with risky text. | `pulse/drift.py`, Portfolio page |
| Nobody can tell what produced a result | Model name and prompt version are stored with every output and every audit entry. | `pulse/prompts.py`, `pulse/audit.py` |
| Untraceable changes | Audit log of every suggestion, approval, edit, rejection, failed check and export. | AI audit log page |
| Lab figures presented as customer results | The brief prompt forbids it, and a rule flags lab-style figures (99.99%, 4-log, "within N minutes") in brief lines. Flagged lines cannot be approved until rewritten with field results or labelled as lab results. Flags are logged. | `pulse/brief.py`, Weekly brief page |
| The AI guesses owners or dates | Prompt tells it to leave owner and needed-by empty unless the update states them. The app shows "not stated". | `pulse/prompts.py` |
| Leaked API key or runaway cost | Key kept in Streamlit secrets, never in code. Public demo runs on saved outputs. Live mode is off unless a key is present. | `pulse/ui.py` |
| Sensitive data in prompts | All data is synthetic. A real deployment would need a data handling review before sending updates to an external API. | |

## Planted failures

The saved demo outputs include two deliberate mistakes so visitors can watch the controls work:

- A risk on the investor update that quotes words not found in the update. The grounding check catches it and locks the related brief lines until a reviewer fixes it. `tests/test_grounding.py` makes sure it stays the only one.
- A brief line saying the units remove 99.99% of mold at customer sites. The lab-figure rule blocks approval until the line is rewritten with field results. `tests/test_brief_and_audit.py` covers it.

## Why the lab-figure rule exists

Manufacturer lab tests run in sealed chambers against one organism for a fixed time. Occupied rooms have open doors, people and changing humidity, so field results are lower. Quoting a lab number to a school, a ministry or an investor as if it were their result is the fastest way to lose trust, and an AI summarizing product material will happily repeat it.

## Known limits

- The grounding check proves the quote exists, not that the AI read it correctly. A real quote can still support a wrong conclusion, which is why a person approves the brief.
- The AI sees one update at a time, so it can miss patterns across weeks. The drift rules cover the common ones.
- Status thresholds (on track, at risk, off track) are judgment calls written into the prompt. Teams should agree on them before relying on the output.

## What I would measure in production

- Share of AI lines reviewers edit or reject, week over week (shown on the audit log page)
- Grounding failures per 100 items
- Agreement between AI status and the status leadership settles on after discussion
- Time from last update to approved brief

## Mapping to the NIST AI Risk Management Framework

| Function | In this app |
|---|---|
| Govern | Named reviewer on every approval, documented intended use, prompt versioning |
| Map | Clear scope above: what the AI does and does not do, who sees its output |
| Measure | Grounding check, edit and rejection rates, tests on the demo outputs |
| Manage | Locked brief lines, human approval gate, audit log, demo mode for public use |
