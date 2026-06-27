---
name: verify
description: Use when running or reviewing Hermes VERIFY and delivery gates: QA reports, visual/content audits, reviewer artifacts, final review smoke, fail-closed delivery evidence, stale artifact checks, or repair targets after BUILD.
---

# Verify Skill

## Tool Contract

<!-- TOOL_CONTRACT_START -->
{
  "version": 1,
  "skill": "verify",
  "stage_owner": "verify_delivery_gate",
  "triggers": [
    "需要驗證成品、review report、delivery gate、orphan process、或 fail-closed 行為",
    "BUILD 後或 no-render campaign 後需要 reviewer/verify evidence"
  ],
  "canonical_tools": [
    {
      "tool": "tools/stage5_final_review_smoke.py",
      "when": "驗證 final review / delivery gate 邊界，不重跑完整 render",
      "inputs": ["stage5 fixture or run folder"],
      "outputs": ["stage5_final_review_smoke_report.json"],
      "stop_if": ["delivery evidence missing or hard gate fails"]
    },
    {
      "tool": "tools/reviewer_flow_acceptance.py",
      "when": "驗證 reviewer flow 是否會 fail-closed 並回報正確 route",
      "inputs": ["review fixture or run folder"],
      "outputs": ["reviewer_flow_acceptance_report.json"],
      "stop_if": ["reviewer blocks or missing review artifact"]
    },
    {
      "tool": "tools/write_delivery_gate_report.py",
      "when": "write delivery_gate.json from current run artifacts so verify_result.pass=true cannot be mistaken for delivery readiness",
      "inputs": ["run folder with verify/material/audio/subtitle/effect evidence"],
      "outputs": ["delivery_gate.json"],
      "stop_if": ["delivery gate blocks or required evidence is missing"]
    }
  ],
  "supporting_tools": [
    {
      "tool": "tools/orphan_audit.py",
      "when": "檢查是否有孤兒 render / ffmpeg / long-running process",
      "inputs": ["optional process filters"],
      "outputs": ["orphan audit report"],
      "stop_if": ["unsafe long-running process is found"]
    },
    {
      "tool": "tools/test_tiers.py",
      "when": "列出或執行測試分層，用於 focused/full regression 決策",
      "inputs": ["test tier name"],
      "outputs": ["test tier command/report"],
      "stop_if": ["requested tier is unknown"]
    }
  ],
  "forbidden_tools": [
    "Do not use local VLM for VERIFY unless explicitly opted into legacy experiment",
    "Do not call a video passed when delivery evidence is missing",
    "Do not confuse warning-only diagnostics with hard gate pass"
  ]
}
<!-- TOOL_CONTRACT_END -->


## Current visual-judgment policy

