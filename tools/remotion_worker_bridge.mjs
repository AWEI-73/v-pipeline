#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const PROTECTED_OUTPUTS = new Set([
  "final.mp4",
  "timeline.json",
  "timeline_build.json",
  "segment_contract.json",
  "project_material_map.json",
]);

const usage = () => `Usage:
  node tools/remotion_worker_bridge.mjs \\
    --job-json JOB.json \\
    --preview-file preview.mp4 \\
    --rendered-asset overlay.mov \\
    --project-root remotion_project \\
    [--remotion-bin path/to/remotion] \\
    [--write-entry-only]
`;

function parseArgs(argv) {
  const out = {};
  for (let i = 0; i < argv.length; i += 1) {
    const key = argv[i];
    if (key === "--write-entry-only") {
      out.writeEntryOnly = true;
      continue;
    }
    if (!key.startsWith("--")) {
      throw new Error(`unexpected positional argument: ${key}`);
    }
    const value = argv[i + 1];
    if (value === undefined || value.startsWith("--")) {
      throw new Error(`missing value for ${key}`);
    }
    out[key.slice(2).replace(/-([a-z])/g, (_, c) => c.toUpperCase())] = value;
    i += 1;
  }
  return out;
}

function requireNonEmptyString(value, field) {
  if (typeof value !== "string" || value.trim() === "") {
    throw new Error(`${field} must be a non-empty string`);
  }
  return value.trim();
}

function positiveFinite(value, field) {
  if (typeof value !== "number" || !Number.isFinite(value) || value <= 0) {
    throw new Error(`${field} must be a positive finite number`);
  }
  return value;
}

function resolvePath(value, base) {
  const p = path.normalize(requireNonEmptyString(value, "path"));
  return path.isAbsolute(p) ? p : path.join(base, p);
}

function assertNotProtected(file) {
  if (PROTECTED_OUTPUTS.has(path.basename(file))) {
    throw new Error(`refusing to write protected canonical artifact: ${path.basename(file)}`);
  }
}

function loadJob(file) {
  const text = fs.readFileSync(file, "utf8").replace(/^\uFEFF/, "");
  const job = JSON.parse(text);
  if (!job || typeof job !== "object" || Array.isArray(job)) {
    throw new Error("job must be a JSON object");
  }
  requireNonEmptyString(job.job_id, "job_id");
  positiveFinite((job.timing || {}).duration_sec ?? job.duration_sec, "duration_sec");
  return job;
}

function escForTs(value) {
  return JSON.stringify(value, null, 2);
}

function mediaMimeType(file) {
  const ext = path.extname(file).toLowerCase();
  if (ext === ".jpg" || ext === ".jpeg") return "image/jpeg";
  if (ext === ".png") return "image/png";
  if (ext === ".webp") return "image/webp";
  if (ext === ".gif") return "image/gif";
  return null;
}

function normalizeMediaSrc(value, baseDir) {
  const raw = String(value || "");
  if (!raw || raw.startsWith("data:") || raw.startsWith("http://") || raw.startsWith("https://")) {
    return raw;
  }
  let localPath = raw;
  if (raw.startsWith("file://")) {
    try {
      localPath = fileURLToPath(raw);
    } catch {
      return raw;
    }
  }
  const resolvedFromJob = path.isAbsolute(localPath) ? localPath : path.resolve(baseDir, localPath);
  const resolved = fs.existsSync(resolvedFromJob) || path.isAbsolute(localPath)
    ? resolvedFromJob
    : path.resolve(process.cwd(), localPath);
  const mime = mediaMimeType(resolved);
  if (!mime || !fs.existsSync(resolved)) {
    return raw;
  }
  const stat = fs.statSync(resolved);
  if (stat.size > 10 * 1024 * 1024) {
    return raw;
  }
  return `data:${mime};base64,${fs.readFileSync(resolved).toString("base64")}`;
}

