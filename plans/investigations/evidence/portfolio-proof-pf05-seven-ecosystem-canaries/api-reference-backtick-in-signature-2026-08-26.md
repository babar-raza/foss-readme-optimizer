# PF05-APIREF-BACKTICK-001 — a backtick inside an API signature corrupts the reference table

## Status

Root-caused with an exact reproduction. **Not repaired**: both files involved are
document-contract inputs, so the fix must land in a batch with a full re-run
behind it rather than in the middle of one.

## Symptom

`aspose-words-foss/Aspose.Words-FOSS-for-Python` fails closed:

```
ValueError: compiled verified presentation is invalid:
API reference summary counts disagree with rendered tables
```

Pre-existing, not a regression from this session's API-index change: the same
error appears for the same repository in `runs/logs/poc-all-python-20260826.log`,
produced by a process that loaded its code before that change.

## Root cause

`verified_template_api_reference.py` renders the type cell as single-backtick
inline code, and `_table_cell()` escapes `|` but not backticks. One real Words
signature contains a backtick as a *default argument value*:

```
| `FencedCodeBlock(code, info='', fence_char='`')` | Represents a Fenced Code Block ... |
```

The inner backtick closes the inline-code span early, so the cell is not a single
code span and the row does not match the validator's row pattern in
`validation/presentation_template.py`:

```python
api_rows = re.findall(r"(?m)^\| `([^`]+)` \| ([^|]+) \|$", api_body)
```

Measured on the real bundle (both revisions agree):

```
declared entry_count : 92
rows the validator matches : 91
total rendered table rows  : 92
```

So `declared_entries != len(api_rows)` fires. The count is a symptom; the real
defect is that the table cell is malformed Markdown for any signature containing a
backtick.

## Repair direction

Two coordinated edits, because producer and validator must agree on the delimiter:

1. Render the cell with a CommonMark-legal fence: a run of N backticks in the
   content requires at least N+1 backticks as the delimiter, plus a single space
   of padding when the content starts or ends with a backtick.
2. Widen the validator's row pattern to accept a multi-backtick delimiter rather
   than exactly one.

Escaping or stripping the inner backtick is the wrong fix: `fence_char='`'` is the
member's real default value, and idea.md l.74 requires API members to retain their
source spelling.

## Why it was not repaired in place

`validation/presentation_template.py` is in
`document_templates.DOCUMENT_CONTRACT_IMPLEMENTATION_PATHS`, and
`presentation/verified_template_api_reference.py` matches its
`src/readme_agent/presentation/verified_*.py` glob. Either edit changes
`document_template_hash()`, which invalidates every cached composition plan in the
portfolio and surfaces as `template_hash_matches failed` on repositories that were
otherwise fine. A fleet pass was in flight when this was found, so the change
belongs in the next contract-affecting batch, applied once, with a full re-run
behind it.
