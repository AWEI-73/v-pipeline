import json
import shutil
import os

src = "mock_exhausted_out"
dst = "mock_exhausted_test"

if os.path.exists(dst):
    shutil.rmtree(dst)
shutil.copytree(src, dst)

# Modify candidates.json
cands_path = f"{dst}/candidates.json"
cands = json.load(open(cands_path))
cands["2"]["candidates"] = cands["2"]["candidates"][:1]
with open(cands_path, "w") as f:
    json.dump(cands, f, indent=2)

# Modify picks.json
picks_path = f"{dst}/picks.json"
picks = json.load(open(picks_path))
picks["picks"] = {"1": 1, "2": 1}
with open(picks_path, "w") as f:
    json.dump(picks, f, indent=2)

print("Mock setup completed successfully!")