VERIFY technical checks remain deterministic and local where possible, but
visual/content judgment is **agent/cloud review by default**. Do not start
Ollama/qwen for VERIFY unless the run explicitly opted into a legacy local-VLM
experiment. When visual judgment is needed, produce or consume the canonical
review artifacts (`visual_review_request.json`, `visual_review_verdict.json`,
or `material_visual_review_*`) and let the route pause at the corresponding
`await_*visual_review` action.
> ## Continuous Verify / QA Contract(Node 12 ??銝蝯?,?航疵蝛踵?園?)
> **VERIFY ?航疵蝛踹瘚???園?,撠文?具?鞎?render 銋???*,銝?敺?蝡?> `verify_result`:`status ??pass / warn / fail / blocked` + `findings`[撅斤?/蝭暺???/撱箄降頝舐] + `next_route`??> **?拙惜瑼Ｘ(撠??拙惜璅∪?):** 璈１瑼Ｘ??(靘踹??eterministic:閬/?/摮?/?喲?/EDL trace/
> 敹?/fallback ?臬鋡恍?暺????**撠芋??VLM(qwen3-vl 蝑????蝡舫?蝖砍神)?芸
> 閬死/隤?/銝餉?瑼Ｘ deterministic 閫??鈭?閫貊** ??human ?芸??斗/identity-proof ?詨/銝餉?撽??targeted??> **AI editor(Node 11)??verify**:editor ?耨瘜?蝺刻摩頝舐;**verify 蝯行迤撘?pass/warn/fail/block ??*??> ?萄?:blocker 銝??ready/approved/render;fallback 鋡恍?暺????fail;timeline item ??trace ??fail??
VERIFY ??pipeline ??暺?蝞∠??? 
**?詨???**嚗?祆 ground truth嚗ERIFY 撠?單瑼Ｘ???箸?虫??氬? 
銝????芾牧?仃??閬?蝣箸???*?芸?Skill 閬耨**嚗ix_target嚗?
---

## 撌亙雿蔭

```
/home/lio730309/.hermes/profiles/video_director/workspace/video_tools.py
```

```bash
python3 video_tools.py verify \
  --script script.json \
  --timing tts_timing.json \
  --edit-log rough_cut_edit_log.json \
  --srt subtitles.srt \
  --video final.mp4 \
  [--threshold 80] [--out qa_report.json]
```

---

## 撠??賭誘
* `[[cmd_verify]]` - 撠??? 5 蝬剖漲閰?嚗蒂頛詨??蝮賢???fix_target 頝舐?內??* `[[cmd_validate]]` - ?典蔣????嚗?? (script.json) ?脰?璅∠?瘨?撘?冽炎?乓?
---

## 5 ???雁摨?
| 蝬剖漲 | 甈? | 靘? | ??璇辣 |
|------|------|------|---------|
| script_coverage | 25% | script.json + edit_log | 瘥?script segment ?賣?撠?敶梁? |
| duration_fit | 25% | tts_timing + edit_log | 瘥挾敶梁? vs TTS 撌?< 300ms |
| subtitle_accuracy | 20% | script.json + srt | 摮???????90% |
| audio_levels | 15% | ffmpeg volumedetect | mean -25~-12dB, max ??-6dB |
| technical_quality | 15% | ffprobe | 1920x1080 @ 30fps + ??audio/video stream |

### ???砍?
```
total_score = sum(dimension_score ? weight)
pass = total_score >= threshold (?身 80)
```

### 蝚?6 蝬哨?content_alignment嚗LM ?批捆撠?嚗 content_qa.py 瘜典嚗?
?銵?5 蝬剖撽撘?銝???銝???Ｗ?銝?憿content_qa.py` ??VLM嚗wen3-vl:4b嚗??挾撠??葬????瘜典 qa_report ? content_alignment 蝬剖漲嚗?閮剜???0.30嚗擗?5 蝬剔?瘥葬?橘???
**???嚗?霅?敺銝剜?嚗?瘥? `visual_desc`嚗?Ｘ?餈堆?嚗???keyword???舀??賬?*
- 4b 撠??prompt 璅⊥鋆∪?銝剜? keyword??瑕?撌殷???撠????no嚗???*銝剜??**????- 瘥?璅???`visual_desc`嚗??恍鈭祕嚗?銝???`text` ?嚗?摮貉?瘞??憭芾?/憭芣芋蝟???- ???胯撐?銝??挾?恍?膩?????????典???撠? primary/related ?????
**D1 ?湔?挾 gate**嚗遙銝畾?content score < 60 ?單擃?fail嚗??像????嚗孛?潸府畾?repick嚗?fix_target = `curator`嚗?蝺券???????
---

## fix_target 頝舐

瘥雁摨西銝??潘?< 80嚗???閮?靽桀??Skill嚗?
| 蝬剖漲憭望? | fix_target | 閰?Skill 閬?隞暻?|
|---------|-----------|------------------|
| script_coverage | editor | ?芾摩撣怎撩畾蛛?鋆?assemble 瞍???segment |
| duration_fit | editor | ?芾摩撣急??瑕?銝?嚗??啣閰脫挾 |
| subtitle_accuracy | subtitle | 摮?撣急?獢???嚗? srt |
| audio_levels | audio | ?單撣恍??/??嚗? mix-audio |
| technical_quality | editor | 閫??摨行? stream 蝻綽???assemble + merge-final |

銝惜 orchestrator 霈 `qa_report.json.issues[].fix_target` ?喳瘙箏?閬?頝??Skill??
---

## qa_report.json 蝭?

```json
{
  "video": "/workspace/final.mp4",
  "timestamp": "2026-05-24T23:03:20",
  "score": 98.5,
  "pass": true,
  "threshold": 80,
  "dimensions": {
    "script_coverage":   { "score": 100, "weight": 0.25, "note": "all segments present", "fix_target": null },
    "duration_fit":      { "score": 100, "weight": 0.25, "note": "4/4 segments within 300ms", "fix_target": null, "issues": [] },
    "subtitle_accuracy": { "score": 100, "weight": 0.20, "note": "overlap 320/320 chars (100.0%)", "fix_target": null },
    "audio_levels":      { "score":  90, "weight": 0.15, "note": "max -5.8dB ?亥??", "fix_target": null, "mean_db": -22.3, "max_db": -5.8 },
    "technical_quality": { "score": 100, "weight": 0.15, "note": "streams OK, 1920x1080 30fps", "fix_target": null }
  },
  "issues": []
}
```

銝???
```json
{
  "score": 64,
  "pass": false,
  "issues": [
    { "dimension": "duration_fit", "segment": 2, "score": 50, "fix_target": "editor",
      "detail": "seg2 actual 23.8s vs tts 22.0s (1800ms diff)" }
  ]
}
```

---

## ?雁摨西身閮敦蝭

### 1. script_coverage
- 瘥? `script.json` ??segment ??vs `edit_log.json` ??segment ??- 蝻箔?畾萄停??100/N ??- **fix_target = editor**嚗??箏頛臬葦瘝撓?箄府畾蛛?

### 2. duration_fit
- 撠???segment 蝞?`|edit_log.actual_sec - tts_timing.duration_sec|`
- ?身?曉?300ms嚗楝蝺?A 撠蔣???閬??湛?
- 頞??曉潛?畾菔?◤? `issues`
- **fix_target = editor**嚗頛臬葦瘝皞?

### 3. subtitle_accuracy
- ??SRT ???撟?摮葡韏瑚?
- 頝?`script.json` ???text 銝脰絲靘?撠?- ??Counter 蝞??惜蝝?憭???鈭日?嚗璅?/蝛箇嚗?- 瘥? = `overlap / len(script_clean)`
- < 90% ??fix_target = subtitle

### 4. audio_levels
- 頝?`ffmpeg -af volumedetect` ??mean/max dB
- 閬?嚗???#21 + 銝??broadcast 璅?嚗?
  - max > -3 ????30嚗??喲◢?迎?
  - max > -6 ????10嚗餈??喉?
  - mean < -30 ????30嚗云撠嚗?  - mean > -12 ????20嚗?憭扯嚗?- < 80 ??fix_target = audio

### 5. technical_quality
- 閫??摨血???1920x1080
- 敹???video + audio stream
- framerate 30fps 簣1
- < 80 ??fix_target = editor

---

## 撌脩??撖虫?

### ?芸祕雿?v1 銝?嚗?- **暺??菜葫**嚗?暺?Ｚ???蝘?府???嚗??砍祕雿???- **?唾??琿??菜葫**嚗oncat ?亦葦???喉???#29嚗??芸祕雿?皜?- **憭挾 BGM ?喲??挾瑼Ｘ**嚗???#21嚗??單挾 vs 蝝?Ｘ挾閰脖???BGM ?喲?嚗撖虫??芰??湧?
- **摮??????*嚗云?哨?< 0.5s嚗?憭芷嚗? 6s嚗府????芸祕雿?
??蝑撖阡??箏?憿?鋆?
### threshold ?身 80 ???- 5 ?雁摨佗?4 ? 100?? ? 80 ???? 96
- 5 ?雁摨佗?3 ? 100?? ? 80 ???? 92
- 5 ?雁摨佗?2 ? 100?? ? 80 ???? 88
- ??80 = pipeline ?箔?撖西釭??雿?撘瑁??threshold 閮剝撥餈思耨

---

## ?隞?Skill ????
### 銝虜嚗ERIFY 霈隞暻潘?
- `蝺典? Skill` ??`script.json`
- `?單撣?Skill` ??`tts_timing.json`
- `摮?撣?Skill` ??`subtitles.srt`
- `?芾摩撣?Skill` ??`rough_cut_edit_log.json` + `final.mp4`

### 銝虜嚗狐??VERIFY 蝯?嚗?- **??璅∪?**嚗?亦? qa_report嚗撌望捱摰?銝???
- **orchestrator 璅∪?**嚗? `issues[].fix_target` ?芸?閫貊??

---

## 撖行葫蝯?嚗?026-05-24嚗?
撠?`v3_skill_final.mp4` 頝?verify嚗?
| 蝬剖漲 | ? | ?酉 |
|------|------|------|
| script_coverage | 100 | 4/4 segments |
| duration_fit | 100 | ?券 < 300ms |
| subtitle_accuracy | 100 | 320/320 摮? |
| audio_levels | 90 | max -5.8dB嚗?憟質萱?唳餈??喲?潘?|
| technical_quality | 100 | 1920x1080 30fps |
| **??蝮賢?** | **98.5** | ??pass |

audio_levels 瘝皛踹???鈭祕??蝝啁?嚗洵銝??SKILL ?刻???停??-5.8dB ?楠嚗靘?BGM ?喲???隤踹捆???迤??VERIFY 閰脣?????*瘝??郎?????湔暺?**??
---

## 撠???vault ?辣
- `projects/video-agent-pipeline/roadmap.md` Phase 4
- `projects/video-agent-pipeline/skill-interface-contracts.md` ??qa_report.json ?澆?
- `projects/video-agent-pipeline/ffmpeg-pitfalls-reference.md` ??#21嚗??/ #29嚗閮暺?
