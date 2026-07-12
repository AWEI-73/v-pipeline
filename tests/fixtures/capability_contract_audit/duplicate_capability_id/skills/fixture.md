<!-- TOOL_CONTRACT_START -->
{
  "version": 1,
  "skill": "fixture",
  "stage_owner": "fixture_stage",
  "capability_namespace": "cap.fixture.*",
  "capability_lookup_owner": "fixture-owner",
  "triggers": [
    "fixture"
  ],
  "forbidden_tools": [],
  "canonical_tools": [
    {
      "capability_id": "cap.fixture.tool.v1",
      "tool": "tools/example.py",
      "loops": [
        "L3"
      ],
      "maturity": "bounded",
      "certified_scope": "fixture scope",
      "when": "run fixture",
      "inputs": [
        "in.json"
      ],
      "outputs": [
        "out.json"
      ],
      "stop_if": [
        "bad"
      ]
    }
  ],
  "supporting_tools": [
    {
      "tool": "tools/support.py",
      "when": "support fixture",
      "inputs": [],
      "outputs": [],
      "stop_if": []
    }
  ],
  "internal_tools": [
    {
      "tool": "tools/internal.py",
      "when": "internal fixture",
      "inputs": [],
      "outputs": [],
      "stop_if": []
    }
  ],
  "diagnostic_tools": [
    {
      "tool": "tools/diagnostic.py",
      "when": "diagnose fixture",
      "inputs": [],
      "outputs": [],
      "stop_if": []
    }
  ]
}
<!-- TOOL_CONTRACT_END -->
<!-- TOOL_CONTRACT_START -->
{
  "version": 1,
  "skill": "other",
  "stage_owner": "fixture_stage",
  "capability_namespace": "cap.fixture.*",
  "capability_lookup_owner": "other",
  "triggers": [
    "fixture"
  ],
  "forbidden_tools": [],
  "canonical_tools": [
    {
      "capability_id": "cap.fixture.tool.v1",
      "tool": "tools/other.py",
      "loops": [
        "L3"
      ],
      "maturity": "bounded",
      "certified_scope": "fixture scope",
      "when": "run fixture",
      "inputs": [
        "in.json"
      ],
      "outputs": [
        "out.json"
      ],
      "stop_if": [
        "bad"
      ]
    }
  ],
  "supporting_tools": [
    {
      "tool": "tools/support.py",
      "when": "support fixture",
      "inputs": [],
      "outputs": [],
      "stop_if": []
    }
  ],
  "internal_tools": [
    {
      "tool": "tools/internal.py",
      "when": "internal fixture",
      "inputs": [],
      "outputs": [],
      "stop_if": []
    }
  ],
  "diagnostic_tools": [
    {
      "tool": "tools/diagnostic.py",
      "when": "diagnose fixture",
      "inputs": [],
      "outputs": [],
      "stop_if": []
    }
  ]
}
<!-- TOOL_CONTRACT_END -->