function buildEntry(job, jobDir = process.cwd()) {
  const durationSec = positiveFinite((job.timing || {}).duration_sec ?? job.duration_sec, "duration_sec");
  const fps = 30;
  const durationFrames = Math.max(1, Math.ceil(durationSec * fps));
  const props = job.props || {};
  const presentation = props.presentation || {};
  const intent = String(props.intent || job.prompt || "Hermes motion overlay");
  const displayText = String(props.display_text || props.label_text || props.title_text || intent).slice(0, 30);
  const subtitleText = String(props.subtitle_text || "").slice(0, 44);
  const speakerName = String(props.speaker_name || "").slice(0, 20);
  const promptParameters = props.prompt_parameters && typeof props.prompt_parameters === "object"
    ? props.prompt_parameters
    : {};
  const effectBuildSpecForMedia = promptParameters.effect_build_spec && typeof promptParameters.effect_build_spec === "object"
    ? promptParameters.effect_build_spec
    : {};
  const rawCollageMediaRefs = Array.isArray(props.collage_media_refs) && props.collage_media_refs.length > 0
    ? props.collage_media_refs
    : (Array.isArray(effectBuildSpecForMedia.material_refs) ? effectBuildSpecForMedia.material_refs : []);
  const collageMediaRefs = Array.isArray(rawCollageMediaRefs)
    ? rawCollageMediaRefs.slice(0, 6).map((item, index) => ({
        refId: String(item?.ref_id || `media_${index + 1}`),
        src: normalizeMediaSrc(item?.src || item?.path || "", jobDir),
        label: String(item?.label || ""),
        containsTitle: item?.contains_title === true,
        visualRole: String(item?.visual_role || ""),
      })).filter((item) => item.src)
    : [];
  const family = String(job.component_family || "custom_motion_effect");
  const visual = Array.isArray(props.visual_language)
    ? props.visual_language.join(" / ")
    : "";
  const jobLiteral = {
    jobId: job.job_id,
    family,
    label: displayText,
    prompt: String(job.prompt || ""),
    visual,
    durationFrames,
    fps,
    templateId: String(props.template_id || ""),
    showTextInRender: ["title_reveal", "lower_third_motion", "page_turn_transition"].includes(family)
      || ["film_strip_transition_card", "clean_white_quote_card"].includes(String(props.template_id || "")),
    subtitle: subtitleText,
    speakerName,
    collageMediaRefs,
    textPosition: String(presentation.text_position || "bottom_left"),
    textScale: String(presentation.text_scale || "medium"),
    effectStrength: String(presentation.effect_strength || "medium"),
    safeArea: String(presentation.safe_area || "lower_third"),
    theme: String(presentation.theme || "default"),
    accentColor: String(presentation.accent_color || "#ffd65a"),
    textColor: String(presentation.text_color || "#fff8dc"),
    backgroundStyle: String(presentation.background_style || "transparent"),
    variant: String(presentation.variant || ""),
    motionEnergy: String(presentation.motion_energy || ""),
    titleHierarchy: String(presentation.title_hierarchy || ""),
    heroMediaPolicy: String(presentation.hero_media_policy || ""),
    thumbnailDensity: String(presentation.thumbnail_density || ""),
    promptParameters,
  };

  return `import React from "react";
import {
  AbsoluteFill,
  Composition,
  Easing,
  interpolate,
  registerRoot,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

const JOB = ${escForTs(jobLiteral)};

const clamp = (value) => Math.max(0, Math.min(1, value));
const effectOpacity = {
  subtle: 0.42,
  low: 0.42,
  medium: 0.72,
  high: 0.92,
  emphasis: 0.92,
}[JOB.effectStrength] ?? 0.72;
const textFontSize = {
  small: 24,
  medium: 34,
  large: 48,
  hero: 86,
}[JOB.textScale] ?? 34;
const textBoxStyle = {
  bottom_left: { left: 72, bottom: 64, right: "auto", textAlign: "left" },
  bottom_center: { left: 0, right: 0, bottom: 64, textAlign: "center" },
  top_left: { left: 72, top: 64, right: "auto", textAlign: "left" },
}[JOB.textPosition] ?? { left: 72, bottom: 64, right: "auto", textAlign: "left" };
const isTraining67 = JOB.theme === "training_recap_67";
const isModuleLabelWhiteBlue = JOB.backgroundStyle === "white_blue_label" || JOB.templateId === "module_label_white_blue";
const isBlueWhiteLabel = isModuleLabelWhiteBlue;
const isBlackCollage = JOB.backgroundStyle === "black_collage" || JOB.templateId === "training_opening_title";
const isYellowSubtitleBar = JOB.backgroundStyle === "yellow_subtitle_bar" || JOB.templateId === "speaker_subtitle_yellow_bar";
const isFilmStripCard = JOB.backgroundStyle === "film_strip" || JOB.templateId === "film_strip_transition_card";
const isCleanWhiteQuote = JOB.backgroundStyle === "clean_white_quote" || JOB.templateId === "clean_white_quote_card";
const isProfileMemoryCard = JOB.backgroundStyle === "clean_profile_card" || JOB.templateId === "profile_memory_card";
const isMemoryPhotoWall = JOB.backgroundStyle === "memory_photo_wall" || JOB.templateId === "memory_photo_wall";
const isSoftLightTransition = JOB.templateId === "soft_light_transition";
const isHighlightWarmGlow = JOB.templateId === "highlight_warm_glow";
const isBlurredSideFill = JOB.backgroundStyle === "blurred_side_fill" || JOB.templateId === "blurred_side_fill";
const isCinematicOpening = isBlackCollage && JOB.variant === "cinematic_collage_reveal";
const effectBuildSpec = JOB.promptParameters?.effect_build_spec || JOB.promptParameters?.effectBuildSpec || {};
const visualTechnique = JOB.promptParameters?.visual_technique_plan || JOB.promptParameters?.visualTechniquePlan || {};
const visualTechniqueControls = visualTechnique?.controls || {};
const visualTechniqueMaterialUse = visualTechnique?.material_use || visualTechnique?.materialUse || {};
const visualTechniqueFamily = String(visualTechnique?.style_family || visualTechnique?.styleFamily || "");
const isJapaneseSakuraTechnique = ["japanese_sakura", "sakura_poetic"].includes(visualTechniqueFamily);
const isWarmLegacyFireTechnique = visualTechniqueFamily === "warm_legacy_fire";
const sakuraPetalCount = Math.min(180, Math.max(12, Number(visualTechniqueControls.petal_count || visualTechniqueControls.petalCount || 80)));
const sakuraWindStrength = Number(visualTechniqueControls.wind_strength ?? visualTechniqueControls.windStrength ?? 0.25);
const sakuraFallSpeed = Number(visualTechniqueControls.fall_speed ?? visualTechniqueControls.fallSpeed ?? 0.25);
const sakuraDepthLayers = Math.max(1, Math.min(6, Number(visualTechniqueControls.depth_layers || visualTechniqueControls.depthLayers || 3)));
const sakuraPetals = Array.from({ length: sakuraPetalCount }, (_, index) => {
  const layer = (index % sakuraDepthLayers) + 1;
  const seed = (index * 37) % 997;
  return {
    id: index,
    x: (seed * 1.91) % 1920,
    y: -160 - ((seed * 2.17) % 1080),
    size: 9 + (seed % 16) + layer * 2,
    layer,
    delay: (seed % 80) / 80,
    opacity: 0.26 + layer * 0.12,
    rotate: seed % 360,
  };
});
const warmLegacyBackgroundSource = String(visualTechniqueMaterialUse.background_source || visualTechniqueMaterialUse.backgroundSource || "group_photo");
const warmLegacyBackground = JOB.collageMediaRefs.find((media) => {
  const role = String(media.visualRole || "");
  return role === warmLegacyBackgroundSource || media.refId === warmLegacyBackgroundSource || role.includes("group");
}) || JOB.collageMediaRefs[0];
const photoDimStrength = {
  low: 0.22,
  medium: 0.42,
  high: 0.58,
}[String(visualTechniqueControls.photo_dim_strength || visualTechniqueControls.photoDimStrength || "medium")] ?? 0.42;
const subtitleReadability = String(visualTechniqueControls.subtitle_readability || visualTechniqueControls.subtitleReadability || "medium");
const warmLegacyEmberCount = {
  none: 0,
  low: 28,
  medium: 52,
  high: 84,
}[String(visualTechniqueControls.ember_density || visualTechniqueControls.emberDensity || "low")] ?? 28;
const warmLegacyEmbers = Array.from({ length: warmLegacyEmberCount }, (_, index) => {
  const seed = (index * 53 + 17) % 991;
  return {
    id: index,
    x: (seed * 2.13) % 1920,
    y: 1110 + ((seed * 1.37) % 160),
    size: 3 + (seed % 8),
    delay: (seed % 120) / 120,
    drift: ((seed % 41) - 20) * 0.9,
    opacity: 0.28 + (seed % 40) / 100,
  };
});
const isStoryToMvBuildSpec = String(effectBuildSpec.component || "") === "StoryToMVTransition";
const isStoryToMvFilmTransition = (isFilmStripCard && JOB.variant === "story_to_mv_film_transition") || isStoryToMvBuildSpec;
const isStoryToMvTransition = isStoryToMvFilmTransition;
const storyToMvPhaseLabels = Array.isArray(effectBuildSpec.phase_labels)
  ? effectBuildSpec.phase_labels
  : (Array.isArray(effectBuildSpec.phaseLabels) ? effectBuildSpec.phaseLabels : ["STORY", "MONTAGE"]);
const pacingShift = String(effectBuildSpec.pacing_shift || effectBuildSpec.pacingShift || "medium");
const impactMomentFrame = Number.isFinite(Number(effectBuildSpec.impact_moment_sec ?? effectBuildSpec.impactMomentSec))
  ? Math.max(0, Math.min(JOB.durationFrames - 1, Math.round(Number(effectBuildSpec.impact_moment_sec ?? effectBuildSpec.impactMomentSec) * JOB.fps)))
  : Math.max(1, Math.round(JOB.durationFrames * 0.5));
const thumbnailAccelerationStrength = {
  none: 0,
  low: 0.72,
  medium: 1,
  high: 1.28,
}[String(effectBuildSpec.thumbnail_acceleration || effectBuildSpec.thumbnailAcceleration || "medium")] ?? 1;
const promptMaterialStrategy = JOB.promptParameters?.material_strategy || JOB.promptParameters?.materialStrategy || {};
const promptHeroSource = String(promptMaterialStrategy.hero_source || promptMaterialStrategy.heroSource || "");
const promptAvoidHeroRoles = Array.isArray(promptMaterialStrategy.avoid_hero_roles)
  ? promptMaterialStrategy.avoid_hero_roles
  : (Array.isArray(promptMaterialStrategy.avoidHeroRoles) ? promptMaterialStrategy.avoidHeroRoles : []);
const buildSpecMotionGrammar = Array.isArray(effectBuildSpec.motion_grammar)
  ? effectBuildSpec.motion_grammar
  : (Array.isArray(effectBuildSpec.motionGrammar) ? effectBuildSpec.motionGrammar : []);
const promptMotionGrammar = buildSpecMotionGrammar.length > 0
  ? buildSpecMotionGrammar
  : Array.isArray(JOB.promptParameters?.motion_grammar)
  ? JOB.promptParameters.motion_grammar
  : (Array.isArray(JOB.promptParameters?.motionGrammar) ? JOB.promptParameters.motionGrammar : []);
const hasPromptMotionGrammar = promptMotionGrammar.length > 0;
const usesMotionGrammar = (token) => !hasPromptMotionGrammar || promptMotionGrammar.includes(token);
const enableFilmRail = usesMotionGrammar("film_rail");
const enableThumbnailAcceleration = usesMotionGrammar("thumbnail_acceleration");
const enableFlashWipe = usesMotionGrammar("flash_wipe");
const enableHardCutBars = usesMotionGrammar("hard_cut_bars");
const enableMidpointImpact = enableFlashWipe || enableHardCutBars || usesMotionGrammar("midpoint_impact");
const enableCollageDepthReveal = usesMotionGrammar("collage_depth_reveal");
const enableGoldTitleSweep = usesMotionGrammar("gold_title_sweep");
const enableTitlePunch = usesMotionGrammar("title_punch");
const transitionStrengthScale = {
  soft: 0.72,
  medium: 1,
  impact: 1.32,
}[String(effectBuildSpec.transition_strength || effectBuildSpec.transitionStrength || JOB.promptParameters?.transition_strength || JOB.promptParameters?.transitionStrength || "medium")] ?? 1;
const shouldAvoidTitleHero = JOB.heroMediaPolicy === "avoid_title_bearing" || promptAvoidHeroRoles.includes("title_card");
const orderedCollageMediaRefs = shouldAvoidTitleHero || promptHeroSource === "reviewed_people_group"
  ? [...JOB.collageMediaRefs].sort((a, b) => {
      const aAvoid = a.containsTitle || promptAvoidHeroRoles.includes(a.visualRole) || a.visualRole === "title_card";
      const bAvoid = b.containsTitle || promptAvoidHeroRoles.includes(b.visualRole) || b.visualRole === "title_card";
      const aPreferred = promptHeroSource === "reviewed_people_group" && a.visualRole === "people_group";
      const bPreferred = promptHeroSource === "reviewed_people_group" && b.visualRole === "people_group";
      return Number(bPreferred) - Number(aPreferred) || Number(aAvoid) - Number(bAvoid);
    })
  : JOB.collageMediaRefs;
const motionScale = {
  low: 0.72,
  subtle: 0.72,
  medium: 1,
  high: 1.24,
  emphasis: 1.24,
}[JOB.motionEnergy || JOB.effectStrength] ?? 1;
const collageSlots = [
  { left: 90, top: 80, width: 350, height: 205, rotate: -2, delay: 0.0 },
  { left: 500, top: 52, width: 300, height: 175, rotate: 1.5, delay: 0.12 },
  { left: 1460, top: 105, width: 330, height: 190, rotate: 2, delay: 0.18 },
  { left: 150, top: 385, width: 280, height: 165, rotate: 2.5, delay: 0.26 },
  { left: 1385, top: 440, width: 360, height: 210, rotate: -1.5, delay: 0.32 },
];
const commercialCollageSlots = [
  { left: 850, top: 72, width: 680, height: 394, rotate: 0.7, delay: 0.0, heroCollageSlot: true },
  { left: 1218, top: 502, width: 500, height: 290, rotate: -2.2, delay: 0.13 },
  { left: 610, top: 392, width: 430, height: 250, rotate: -1.1, delay: 0.23 },
  { left: 1470, top: 118, width: 340, height: 198, rotate: 3.1, delay: 0.31 },
  { left: 920, top: 704, width: 390, height: 226, rotate: 1.7, delay: 0.36 },
];
const commercialFilmRailSlots = [
  { left: 175, top: 218, width: 250, height: 142, rotate: -3, delay: 0.04 },
  { left: 456, top: 190, width: 270, height: 152, rotate: 1.5, delay: 0.10 },
  { left: 1170, top: 704, width: 278, height: 156, rotate: -1.5, delay: 0.18 },
  { left: 1470, top: 684, width: 252, height: 142, rotate: 3, delay: 0.24 },
];
const memoryWallSlots = [
  { left: 176, top: 138, width: 560, height: 330, rotate: -2.4 },
  { left: 1038, top: 116, width: 520, height: 306, rotate: 1.8 },
  { left: 628, top: 506, width: 620, height: 360, rotate: 0.8 },
  { left: 1322, top: 554, width: 420, height: 248, rotate: -2.0 },
  { left: 250, top: 610, width: 390, height: 230, rotate: 1.6 },
];
const memoryPacing = String(effectBuildSpec.pacing || "slow");
const memoryDensity = String(effectBuildSpec.density || "low");
const memoryRevealMode = String(effectBuildSpec.reveal_mode || effectBuildSpec.revealMode || "one_by_one");
const memoryRevealIntervalFrames = Math.max(
  12,
  Math.round(Number(effectBuildSpec.reveal_interval_sec ?? effectBuildSpec.revealIntervalSec ?? (memoryPacing === "slow" ? 1.2 : 0.65)) * JOB.fps),
);
const holdAfterFullWallFrames = Math.max(
  0,
  Math.round(Number(effectBuildSpec.hold_after_full_wall_sec ?? effectBuildSpec.holdAfterFullWallSec ?? (memoryPacing === "slow" ? 2.0 : 0.8)) * JOB.fps),
);
const memoryWallMaxItems = Math.min(
  JOB.collageMediaRefs.length,
  memoryDensity === "low" ? 5 : (memoryDensity === "medium" ? 6 : 8),
);
const commercialTitleScale = isCinematicOpening ? 122 : textFontSize;
const suppressStoryToMvBaseText = isStoryToMvFilmTransition;
const filmStripHoles = Array.from({ length: 18 }, (_, index) => index);
const labelBackground = isBlueWhiteLabel
  ? "linear-gradient(90deg, rgba(255,255,255,.96) 0%, rgba(255,255,255,.96) 76%, rgba(24,82,178,.96) 76%, rgba(24,82,178,.96) 100%)"
  : isYellowSubtitleBar
    ? "linear-gradient(90deg, rgba(255,225,0,.96), rgba(255,190,40,.96))"
    : isCleanWhiteQuote
      ? "rgba(255,255,255,.96)"
      : isFilmStripCard
        ? "rgba(0,0,0,.52)"
    : isMemoryPhotoWall
      ? "linear-gradient(90deg, rgba(0,0,0,.62), rgba(0,0,0,.16))"
    : isProfileMemoryCard
      ? "linear-gradient(90deg, rgba(0,0,0,.72), rgba(0,0,0,.18))"
      : (JOB.family === "lower_third_motion" ? "rgba(0,0,0,.32)" : "transparent");
const labelColor = isCleanWhiteQuote
  ? JOB.textColor
  : isModuleLabelWhiteBlue
    ? JOB.accentColor
  : (isTraining67 && JOB.family === "title_reveal" ? JOB.accentColor : JOB.textColor);
const labelShadow = isCleanWhiteQuote
  ? "none"
  : (isTraining67 ? "0 4px 18px rgba(0,0,0,.62)" : "0 3px 18px rgba(0,0,0,.45)");

const HermesEffectOverlay = ({ preview = false }) => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();
  const enter = interpolate(frame, [0, Math.min(18, JOB.durationFrames / 2)], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const exit = interpolate(frame, [Math.max(0, JOB.durationFrames - 16), JOB.durationFrames - 1], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.in(Easing.cubic),
  });
  const sweep = interpolate(frame, [0, JOB.durationFrames - 1], [-0.35, 1.35], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const slowParallax = interpolate(frame, [0, JOB.durationFrames - 1], [-18, 18], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.cubic),
  });
  const filmDrift = interpolate(frame, [0, JOB.durationFrames - 1], [-42, 42], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const flash = interpolate(
    frame,
    [Math.max(0, JOB.durationFrames * 0.35), Math.max(1, JOB.durationFrames * 0.43), Math.max(2, JOB.durationFrames * 0.52)],
    [0, 0.72, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) },
  );
  const transitionTimingRamp = interpolate(
    frame,
    [0, Math.max(1, JOB.durationFrames * 0.22), Math.max(2, JOB.durationFrames * 0.72), JOB.durationFrames - 1],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.inOut(Easing.cubic) },
  );
  const titleImpactPulse = interpolate(
    frame,
    [Math.max(0, JOB.durationFrames * 0.16), Math.max(1, JOB.durationFrames * 0.30), Math.max(2, JOB.durationFrames * 0.46)],
    [0.92, 1.08, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.back(1.4)) },
  );
  const midpointImpactFrame = interpolate(
    frame,
    [
      Math.max(0, impactMomentFrame - Math.round(JOB.durationFrames * 0.04)),
      Math.max(1, impactMomentFrame),
      Math.max(2, impactMomentFrame + Math.round(JOB.durationFrames * 0.06)),
    ],
    [0, 0.88, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) },
  );
  const impactBarsScale = interpolate(
    frame,
    [
      Math.max(0, impactMomentFrame - Math.round(JOB.durationFrames * 0.06)),
      Math.max(1, impactMomentFrame),
      Math.max(2, impactMomentFrame + Math.round(JOB.durationFrames * 0.12)),
    ],
    [0.18, 1, 0.28],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.back(1.1)) },
  );
  const thumbnailAccelerationCurve = interpolate(
    frame,
    [0, Math.max(1, JOB.durationFrames * 0.36), JOB.durationFrames - 1],
    [0, 0.28 * thumbnailAccelerationStrength, 1 * thumbnailAccelerationStrength],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.in(Easing.cubic) },
  );
  const opacity = clamp(enter * exit);
  const slowPushInScale = isMemoryPhotoWall && effectBuildSpec.camera_motion === "slow_push_in"
    ? interpolate(frame, [0, JOB.durationFrames - 1], [1, 1.045], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
        easing: Easing.bezier(0.45, 0, 0.55, 1),
      })
    : 1;
  return (
    <AbsoluteFill style={{ backgroundColor: preview ? "#101018" : "transparent", overflow: "hidden" }}>
      {isBlackCollage ? (
        <AbsoluteFill
          style={{
            background: "radial-gradient(circle at 72% 30%, rgba(40,40,48,.72), rgba(5,5,7,1) 58%, rgba(0,0,0,1) 100%)",
            opacity,
          }}
        />
      ) : null}
      {isWarmLegacyFireTechnique ? (
        <AbsoluteFill className="warmLegacyFireClosing" style={{ opacity, overflow: "hidden" }}>
          {warmLegacyBackground?.src ? (
            <img
              className="warmLegacyPhotoBackground"
              src={warmLegacyBackground.src}
              style={{
                position: "absolute",
                inset: -28,
                width: "calc(100% + 56px)",
                height: "calc(100% + 56px)",
                objectFit: "cover",
                transform: "scale(" + (1.02 + enter * 0.025) + ")",
                filter: "saturate(.82) contrast(.92) brightness(" + (0.78 - photoDimStrength * 0.38) + ")",
                opacity: 0.72,
              }}
            />
          ) : null}
          <AbsoluteFill
            className="warmLegacyPhotoDimPlate"
            style={{
              background:
                "linear-gradient(180deg, rgba(0,0,0,.42), rgba(0,0,0," + (0.38 + photoDimStrength) + ") 62%, rgba(0,0,0,.86)), radial-gradient(circle at 50% 70%, rgba(255,172,62,.18), rgba(0,0,0,0) 48%)",
            }}
          />
          <AbsoluteFill
            className="warmLegacyAfterglow"
            style={{
              background:
                "radial-gradient(circle at 50% 72%, rgba(255,176,64,.26), rgba(255,176,64,.08) 26%, rgba(0,0,0,0) 58%), radial-gradient(circle at 50% 48%, rgba(255,221,148,.10), rgba(0,0,0,0) 34%)",
              mixBlendMode: "screen",
              opacity: 0.84,
            }}
          />
          <AbsoluteFill className="warmLegacyEmbers">
            {warmLegacyEmbers.map((ember) => {
              const progress = ((frame + ember.delay * JOB.durationFrames) % JOB.durationFrames) / Math.max(1, JOB.durationFrames);
              const rise = progress * 820;
              const x = ember.x + Math.sin(progress * Math.PI * 2 + ember.id) * 28 + ember.drift * progress;
              const y = ember.y - rise;
              return (
                <div
                  key={"warm-legacy-ember-" + ember.id}
                  className="warmLegacyEmber"
                  style={{
                    position: "absolute",
                    left: x,
                    top: y,
                    width: ember.size,
                    height: ember.size,
                    borderRadius: 999,
                    background: "rgba(255,190,72,.92)",
                    boxShadow: "0 0 " + (8 + ember.size * 2) + "px rgba(255,154,45,.52)",
                    opacity: Math.max(0, ember.opacity * (1 - progress * 0.82)),
                  }}
                />
              );
            })}
          </AbsoluteFill>
        </AbsoluteFill>
      ) : null}
      {isCinematicOpening && enableCollageDepthReveal ? (
        <AbsoluteFill className="commercialOpeningPlate" style={{ opacity }}>
          <div
            className="cinematicDepthVignette"
            style={{
              position: "absolute",
              inset: 0,
              background:
                "radial-gradient(circle at 50% 44%, rgba(255,255,255,.04), rgba(0,0,0,0) 32%), radial-gradient(circle at 50% 50%, rgba(0,0,0,0) 44%, rgba(0,0,0,.72) 100%)",
              mixBlendMode: "multiply",
            }}
          />
          <div
            className="scanlineTexture"
            style={{
              position: "absolute",
              inset: 0,
              background:
                "repeating-linear-gradient(0deg, rgba(255,255,255,.035) 0 1px, rgba(0,0,0,0) 1px 5px), repeating-linear-gradient(90deg, rgba(255,225,0,.035) 0 1px, rgba(0,0,0,0) 1px 80px)",
              opacity: 0.42,
              mixBlendMode: "screen",
            }}
          />
        </AbsoluteFill>
      ) : null}
      {isJapaneseSakuraTechnique ? (
        <AbsoluteFill className="visualTechniqueSakuraLayer" style={{ opacity: opacity * 0.92, pointerEvents: "none" }}>
          <AbsoluteFill
            className="sakuraSoftBloom"
            style={{
              background:
                "radial-gradient(circle at 72% 24%, rgba(255,210,226,.18), rgba(255,210,226,0) 42%), radial-gradient(circle at 20% 70%, rgba(255,245,250,.12), rgba(255,245,250,0) 36%)",
              mixBlendMode: "screen",
            }}
          />
          {sakuraPetals.map((petal) => {
            const cycleFrames = Math.max(1, JOB.durationFrames);
            const progress = ((frame + petal.delay * cycleFrames) % cycleFrames) / cycleFrames;
            const depth = petal.layer / sakuraDepthLayers;
            const fallDistance = 1220 + depth * 220;
            const drift = Math.sin(progress * Math.PI * 2 + petal.id) * 70 * sakuraWindStrength * (0.55 + depth);
            const x = (petal.x + drift + progress * 180 * sakuraWindStrength) % 1980 - 30;
            const y = petal.y + progress * fallDistance * (0.72 + sakuraFallSpeed + depth * 0.18);
            const rotate = petal.rotate + progress * 360 * (0.35 + depth);
            return (
              <div
                key={"sakura-petal-" + petal.id}
                className="sakuraPetal"
                style={{
                  position: "absolute",
                  left: x,
                  top: y,
                  width: petal.size,
                  height: petal.size * 0.58,
                  borderRadius: "90% 12% 90% 18%",
                  background:
                    "linear-gradient(135deg, rgba(255,255,255,.92), rgba(255,194,214,.80) 54%, rgba(255,142,181,.56))",
                  boxShadow: "0 0 " + (8 + petal.layer * 2) + "px rgba(255,190,215,.32)",
                  opacity: Math.min(0.92, petal.opacity),
                  transform: "rotate(" + rotate + "deg) translateZ(0)",
                  filter: "blur(" + (sakuraDepthLayers - petal.layer) * 0.25 + "px)",
                }}
              />
            );
          })}
        </AbsoluteFill>
      ) : null}
      {isBlackCollage ? (isCinematicOpening ? commercialCollageSlots : collageSlots).map((slot, index) => {
        const media = orderedCollageMediaRefs[index % Math.max(1, orderedCollageMediaRefs.length)];
        const hasMedia = media && media.src;
        const slotEnter = interpolate(
          frame,
          [Math.round(slot.delay * JOB.durationFrames), Math.round(slot.delay * JOB.durationFrames) + 14],
          [0, 1],
          { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) },
        );
        return (
          <div
            key={"collage-" + index}
            style={{
              position: "absolute",
              left: slot.left + (isCinematicOpening ? slowParallax * motionScale * (slot.heroCollageSlot ? 0.35 : (index % 2 === 0 ? 0.6 : -0.45)) : 0),
              top: slot.top + (isCinematicOpening ? slowParallax * motionScale * (slot.heroCollageSlot ? 0.1 : (index % 2 === 0 ? 0.18 : -0.12)) : 0),
              width: slot.width,
              height: slot.height,
              transform: "rotate(" + slot.rotate + "deg) scale(" + (0.96 + slotEnter * 0.04) + ")",
              border: isCinematicOpening ? (slot.heroCollageSlot ? "2px solid rgba(255,225,0,.66)" : "1px solid rgba(255,255,255,.72)") : "3px solid rgba(255,255,255,.85)",
              background:
                "linear-gradient(135deg, rgba(255,255,255,.18), rgba(80,110,150,.22)), repeating-linear-gradient(45deg, rgba(255,255,255,.08) 0 10px, rgba(255,255,255,.02) 10px 22px)",
              boxShadow: isCinematicOpening
                ? (slot.heroCollageSlot
                  ? "0 34px 90px rgba(0,0,0,.78), 0 0 0 10px rgba(255,225,0,.035), 0 0 52px rgba(255,225,0,.14)"
                  : "0 26px 70px rgba(0,0,0,.72), 0 0 0 8px rgba(255,255,255,.025)")
                : "0 14px 32px rgba(0,0,0,.55)",
              opacity: opacity * slotEnter * 0.96,
              overflow: "hidden",
            }}
            className={isCinematicOpening && enableCollageDepthReveal ? "collageDepthShadow" : undefined}
          >
            {hasMedia ? (
              <img
                src={media.src}
                style={{
                  width: "100%",
                  height: "100%",
                  objectFit: "cover",
                  filter: "saturate(1.08) contrast(1.12) brightness(1.18)",
                }}
              />
            ) : null}
            {hasMedia && media.label ? (
              <div
                style={{
                  position: "absolute",
                  left: 10,
                  bottom: 8,
                  padding: "2px 8px",
                  background: "rgba(0,0,0,.55)",
                  color: "rgba(255,255,255,.86)",
                  fontSize: 14,
                  fontWeight: 700,
                }}
              >
                {media.label}
              </div>
            ) : null}
          </div>
        );
      }) : null}
      {isFilmStripCard ? (
        <AbsoluteFill
          className={isStoryToMvFilmTransition ? "commercialFilmGate" : undefined}
          style={{
            background: isStoryToMvFilmTransition
              ? "radial-gradient(circle at 50% 44%, rgba(255,225,0,.13), rgba(0,0,0,0) 36%), linear-gradient(135deg, rgba(2,3,5,1), rgba(30,32,40,1) 46%, rgba(3,4,7,1))"
              : "linear-gradient(135deg, rgba(9,12,18,1), rgba(30,34,42,1) 48%, rgba(4,5,8,1))",
            opacity,
          }}
        >
          <div
            style={{
              position: "absolute",
              left: 72 + (isStoryToMvFilmTransition ? filmDrift * 0.18 : 0),
              right: 72 - (isStoryToMvFilmTransition ? filmDrift * 0.18 : 0),
              top: 96,
              bottom: 96,
              border: "5px solid rgba(255,255,255,.88)",
              boxShadow: "0 24px 60px rgba(0,0,0,.6), inset 0 0 70px rgba(255,225,0,.12)",
              background:
                "linear-gradient(90deg, rgba(255,255,255,.08), rgba(255,255,255,.02)), repeating-linear-gradient(90deg, rgba(255,255,255,.06) 0 24px, rgba(255,255,255,.02) 24px 48px)",
              transform: "translateY(" + ((1 - enter) * 20) + "px)",
            }}
          />
          {isStoryToMvFilmTransition && enableThumbnailAcceleration ? (
            <div
              className="thumbnailMotionBlurTrail"
              style={{
                position: "absolute",
                inset: 0,
                opacity: opacity * thumbnailAccelerationCurve * 0.34,
                filter: "blur(14px)",
                mixBlendMode: "screen",
                pointerEvents: "none",
              }}
            >
              {commercialFilmRailSlots.map((slot, index) => (
                <div
                  key={"thumb-trail-" + index}
                  style={{
                    position: "absolute",
                    left: slot.left - 120 + thumbnailAccelerationCurve * motionScale * transitionStrengthScale * 180,
                    top: slot.top + 14,
                    width: slot.width + 90,
                    height: slot.height - 18,
                    transform: "rotate(" + slot.rotate + "deg) skewX(-12deg)",
                    background:
                      "linear-gradient(90deg, rgba(255,225,0,0), rgba(255,255,255,.24), rgba(255,225,0,.18), rgba(255,225,0,0))",
                    boxShadow: "0 0 28px rgba(255,225,0,.22)",
                  }}
                />
              ))}
            </div>
          ) : null}
          {isStoryToMvFilmTransition && enableFilmRail ? (
            <div
              className="filmThumbnailRail"
              style={{
                position: "absolute",
                inset: 0,
                transform: "translateX(" + ((filmDrift * motionScale * 0.2) + (thumbnailAccelerationCurve * motionScale * transitionStrengthScale * 92)) + "px)",
                opacity: opacity * 0.96,
              }}
            >
              {commercialFilmRailSlots.map((slot, index) => {
                const media = orderedCollageMediaRefs[index % Math.max(1, orderedCollageMediaRefs.length)];
                const thumbEnter = interpolate(
                  frame,
                  [Math.round(slot.delay * JOB.durationFrames), Math.round(slot.delay * JOB.durationFrames) + 10],
                  [0, 1],
                  { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) },
                );
                return (
                  <div
                    key={"film-thumb-" + index}
                    style={{
                      position: "absolute",
                      left: slot.left,
                      top: slot.top,
                      width: slot.width,
                      height: slot.height,
                      transform: "rotate(" + slot.rotate + "deg) scale(" + (0.94 + thumbEnter * 0.06 + thumbnailAccelerationCurve * 0.025) + ")",
                      border: "4px solid rgba(255,255,255,.86)",
                      boxShadow: "0 18px 45px rgba(0,0,0,.68)",
                      background: "rgba(255,255,255,.08)",
                      overflow: "hidden",
                      opacity: thumbEnter,
                    }}
                  >
                    {media?.src ? (
                      <img
                        src={media.src}
                        style={{
                          width: "100%",
                          height: "100%",
                          objectFit: "cover",
                          filter: "saturate(1.06) contrast(1.12) brightness(1.04)",
                        }}
                      />
                    ) : null}
                  </div>
                );
              })}
            </div>
          ) : null}
          {isStoryToMvFilmTransition && enableThumbnailAcceleration ? (
            <AbsoluteFill
              className="acceleratingThumbnailRail"
              style={{
                opacity: opacity * thumbnailAccelerationCurve * 0.38 * transitionStrengthScale,
                background:
                  "linear-gradient(90deg, rgba(255,225,0,0), rgba(255,225,0,.18), rgba(255,255,255,.22), rgba(255,225,0,0))",
                transform: "translateX(" + (thumbnailAccelerationCurve * width * 0.42 - width * 0.16) + "px) skewX(-18deg)",
                filter: "blur(22px)",
                mixBlendMode: "screen",
              }}
            />
          ) : null}
          {isStoryToMvFilmTransition ? (
            <div
              className="filmCenterFrame"
              style={{
                position: "absolute",
                left: 610,
                right: 610,
                top: 350,
                height: 214,
                border: "3px solid rgba(255,255,255,.74)",
                boxShadow: "0 18px 60px rgba(0,0,0,.72), inset 0 0 60px rgba(255,225,0,.10)",
                background: "linear-gradient(135deg, rgba(0,0,0,.58), rgba(0,0,0,.26))",
                opacity: opacity * enter,
              }}
            />
          ) : null}
          {isStoryToMvFilmTransition ? (
            <AbsoluteFill className="storyMvSplitBeam" style={{ opacity: opacity * enter }}>
              <div
                style={{
                  position: "absolute",
                  left: -160 + sweep * width * 0.24,
                  top: 150,
                  width: 760,
                  height: 980,
                  transform: "rotate(-17deg)",
                  background: "linear-gradient(90deg, rgba(255,255,255,0), rgba(255,225,0,.18), rgba(255,255,255,0))",
                  filter: "blur(26px)",
                  mixBlendMode: "screen",
                }}
              />
              <div
                style={{
                  position: "absolute",
                  right: -240 + filmDrift * motionScale * 0.2,
                  top: 180,
                  width: 860,
                  height: 860,
                  transform: "rotate(16deg)",
                  background: "linear-gradient(90deg, rgba(255,255,255,0), rgba(120,170,255,.13), rgba(255,255,255,0))",
                  filter: "blur(34px)",
                  mixBlendMode: "screen",
                }}
              />
            </AbsoluteFill>
          ) : null}
          {isStoryToMvFilmTransition ? (
            <div className="transitionPhaseLabels" style={{ opacity: opacity * 0.78 }}>
              <div
                style={{
                  position: "absolute",
                  left: 118,
                  top: 388,
                  color: "rgba(255,255,255,.62)",
                  fontSize: 20,
                  fontWeight: 800,
                  letterSpacing: 4,
                }}
              >
                {storyToMvPhaseLabels[0] || "STORY"}
              </div>
              <div
                style={{
                  position: "absolute",
                  right: 138,
                  top: 622,
                  color: "rgba(255,225,0,.72)",
                  fontSize: 20,
                  fontWeight: 900,
                  letterSpacing: 4,
                }}
              >
                {storyToMvPhaseLabels[1] || "MONTAGE"}
              </div>
            </div>
          ) : null}
          {isStoryToMvFilmTransition ? (
            <div className="largeReadablePhaseLabels" style={{ opacity: opacity * transitionTimingRamp }}>
              <div
                style={{
                  position: "absolute",
                  left: 110,
                  top: 482,
                  padding: "10px 18px",
                  color: "rgba(255,255,255,.82)",
                  fontSize: 34,
                  fontWeight: 900,
                  letterSpacing: 2,
                  borderLeft: "6px solid rgba(255,255,255,.62)",
                  background: "linear-gradient(90deg, rgba(0,0,0,.58), rgba(0,0,0,0))",
                  textShadow: "0 8px 28px rgba(0,0,0,.9)",
                }}
              >
                {storyToMvPhaseLabels[0] || "STORY"}
              </div>
              <div
                style={{
                  position: "absolute",
                  right: 118,
                  top: 526,
                  padding: "10px 20px",
                  color: JOB.accentColor,
                  fontSize: 38,
                  fontWeight: 950,
                  letterSpacing: 2,
                  borderRight: "6px solid rgba(255,225,0,.74)",
                  background: "linear-gradient(270deg, rgba(0,0,0,.58), rgba(0,0,0,0))",
                  textShadow: "0 8px 30px rgba(0,0,0,.9)",
                }}
              >
                {storyToMvPhaseLabels[1] || "MONTAGE"}
              </div>
            </div>
          ) : null}
          {isStoryToMvFilmTransition ? (
            <div className="energyPulseBars" style={{ opacity: opacity * 0.7 }}>
              {[0, 1, 2, 3].map((bar) => (
                <div
                  key={"energy-bar-" + bar}
                  style={{
                    position: "absolute",
                    left: 146 + bar * 70 + filmDrift * motionScale * 0.18,
                    bottom: 138 + bar * 7,
                    width: 44,
                    height: 6,
                    borderRadius: 999,
                    background: bar % 2 === 0 ? JOB.accentColor : "rgba(255,255,255,.72)",
                    boxShadow: "0 0 18px rgba(255,225,0,.35)",
                  }}
                />
              ))}
              {[0, 1, 2, 3].map((bar) => (
                <div
                  key={"energy-bar-r-" + bar}
                  style={{
                    position: "absolute",
                    right: 168 + bar * 68 - filmDrift * motionScale * 0.16,
                    top: 184 + bar * 7,
                    width: 48,
                    height: 6,
                    borderRadius: 999,
                    background: bar % 2 === 0 ? "rgba(255,255,255,.70)" : JOB.accentColor,
                    boxShadow: "0 0 18px rgba(255,225,0,.28)",
                  }}
                />
              ))}
            </div>
          ) : null}
          {["top", "bottom"].map((edge) => (
            <div
              key={"film-holes-" + edge}
              className={isStoryToMvFilmTransition ? "movingSprocketMask" : undefined}
              style={{
                position: "absolute",
                left: 108 + (isStoryToMvFilmTransition ? filmDrift : 0),
                right: 108 - (isStoryToMvFilmTransition ? filmDrift : 0),
                [edge]: 34,
                height: 38,
                display: "flex",
                justifyContent: "space-between",
                opacity: opacity * 0.95,
              }}
            >
              {filmStripHoles.map((hole) => (
                <div
                  key={edge + "-" + hole}
                  style={{
                    width: 38,
                    height: 30,
                    borderRadius: 7,
                    background: "rgba(255,255,255,.9)",
                    boxShadow: "inset 0 2px 6px rgba(0,0,0,.45)",
                  }}
                />
              ))}
            </div>
          ))}
          {isStoryToMvFilmTransition && enableFlashWipe ? (
            <AbsoluteFill
              className="filmFlashWipe"
              style={{
                background: "linear-gradient(90deg, rgba(255,255,255,0), rgba(255,244,190,.92), rgba(255,255,255,0))",
                opacity: flash,
            transform: "translateX(" + (sweep * width - width * 0.5) + "px) skewX(-12deg)",
                filter: "blur(18px)",
                mixBlendMode: "screen",
              }}
            />
          ) : null}
          {isStoryToMvFilmTransition && enableMidpointImpact ? (
            <AbsoluteFill
              className="midpointImpactFrame"
              style={{
                opacity: midpointImpactFrame * transitionStrengthScale,
                background:
                  "radial-gradient(circle at 50% 50%, rgba(255,255,255,.72), rgba(255,235,160,.36) 26%, rgba(255,225,0,.14) 48%, rgba(255,255,255,0) 72%)",
                mixBlendMode: "screen",
              }}
            />
          ) : null}
          {isStoryToMvFilmTransition && enableHardCutBars ? (
            <AbsoluteFill
              className="impactFlashPlate"
              style={{
                opacity: Math.min(0.92, midpointImpactFrame * transitionStrengthScale * 1.14),
                background:
                  "linear-gradient(90deg, rgba(255,255,255,0), rgba(255,255,255,.68) 18%, rgba(255,225,0,.62) 50%, rgba(255,255,255,.72) 82%, rgba(255,255,255,0))",
                mixBlendMode: "screen",
                filter: "blur(8px)",
              }}
            />
          ) : null}
          {isStoryToMvFilmTransition && enableHardCutBars ? (
            <AbsoluteFill className="hardCutImpactBars" style={{ opacity: Math.min(1, midpointImpactFrame * transitionStrengthScale * 1.08) }}>
              <div
                className="commercialImpactShutter"
                style={{
                  position: "absolute",
                  left: -180,
                  right: -180,
                  top: 424,
                  height: 112,
                  background: "linear-gradient(90deg, rgba(0,0,0,0), rgba(255,255,255,.92), rgba(255,225,0,.78), rgba(255,255,255,.92), rgba(0,0,0,0))",
                  transform: "skewX(-12deg) scaleY(" + impactBarsScale + ")",
                  boxShadow: "0 0 56px rgba(255,225,0,.58), 0 0 84px rgba(255,255,255,.34)",
                  mixBlendMode: "screen",
                }}
              />
              <div
                className="commercialImpactShutter"
                style={{
                  position: "absolute",
                  left: -160,
                  right: -160,
                  top: 548,
                  height: 74,
                  background: "linear-gradient(90deg, rgba(0,0,0,0), rgba(255,225,0,.72), rgba(255,255,255,.84), rgba(255,225,0,.62), rgba(0,0,0,0))",
                  transform: "skewX(10deg) scaleY(" + Math.max(0.24, impactBarsScale * 0.82) + ")",
                  boxShadow: "0 0 44px rgba(255,225,0,.44)",
                  mixBlendMode: "screen",
                }}
              />
              <div
                style={{
                  position: "absolute",
                  left: 0,
                  right: 0,
                  top: 340,
                  height: 14,
                  background: "rgba(255,255,255,.92)",
                  boxShadow: "0 0 34px rgba(255,225,0,.62)",
                }}
              />
              <div
                style={{
                  position: "absolute",
                  left: 0,
                  right: 0,
                  top: 722,
                  height: 10,
                  background: JOB.accentColor,
                  boxShadow: "0 0 30px rgba(255,225,0,.58)",
                }}
              />
              <div
                style={{
                  position: "absolute",
                  left: 858,
                  top: 0,
                  bottom: 0,
                  width: 12,
                  background: "rgba(255,255,255,.78)",
                  transform: "skewX(-14deg)",
                  boxShadow: "0 0 40px rgba(255,255,255,.45)",
                }}
              />
            </AbsoluteFill>
          ) : null}
        </AbsoluteFill>
      ) : null}
      {isCleanWhiteQuote ? (
        <AbsoluteFill
          style={{
            background: "linear-gradient(135deg, rgba(255,255,255,1), rgba(245,248,253,1))",
            opacity,
          }}
        >
          <div
            className="quoteAccentLine"
            style={{
              position: "absolute",
              left: 510,
              right: 510,
              bottom: 248,
              height: 5,
              borderRadius: 999,
              background: JOB.accentColor,
              opacity: opacity * 0.9,
            }}
          />
          <div
            style={{
              position: "absolute",
              left: 120,
              top: 96,
              fontSize: 130,
              fontWeight: 900,
              color: "rgba(30,91,184,.11)",
              fontFamily: "Georgia, 'Times New Roman', serif",
            }}
          >
            “
          </div>
        </AbsoluteFill>
      ) : null}
      {isMemoryPhotoWall ? (
        <AbsoluteFill
          className="memoryPhotoWall"
          style={{
            background:
              "radial-gradient(circle at 28% 18%, rgba(255,211,106,.16), rgba(0,0,0,0) 36%), linear-gradient(135deg, rgba(10,12,16,1), rgba(26,28,34,1) 50%, rgba(8,9,12,1))",
            opacity,
          }}
        >
          <AbsoluteFill
            className="memoryWallSlowCamera"
            style={{
              transform: "scale(" + slowPushInScale + ")",
              transformOrigin: "50% 50%",
            }}
          >
            {orderedCollageMediaRefs.slice(0, memoryWallMaxItems).map((media, index) => {
              const slot = memoryWallSlots[index % memoryWallSlots.length];
              const revealStart = memoryRevealMode === "one_by_one" ? index * memoryRevealIntervalFrames : Math.round(index * 0.18 * memoryRevealIntervalFrames);
              const revealEnd = revealStart + Math.round(memoryRevealIntervalFrames * 0.7);
              const cardIn = interpolate(frame, [revealStart, revealEnd], [0, 1], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
                easing: Easing.bezier(0.16, 1, 0.3, 1),
              });
              const photoDrift = interpolate(frame, [revealStart, JOB.durationFrames - 1], [0, index % 2 === 0 ? 16 : -14], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
                easing: Easing.bezier(0.45, 0, 0.55, 1),
              });
              return (
                <div
                  key={"memory-wall-" + media.refId + "-" + index}
                  className="memoryWallCard"
                  style={{
                    position: "absolute",
                    left: slot.left,
                    top: slot.top,
                    width: slot.width,
                    height: slot.height,
                    transform:
                      "translateY(" + ((1 - cardIn) * 36 + photoDrift * 0.18) + "px) rotate(" + slot.rotate + "deg) scale(" + (0.94 + cardIn * 0.06) + ")",
                    opacity: opacity * cardIn,
                    border: "2px solid rgba(255,255,255,.78)",
                    background: "rgba(255,255,255,.10)",
                    boxShadow: "0 26px 74px rgba(0,0,0,.58), 0 0 0 8px rgba(255,255,255,.025)",
                    overflow: "hidden",
                  }}
                >
                  {media.src ? (
                    <img
                      src={media.src}
                      style={{
                        width: "100%",
                        height: "100%",
                        objectFit: "cover",
                        filter: "saturate(1.02) contrast(1.05) brightness(1.08)",
                      }}
                    />
                  ) : null}
                  {effectBuildSpec.caption_mode === "minimal" && media.label ? (
                    <div
                      className="minimalCaption"
                      style={{
                        position: "absolute",
                        left: 14,
                        bottom: 12,
                        padding: "4px 10px",
                        borderRadius: 4,
                        background: "rgba(0,0,0,.46)",
                        color: "rgba(255,255,255,.88)",
                        fontSize: 16,
                        fontWeight: 700,
                        letterSpacing: 0,
                      }}
                    >
                      {media.label}
                    </div>
                  ) : null}
                </div>
              );
            })}
          </AbsoluteFill>
          {effectBuildSpec.accent_light === "soft_warm" ? (
            <AbsoluteFill
              className="memoryWallSoftWarmAccent"
              style={{
                background:
                  "radial-gradient(circle at 42% 26%, rgba(255,211,106,.20), rgba(255,211,106,.05) 34%, rgba(0,0,0,0) 62%)",
                opacity: opacity * 0.76,
                mixBlendMode: "screen",
              }}
            />
          ) : null}
          <div
            className="memoryWallHoldMeter"
            style={{
              position: "absolute",
              left: 74,
              bottom: 54,
              width: Math.min(260, Math.max(90, holdAfterFullWallFrames * 2)),
              height: 4,
              borderRadius: 999,
              background: "linear-gradient(90deg, " + JOB.accentColor + ", rgba(255,255,255,.62), rgba(255,255,255,0))",
              opacity: opacity * 0.74,
            }}
          />
        </AbsoluteFill>
      ) : null}
      {isProfileMemoryCard ? (
        <AbsoluteFill
          style={{
            background:
              "linear-gradient(135deg, rgba(8,10,14,1), rgba(32,38,48,1) 46%, rgba(8,10,14,1)), radial-gradient(circle at 82% 18%, rgba(255,225,0,.24), rgba(0,0,0,0) 48%)",
            opacity,
          }}
        >
          <div
            className="profilePhotoFrame"
            style={{
              position: "absolute",
              right: 124,
              top: 132,
              width: 640,
              height: 420,
              border: "5px solid rgba(255,255,255,.86)",
              borderBottom: "18px solid rgba(255,255,255,.86)",
              boxShadow: "0 26px 70px rgba(0,0,0,.62)",
              transform: "rotate(1.2deg) translateY(" + ((1 - enter) * 20) + "px)",
              overflow: "hidden",
              background:
                "linear-gradient(135deg, rgba(255,255,255,.18), rgba(255,255,255,.04)), repeating-linear-gradient(45deg, rgba(255,255,255,.08) 0 16px, rgba(255,255,255,.02) 16px 32px)",
            }}
          >
            {JOB.collageMediaRefs[0]?.src ? (
              <img
                src={JOB.collageMediaRefs[0].src}
                style={{
                  width: "100%",
                  height: "100%",
                  objectFit: "cover",
                  filter: "saturate(1.04) contrast(1.08) brightness(1.05)",
                }}
              />
            ) : null}
          </div>
          <div
            style={{
              position: "absolute",
              left: 96,
              top: 108,
              width: 88,
              height: 8,
              background: JOB.accentColor,
              boxShadow: "0 0 18px rgba(255,225,0,.35)",
            }}
          />
        </AbsoluteFill>
      ) : null}
      {isBlurredSideFill ? (
        <AbsoluteFill
          className="sideFillFrame"
          style={{ opacity }}
        >
          {JOB.collageMediaRefs[0]?.src ? (
            <img
              src={JOB.collageMediaRefs[0].src}
              style={{
                position: "absolute",
                inset: -48,
                width: "calc(100% + 96px)",
                height: "calc(100% + 96px)",
                objectFit: "cover",
                filter: "blur(30px) saturate(1.08) brightness(.72)",
                transform: "scale(1.06)",
              }}
            />
          ) : null}
          <div
            style={{
              position: "absolute",
              left: "50%",
              top: 48,
              bottom: 48,
              width: 610,
              transform: "translateX(-50%)",
              border: "4px solid rgba(255,255,255,.88)",
              boxShadow: "0 20px 70px rgba(0,0,0,.68)",
              background: "rgba(0,0,0,.18)",
              overflow: "hidden",
            }}
          >
            {JOB.collageMediaRefs[0]?.src ? (
              <img
                src={JOB.collageMediaRefs[0].src}
                style={{
                  width: "100%",
                  height: "100%",
                  objectFit: "contain",
                  background: "rgba(0,0,0,.72)",
                }}
              />
            ) : null}
          </div>
        </AbsoluteFill>
      ) : null}
      {isTraining67 && JOB.family === "title_reveal" ? (
        <AbsoluteFill
          style={{
            background: "linear-gradient(90deg, rgba(0,0,0,.68), rgba(0,0,0,.18), rgba(0,0,0,.62))",
            opacity: isBlackCollage ? opacity * 0.28 : (isCleanWhiteQuote || isProfileMemoryCard ? 0 : opacity),
          }}
        />
      ) : null}
      {isModuleLabelWhiteBlue ? (
        <div
          className="moduleAccentBlock"
          style={{
            position: "absolute",
            left: 72,
            bottom: 44,
            width: 168,
            height: 8,
            background: JOB.accentColor,
            opacity,
          }}
        />
      ) : null}
      {isSoftLightTransition ? (
        <div
          className="softLightSweep"
          style={{
            position: "absolute",
            left: sweep * width - width * 0.55,
            top: -height * 0.18,
            width: width * 0.48,
            height: height * 1.36,
            transform: "rotate(14deg)",
            background: "linear-gradient(90deg, rgba(255,255,255,0), " + JOB.accentColor + ", rgba(255,255,255,0))",
            filter: "blur(42px)",
            opacity: opacity * effectOpacity,
            mixBlendMode: "screen",
          }}
        />
      ) : null}
      {isHighlightWarmGlow ? (
        <div
          className="focusGlowRing"
          style={{
            position: "absolute",
            left: "50%",
            top: "50%",
            width: 620,
            height: 360,
            transform: "translate(-50%, -50%) scale(" + (0.94 + enter * 0.06) + ")",
            borderRadius: 999,
            border: "5px solid rgba(255,211,106,.42)",
            background: "radial-gradient(circle, rgba(255,211,106,.32), rgba(255,211,106,.12) 38%, rgba(0,0,0,0) 72%)",
            boxShadow: "0 0 80px " + JOB.accentColor + ", inset 0 0 70px rgba(255,255,255,.22)",
            opacity: opacity * effectOpacity,
            mixBlendMode: "screen",
          }}
        />
      ) : null}
      {!isCleanWhiteQuote && !isProfileMemoryCard && !isBlurredSideFill ? (
        <AbsoluteFill
          style={{
            background: "radial-gradient(circle at 22% 18%, rgba(255,244,184,.42), rgba(255,178,74,.14) 34%, rgba(0,0,0,0) 72%)",
            opacity: opacity * effectOpacity,
          }}
        />
      ) : null}
      {isStoryToMvFilmTransition ? (
        <div
          className="commercialTransitionTitleBlock"
          style={{
            position: "absolute",
            left: 540,
            right: 540,
            top: 366,
            padding: "24px 34px 26px",
            transform: "scale(" + (enableTitlePunch ? titleImpactPulse : 1) + ")",
            textAlign: "center",
            color: JOB.accentColor,
            fontFamily: "'Microsoft JhengHei', 'Noto Sans CJK TC', 'PingFang TC', Arial, sans-serif",
            fontSize: 62,
            fontWeight: 900,
            letterSpacing: 0,
            textShadow: "0 8px 28px rgba(0,0,0,.82)",
            borderTop: "1px solid rgba(255,255,255,.38)",
            borderBottom: "1px solid rgba(255,225,0,.62)",
            background: "linear-gradient(90deg, rgba(0,0,0,0), rgba(0,0,0,.38), rgba(0,0,0,0))",
            opacity: opacity * enter,
          }}
        >
          {JOB.label}
          {JOB.subtitle ? (
            <div
              style={{
                marginTop: 8,
                fontSize: 22,
                fontWeight: 700,
                color: "rgba(255,255,255,.86)",
                letterSpacing: 1.4,
              }}
            >
              {JOB.subtitle}
            </div>
          ) : null}
        </div>
      ) : null}
      {isCinematicOpening && enableGoldTitleSweep ? (
      <div
        className={isCinematicOpening ? "goldTitleSweep" : undefined}
        style={{
          position: "absolute",
          left: sweep * width - width * 0.42,
          top: -height * 0.08,
          width: width * 0.28,
          height: height * 1.24,
          transform: "rotate(10deg)",
          background: "linear-gradient(90deg, rgba(255,255,255,0), rgba(255,245,196,.55), rgba(255,255,255,0))",
          filter: "blur(24px)",
          opacity: opacity * effectOpacity,
        }}
      />
      ) : null}
      <div
        style={{
          position: "absolute",
          ...textBoxStyle,
          maxWidth: isCinematicOpening ? 1040 : (JOB.textPosition === "bottom_center" ? (isYellowSubtitleBar ? 1180 : (isCleanWhiteQuote ? 1040 : "100%")) : (isProfileMemoryCard ? 760 : 860)),
          padding: isCinematicOpening ? "10px 18px" : (isBlueWhiteLabel ? "14px 28px" : (isYellowSubtitleBar ? "14px 26px" : (isCleanWhiteQuote ? "24px 42px" : (isProfileMemoryCard ? "18px 24px" : "8px 14px")))),
          borderRadius: isBlueWhiteLabel ? 0 : (isCleanWhiteQuote ? 0 : 8),
          borderBottom: isBlueWhiteLabel ? "8px solid rgba(24,82,178,.96)" : (isFilmStripCard ? "5px solid " + JOB.accentColor : "none"),
          background: labelBackground,
          color: labelColor,
          fontFamily: "'Microsoft JhengHei', 'Noto Sans CJK TC', 'PingFang TC', Arial, sans-serif",
          fontSize: isTraining67 && JOB.family === "title_reveal" && !isCleanWhiteQuote && !isProfileMemoryCard ? Math.max(commercialTitleScale, 78) : textFontSize,
          fontWeight: isTraining67 ? 900 : 700,
          letterSpacing: 0.4,
          textShadow: labelShadow,
          opacity: suppressStoryToMvBaseText ? 0 : ((preview || JOB.showTextInRender) ? opacity : 0),
        }}
      >
        {isYellowSubtitleBar && JOB.speakerName ? (
          <span style={{ marginRight: 12, color: "rgba(20,20,20,.82)", fontWeight: 900 }}>
            {JOB.speakerName}
          </span>
        ) : null}
        {JOB.label}
        {isCinematicOpening ? (
          <div
            className="cinematicTitleUnderline"
            style={{
              width: 188,
              height: 6,
              marginTop: 12,
              background: "linear-gradient(90deg, " + JOB.accentColor + ", rgba(255,255,255,.62), rgba(255,255,255,0))",
              boxShadow: "0 0 24px rgba(255,225,0,.32)",
            }}
          />
        ) : null}
        {JOB.subtitle ? (
          <div
            className={isCinematicOpening ? "cinematicSubtitleLine" : undefined}
            style={{
              marginTop: 10,
              color: isCleanWhiteQuote ? "rgba(17,17,17,.62)" : (isModuleLabelWhiteBlue ? "rgba(25,82,178,.72)" : "rgba(255,255,255,.9)"),
              fontSize: Math.max(20, Math.round(textFontSize * 0.24)),
              fontWeight: 700,
              letterSpacing: 2,
              textShadow: isCleanWhiteQuote ? "none" : "0 3px 12px rgba(0,0,0,.72)",
            }}
          >
            {JOB.subtitle}
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};

const Root = () => (
  <>
    <Composition
      id="HermesEffectOverlay"
      component={HermesEffectOverlay}
      durationInFrames={JOB.durationFrames}
      fps={JOB.fps}
      width={1920}
      height={1080}
      defaultProps={{ preview: false }}
    />
    <Composition
      id="HermesEffectOverlayPreview"
      component={HermesEffectOverlay}
      durationInFrames={JOB.durationFrames}
      fps={JOB.fps}
      width={1920}
      height={1080}
      defaultProps={{ preview: true }}
    />
  </>
);

registerRoot(Root);
`;
}

