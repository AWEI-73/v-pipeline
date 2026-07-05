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
