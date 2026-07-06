## Text Encoding

This repository contains Chinese Markdown and skill files. When checking
whether a text artifact is corrupted, do not rely on PowerShell `Get-Content`
output in the current console codepage.

Read Markdown / skill files with explicit UTF-8 first:

```powershell
@'
from pathlib import Path
p = Path("skills/material-map.md")
text = p.read_text(encoding="utf-8")
print(text[:800])
print("contains replacement char:", "\ufffd" in text)
'@ | python -
```

Only report an encoding/corruption issue after explicit UTF-8 decoding and a
replacement-character check.

When creating or repairing Chinese JSON/SRT/Markdown artifacts on Windows, do
not pass raw Chinese text through PowerShell here-strings, stdin, `>`,
`Out-File`, or `Set-Content`. The text may be replaced with literal `?` before
Python receives it.

Use one of these safer paths instead:

- Read Chinese text from an existing UTF-8 file and write with
  `Path.write_text(..., encoding="utf-8")`.
- Represent newly authored Chinese literals with Python Unicode escapes
  (`"\u8a13\u7df4..."`).
- Use `apply_patch` for repo text files when editing manually.

After writing Chinese artifacts, verify generated JSON/SRT/Markdown with
explicit UTF-8 decoding and check both:

- `"\ufffd" not in text`
- No suspicious repeated literal question marks in Chinese fields, such as
  `"????"` or a high `?` count where Chinese text is expected.
