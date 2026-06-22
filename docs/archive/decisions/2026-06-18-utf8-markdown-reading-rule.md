# UTF-8 Markdown Reading Rule

Date: 2026-06-18

## Decision

When reviewing project Markdown, skill files, or other text artifacts that may
contain Chinese, read the file with explicit UTF-8 decoding before reporting text
corruption.

Recommended check:

```powershell
@'
from pathlib import Path
p = Path("skills/material-map.md")
text = p.read_text(encoding="utf-8")
print(text[:800])
print("contains replacement char:", "\ufffd" in text)
'@ | python -
```

Do not treat PowerShell `Get-Content` output in the current console codepage as
authoritative evidence of file corruption.

## Why

`skills/material-map.md` appeared corrupted when read through the PowerShell
console, but the file was valid UTF-8 and displayed correctly when decoded
explicitly. The earlier observation was a tool/console decoding mistake, not a
project artifact problem.

## Rule For Future Agents

If a text file appears garbled:

1. Re-read it with explicit UTF-8.
2. Check for replacement characters (`\ufffd`).
3. Only then report an encoding or corruption issue.

