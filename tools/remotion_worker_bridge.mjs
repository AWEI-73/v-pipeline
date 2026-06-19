#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";

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

function buildEntry(job) {
  const durationSec = positiveFinite((job.timing || {}).duration_sec ?? job.duration_sec, "duration_sec");
  const fps = 30;
  const durationFrames = Math.max(1, Math.ceil(durationSec * fps));
  const intent = String((job.props || {}).intent || job.prompt || "Hermes motion overlay");
  const family = String(job.component_family || "custom_motion_effect");
  const visual = Array.isArray((job.props || {}).visual_language)
    ? (job.props || {}).visual_language.join(" / ")
    : "";
  const label = `${family}: ${intent}`;
  const jobLiteral = {
    jobId: job.job_id,
    label,
    prompt: String(job.prompt || ""),
    visual,
    durationFrames,
    fps,
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
  const opacity = clamp(enter * exit);
  return (
    <AbsoluteFill style={{ backgroundColor: preview ? "#101018" : "transparent", overflow: "hidden" }}>
      <AbsoluteFill
        style={{
          background: "radial-gradient(circle at 22% 18%, rgba(255,244,184,.42), rgba(255,178,74,.14) 34%, rgba(0,0,0,0) 72%)",
          opacity: opacity * 0.92,
        }}
      />
      <div
        style={{
          position: "absolute",
          left: sweep * width - width * 0.42,
          top: -height * 0.08,
          width: width * 0.28,
          height: height * 1.24,
          transform: "rotate(10deg)",
          background: "linear-gradient(90deg, rgba(255,255,255,0), rgba(255,245,196,.55), rgba(255,255,255,0))",
          filter: "blur(24px)",
          opacity: opacity,
        }}
      />
      <div
        style={{
          position: "absolute",
          left: 64,
          bottom: 56,
          color: "rgba(255,248,220,.92)",
          fontFamily: "Arial, sans-serif",
          fontSize: 28,
          fontWeight: 700,
          letterSpacing: 0.4,
          textShadow: "0 3px 18px rgba(0,0,0,.45)",
          opacity: preview ? opacity : 0,
        }}
      >
        {JOB.label}
        <div style={{ marginTop: 8, fontSize: 18, opacity: 0.76 }}>{JOB.visual}</div>
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
  const job = loadJob(resolvePath(args.jobJson, cwd));
  const previewFile = resolvePath(args.previewFile, cwd);
  const renderedAsset = resolvePath(args.renderedAsset, cwd);
  assertNotProtected(previewFile);
  assertNotProtected(renderedAsset);

  fs.mkdirSync(path.join(projectRoot, "src"), { recursive: true });
  fs.mkdirSync(path.dirname(previewFile), { recursive: true });
  fs.mkdirSync(path.dirname(renderedAsset), { recursive: true });
  const entry = path.join(projectRoot, "src", `hermes_worker_${job.job_id}.tsx`);
  fs.writeFileSync(entry, buildEntry(job), "utf8");

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
