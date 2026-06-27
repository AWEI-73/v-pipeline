export const stageLabelsZh = {
  Intent: "影片需求",
  "Material Ingest": "素材匯入",
  "Material Map": "素材地圖",
  "Coverage Delta": "覆蓋差異",
  Structure: "結構規劃",
  Contract: "段落契約",
  Timeline: "時間軸",
  "Review Gates": "審核關卡",
  Verify: "驗證",
};

export const valueLabelsZh = {
  training_recap: "養成班 / 訓練回顧",
  children_story: "兒童故事",
  graduation_recap: "結訓 / 畢業回顧",
  existing_material_available: "已有素材",
  no_existing_visual_material: "沒有現成視覺素材",
  brief_available: "已有 brief / 文字說明",
  story_outline_available: "已有故事大綱",
  brownfield_existing_material: "棕地：已有素材，需要整理與剪輯",
  greenfield_story_first: "綠地：先做故事，再生成或收集素材",
  material_first: "素材優先",
  story_first: "故事優先",
  existing_material_first: "既有素材優先",
  story_first_generated_material: "故事優先，必要時生成素材",
  material_delta_then_collect_or_generate_if_needed: "先看素材缺口，再補拍 / 收集 / 生成",
  generated_material_fallback: "生成素材 fallback",
  material_map_lifecycle: "素材地圖生命週期",
  story_blueprint_then_material_generation_fallback: "故事藍圖後接素材生成 fallback",
};

export const statusLabelsZh = {
  accepted: "已接受",
  blocked: "已阻擋",
  candidate: "候選",
  completed: "已完成",
  declared: "已宣告",
  fail: "失敗",
  missing: "缺少",
  pass: "通過",
  pending: "等待中",
  present: "已存在",
  ready: "可繼續",
  rejected: "已排除",
  review_required: "需要審核",
  running: "執行中",
  skipped: "已略過",
  unknown: "未知",
};

export const workbenchLabelsZh = {
  timelineDraft: "時間軸草稿",
  subtitleDraft: "字幕草稿",
  audioCueDraft: "音訊提示草稿",
  effectDraft: "特效意圖草稿",
  handoff: "Workbench 交接包",
  reviewReport: "Workbench 審核報告",
};

Object.assign(workbenchLabelsZh, {
  timelineDraft: "時間軸草稿",
  subtitleDraft: "字幕草稿",
  audioCueDraft: "音訊提示草稿",
  effectDraft: "特效意圖草稿",
  handoff: "Workbench 交接包",
  reviewReport: "Workbench 審查報告",
});

export function zhValue(value) {
  if (value === undefined || value === null || value === "") return "-";
  return valueLabelsZh[value] || statusLabelsZh[value] || String(value).replaceAll("_", " ");
}

export function zhStatus(status) {
  if (status === undefined || status === null || status === "") return "-";
  return statusLabelsZh[status] || String(status).replaceAll("_", " ");
}