function localRemotionBin(projectRoot) {
  const cmd = process.platform === "win32" ? "remotion.cmd" : "remotion";
  const candidate = path.join(projectRoot, "node_modules", ".bin", cmd);
  return fs.existsSync(candidate) ? candidate : "npx remotion";
}

function ensureRemotionProject(projectRoot) {
  const packageJson = path.join(projectRoot, "package.json");
  if (!fs.existsSync(packageJson)) {
    fs.writeFileSync(packageJson, `${JSON.stringify({
      private: true,
      name: "hermes-remotion-effect-worker",
      version: "0.0.0",
      type: "module",
      dependencies: {
        "@remotion/cli": "latest",
        react: "latest",
        "react-dom": "latest",
        remotion: "latest",
      },
      devDependencies: {
        "@types/react": "latest",
        "@types/react-dom": "latest",
        typescript: "latest",
      },
    }, null, 2)}\n`, "utf8");
  }
  const remotionBin = path.join(
    projectRoot,
    "node_modules",
    ".bin",
    process.platform === "win32" ? "remotion.cmd" : "remotion",
  );
  if (fs.existsSync(remotionBin)) {
    return;
  }
  const proc = spawnSync("npm", ["install"], {
    cwd: projectRoot,
    shell: process.platform === "win32",
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
  });
  if (proc.status !== 0) {
    throw new Error((proc.stderr || proc.stdout || "npm install failed").trim());
  }
}

function splitCommand(command) {
  if (command.includes(" ")) {
    return { executable: command, shell: true };
  }
  return { executable: command, shell: process.platform === "win32" };
}

function runCommand(command, args, cwd) {
  const { executable, shell } = splitCommand(command);
  const proc = spawnSync(executable, args, {
    cwd,
    shell,
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
  });
  if (proc.status !== 0) {
    throw new Error((proc.stderr || proc.stdout || `command failed: ${command}`).trim());
  }
  return {
    command: [command, ...args],
    stdout: proc.stdout || "",
  };
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.jobJson || !args.previewFile || !args.renderedAsset || !args.projectRoot) {
    throw new Error(usage());
  }
  const cwd = process.cwd();
  const projectRoot = resolvePath(args.projectRoot, cwd);
  const jobFile = resolvePath(args.jobJson, cwd);
  const job = loadJob(jobFile);
  const previewFile = resolvePath(args.previewFile, cwd);
  const renderedAsset = resolvePath(args.renderedAsset, cwd);
  assertNotProtected(previewFile);
  assertNotProtected(renderedAsset);

  fs.mkdirSync(path.join(projectRoot, "src"), { recursive: true });
  fs.mkdirSync(path.dirname(previewFile), { recursive: true });
  fs.mkdirSync(path.dirname(renderedAsset), { recursive: true });
  const entry = path.join(projectRoot, "src", `hermes_worker_${job.job_id}.tsx`);
  fs.writeFileSync(entry, buildEntry(job, path.dirname(jobFile)), "utf8");

  if (!args.writeEntryOnly) {
    ensureRemotionProject(projectRoot);
  }
  const remotionBin = args.remotionBin || localRemotionBin(projectRoot);
  const renderArgs = [
    "render",
    entry,
    "HermesEffectOverlay",
    renderedAsset,
    "--codec=prores",
    "--image-format=png",
    "--pixel-format=yuva444p10le",
    "--prores-profile=4444",
  ];
  const previewArgs = [
    "render",
    entry,
    "HermesEffectOverlayPreview",
    previewFile,
    "--codec=h264",
    "--pixel-format=yuv420p",
  ];
  const payload = {
    status: args.writeEntryOnly ? "entry_written" : "rendered",
    backend: "remotion_cli",
    job_id: job.job_id,
    entry,
    preview_file: previewFile,
    rendered_asset: renderedAsset,
    remotion_bin: remotionBin,
    render_command: [remotionBin, ...renderArgs],
    preview_command: [remotionBin, ...previewArgs],
  };
  if (!args.writeEntryOnly) {
    const render = runCommand(remotionBin, renderArgs, projectRoot);
    const preview = runCommand(remotionBin, previewArgs, projectRoot);
    if (!fs.existsSync(renderedAsset) || !fs.existsSync(previewFile)) {
      throw new Error("Remotion render completed but expected output files are missing");
    }
    payload.render_stdout = render.stdout;
    payload.preview_stdout = preview.stdout;
  }
  process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
}

try {
  main();
} catch (err) {
  process.stderr.write(`${err && err.message ? err.message : String(err)}\n`);
  process.exit(2);
}
