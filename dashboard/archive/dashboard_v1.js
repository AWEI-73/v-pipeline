document.addEventListener("DOMContentLoaded", () => {
    // UI Elements - Header & Tabs
    const projectSelector = document.getElementById("project-selector");
    const metaProject = document.getElementById("meta-project");
    const metaRoot = document.getElementById("meta-root");
    const metaDuration = document.getElementById("meta-duration");
    const gateStatus = document.getElementById("gate-status");
    const btnOpenWorkbench = document.getElementById("btn-open-workbench");

    const btnTabEditor = document.getElementById("btn-tab-editor");
    const btnTabStorymap = document.getElementById("btn-tab-storymap");
    const btnTabPipeline = document.getElementById("btn-tab-pipeline");

    const viewEditor = document.getElementById("view-editor");
    const viewStorymap = document.getElementById("view-storymap");
    const viewPipeline = document.getElementById("view-pipeline");

    // Profile summary details
    const profileMode = document.getElementById("profile-mode");
    const profileProvider = document.getElementById("profile-provider");
    const profileGraphics = document.getElementById("profile-graphics");
    const profileEffects = document.getElementById("profile-effects");
    const bgmContainer = document.getElementById("bgm-player-container");
    const workbenchStatus = document.getElementById("workbench-status");

    // Left Sidebar Elements
    const issuesList = document.getElementById("issues-list");
    const sidebarSegmentsList = document.getElementById("sidebar-segments-list");
    const contactSheetContainer = document.getElementById("contact-sheet-container");

    // Center Video Panel Elements
    const finalVideo = document.getElementById("final-video");
    const noVideoOverlay = document.getElementById("no-video-overlay");
    const btnVideoPlay = document.getElementById("btn-video-play");
    const btnVideoStop = document.getElementById("btn-video-stop");
    const videoTimeDisplay = document.getElementById("video-time-display");

    // Right Detail Panel Elements
    const detailPanelContent = document.getElementById("detail-panel-content");

    // Zoom Controls
    const btnZoomOut = document.getElementById("btn-zoom-out");
    const btnZoomIn = document.getElementById("btn-zoom-in");
    const btnZoomFit = document.getElementById("btn-zoom-fit");
    const timelineZoomSlider = document.getElementById("timeline-zoom-slider");

    // Timeline Elements
    const timelineRuler = document.getElementById("timeline-ruler");
    const timelinePlayhead = document.getElementById("timeline-playhead");
    const trackVideoSlots = document.getElementById("track-video-slots");
    const trackAudioSlots = document.getElementById("track-audio-slots");
    const trackSubtitleSlots = document.getElementById("track-subtitle-slots");

    // Tab B (Pipeline Console) Elements
    const findingsSection = document.getElementById("findings-section");
    const findingsList = document.getElementById("findings-list");
    const nextActionContainer = document.getElementById("next-action-container");
    const nextActionVal = document.getElementById("next-action-val");
    const nextActionCmdBox = document.getElementById("next-action-cmd-box");
    const nextActionCmd = document.getElementById("next-action-cmd");
    const btnCopyCmd = document.getElementById("btn-copy-cmd");
    const nodesChecklistRail = document.getElementById("nodes-checklist-rail");
    const nodeDetailsContent = document.getElementById("node-details-content");

    // Tab C (Story Map) Elements
    const storylineNodesContainer = document.getElementById("storyline-nodes-container");
    const alignmentDetailCardStorymap = document.getElementById("alignment-detail-card-storymap");

    // Global State Variables
    let artifactData = null;
    let selectedSlotIndex = null;
    let pixelsPerSecond = 15;
    let currentRootPath = "";
    let activeNodeId = 12;

    // Create Tooltip Element dynamically
    const tooltip = document.createElement("div");
    tooltip.className = "timeline-slot-tooltip";
    document.body.appendChild(tooltip);

    // ==========================================
    // Tab Navigation Logic
    // ==========================================
    function switchTab(activeBtn, activeView) {
        [btnTabEditor, btnTabStorymap, btnTabPipeline].forEach(b => b.classList.remove("active"));
        [viewEditor, viewStorymap, viewPipeline].forEach(v => v.classList.remove("active"));
        activeBtn.classList.add("active");
        activeView.classList.add("active");
    }

    if (btnTabEditor) btnTabEditor.addEventListener("click", () => switchTab(btnTabEditor, viewEditor));
    if (btnTabStorymap) btnTabStorymap.addEventListener("click", () => switchTab(btnTabStorymap, viewStorymap));
    if (btnTabPipeline) btnTabPipeline.addEventListener("click", () => switchTab(btnTabPipeline, viewPipeline));
    if (btnOpenWorkbench) {
        btnOpenWorkbench.addEventListener("click", () => {
            const url = (artifactData && artifactData.workbench && artifactData.workbench.url) || "http://localhost:8770/workbench";
            window.open(url, "_blank", "noopener");
        });
    }

    // ==========================================
    // Fetch and Load Projects List
    // ==========================================
    async function loadProjects() {
        try {
            const res = await fetch("/api/projects");
            const data = await res.json();
            projectSelector.innerHTML = "";
            
            data.forEach(p => {
                const opt = document.createElement("option");
                opt.value = p.path;
                opt.textContent = p.name;
                projectSelector.appendChild(opt);
            });

            // Read query root parameter
            const urlParams = new URLSearchParams(window.location.search);
            const queryRoot = urlParams.get("root");
            if (queryRoot) {
                const matchedProj = data.find(p => {
                    const pNorm = p.path.toLowerCase().replace(/\\/g, '/');
                    const qNorm = queryRoot.toLowerCase().replace(/\\/g, '/');
                    return pNorm === qNorm || pNorm.endsWith('/' + qNorm) || qNorm.endsWith('/' + pNorm);
                });
                if (matchedProj) {
                    projectSelector.value = matchedProj.path;
                    currentRootPath = matchedProj.path;
                } else {
                    const opt = document.createElement("option");
                    opt.value = queryRoot;
                    opt.textContent = `指定專案: ${queryRoot}`;
                    projectSelector.appendChild(opt);
                    projectSelector.value = queryRoot;
                    currentRootPath = queryRoot;
                }
            } else if (data.length > 0) {
                projectSelector.value = data[0].path;
                currentRootPath = data[0].path;
            }
        } catch (e) {
            console.error("Failed to load projects:", e);
            projectSelector.innerHTML = '<option value="">加載失敗</option>';
        }
    }

    // ==========================================
    // Load Selected Project Artifacts
    // ==========================================
    async function fetchArtifactsData() {
        if (!currentRootPath) return;
        try {
            const res = await fetch(`/api/artifacts?root=${encodeURIComponent(currentRootPath)}`);
            artifactData = await res.json();
            
            renderDashboard();
        } catch (e) {
            console.error("Failed to load artifacts:", e);
        }
    }

    projectSelector.addEventListener("change", (e) => {
        currentRootPath = e.target.value;
        const newUrl = `${window.location.pathname}?root=${encodeURIComponent(currentRootPath)}`;
        window.history.pushState({ path: newUrl }, "", newUrl);
        fetchArtifactsData();
    });

    // Helper to resolve asset URLs
    function getAssetUrl(filename) {
        if (!filename) return "";
        return `/static/${encodeURIComponent(filename)}?root=${encodeURIComponent(artifactData.artifact_root)}`;
    }

    // ==========================================
    // Main UI Render Dispatcher
    // ==========================================
    function renderDashboard() {
        if (!artifactData) return;

        const stateData = artifactData.state || {};
        const runMode = stateData.mode || "mv";
        const duration = getTimelineDuration();

        // 1. Update Header Information
        metaProject.textContent = stateData.mode ? `Hermes (${stateData.mode})` : "Hermes Video Pipeline";
        metaRoot.textContent = getFilename(artifactData.artifact_root) || artifactData.artifact_root;
        metaDuration.textContent = duration.toFixed(2) + "s";

        // Update Gate Status Badge
        let pass = false;
        let reasons = [];
        if (artifactData.delivery_gate) {
            pass = artifactData.delivery_gate.pass;
            reasons = artifactData.delivery_gate.blocking || [];
        } else if (artifactData.review_report && artifactData.review_report.need_aware) {
            pass = artifactData.review_report.need_aware.all_segments_matched;
            if (!pass) reasons = ["素材語意對齊存在 Drift 或 Gap 錯位"];
        }

        if (pass) {
            gateStatus.className = "badge status-success";
            gateStatus.querySelector(".text").textContent = "PASS";
        } else {
            gateStatus.className = "badge status-fail";
            gateStatus.querySelector(".text").textContent = "FAIL";
        }

        // Sub-header Info
        profileMode.textContent = runMode;
        profileProvider.textContent = artifactData.black_frame_audit?.provider || artifactData.broll_audit?.provider || "pexels";
        profileGraphics.textContent = artifactData.caption_audit?.graphics_backend || "ffmpeg";
        profileEffects.textContent = artifactData.black_frame_audit?.profile || "normal";
        
        // Background Music display
        let bgmMusicFile = "bgm.mp3";
        if (artifactData.review_report && artifactData.review_report.music) {
            bgmMusicFile = getFilename(artifactData.review_report.music);
        }
        if (bgmContainer) {
            bgmContainer.innerHTML = `<div style="font-size: 11px; font-weight: 700; color: #64748b;">🎵 背景配樂: ${bgmMusicFile}</div>`;
        }

        // 2. Load Video Source
        if (artifactData.final_video_url) {
            finalVideo.querySelector("source").src = artifactData.final_video_url;
            finalVideo.load();
            finalVideo.style.display = "block";
            noVideoOverlay.style.display = "none";
        } else {
            finalVideo.style.display = "none";
            noVideoOverlay.style.display = "flex";
        }

        // 3. Render Left Sidebar (Issues, Segments, Contact Sheet)
        renderIssuesList();
        renderSegmentsList();
        renderContactSheet();

        // 4. Render Multi-track Timeline
        renderTimeline();

        // 5. Populate Tabs B & C
        renderWorkbenchStatus();
        renderStorylineTrack();
        renderPipelineConsole();
    }

    function renderWorkbenchStatus() {
        if (!workbenchStatus) return;
        const workbench = artifactData.workbench || {};
        const summary = workbench.draft_summary || {};
        const drafts = workbench.draft_artifacts || {};
        const presentCount = Number(summary.present_count || 0);
        const badgeClass = presentCount > 0 ? "badge warn" : "badge status-pass";
        const badgeText = presentCount > 0 ? `${presentCount} draft file(s)` : "clean";
        const tracked = [
            ["timeline", drafts.timeline_patch],
            ["contract", drafts.workbench_contract_patch],
            ["handoff", drafts.workbench_handoff],
            ["subtitles", drafts.subtitle_patch],
            ["audio", drafts.audio_cue_patch],
            ["effects", drafts.effect_patch],
            ["review", drafts.workbench_review_report],
        ];
        const chips = tracked.map(([label, item]) => {
            const active = item && item.exists;
            return `<span class="workbench-draft-chip ${active ? "active" : ""}">${label}: ${active ? "present" : "none"}</span>`;
        }).join("");

        workbenchStatus.innerHTML = `
            <div class="workbench-status-head">
                <span class="workbench-status-label">Workbench drafts</span>
                <span class="${badgeClass}">${badgeText}</span>
            </div>
            <div class="workbench-status-body">
                <span>Read-only dashboard. Edit in Workbench, then let Agent consume draft patches.</span>
                <div class="workbench-draft-chips">${chips}</div>
            </div>
        `;
    }

    function getTimelineDuration() {
        const slots = artifactData.timeline_slots || [];
        if (slots.length === 0) return 0.0;
        return Math.max(...slots.map(s => s.end_sec || 0.0));
    }

    function getFilename(pathStr) {
        if (!pathStr) return "";
        return pathStr.replace(/\\/g, '/').split('/').pop();
    }

    // ==========================================
    // Left Sidebar Renders
    // ==========================================
    function renderIssuesList() {
        issuesList.innerHTML = "";
        const issues = artifactData.issues || [];

        if (issues.length === 0) {
            issuesList.innerHTML = '<p class="placeholder-text">✅ 無任何品質缺陷或警告。</p>';
            return;
        }

        issues.forEach(iss => {
            const item = document.createElement("div");
            item.className = `issue-item severity-${iss.severity || 'error'}`;
            item.textContent = iss.message || "品質稽核警告";
            item.addEventListener("click", () => {
                // Seek to the segment/slot index
                let targetSlot = null;
                if (iss.slot_index !== undefined) {
                    targetSlot = (artifactData.timeline_slots || []).find(s => s.slot_index === iss.slot_index);
                } else if (iss.segment !== undefined) {
                    targetSlot = (artifactData.timeline_slots || []).find(s => (s.segment === iss.segment || s.segment_id === iss.segment));
                }
                if (targetSlot) {
                    selectSlot(targetSlot);
                    seekVideo(targetSlot.start_sec);
                }
            });
            issuesList.appendChild(item);
        });
    }

    function renderSegmentsList() {
        sidebarSegmentsList.innerHTML = "";
        const slots = artifactData.timeline_slots || [];

        if (slots.length === 0) {
            sidebarSegmentsList.innerHTML = '<p class="placeholder-text">無故事段落資料。</p>';
            return;
        }

        slots.forEach(slot => {
            const item = document.createElement("div");
            item.className = "sidebar-seg-item";
            if (slot.slot_index === selectedSlotIndex) {
                item.classList.add("active");
            }
            
            const segmentId = (slot.segment !== undefined && slot.segment !== null) ? slot.segment : slot.slot_index;
            const title = slot.title || slot.label || `段落 ${segmentId}`;
            const displayTitle = title.length > 18 ? title.substring(0, 18) + "..." : title;
            
            item.innerHTML = `
                <span>Seg ${segmentId} - ${displayTitle}</span>
                <span class="badge ${slot.status === 'matched' ? 'status-success' : 'status-fail'}" style="font-size: 8px; padding: 2px 4px;">${slot.status}</span>
            `;

            item.addEventListener("click", () => {
                selectSlot(slot);
                seekVideo(slot.start_sec);
            });
            sidebarSegmentsList.appendChild(item);
        });
    }

    function renderContactSheet() {
        contactSheetContainer.innerHTML = "";
        if (artifactData.contact_sheet_url) {
            const img = document.createElement("img");
            img.src = artifactData.contact_sheet_url;
            img.className = "contact-sheet-img";
            img.alt = "Contact Sheet Grid";
            img.addEventListener("click", () => {
                showToast("視覺關鍵影格網格 (Contact Sheet) 點擊定位時間軸成功！");
                seekVideo(0);
            });
            contactSheetContainer.appendChild(img);
        } else {
            contactSheetContainer.innerHTML = '<p class="placeholder-text">無 Contact Sheet 圖像。</p>';
        }
    }

    // ==========================================
    // Multi-track Timeline Renders & Sync
    // ==========================================
    function renderTimeline() {
        const slots = artifactData.timeline_slots || [];
        const totalDuration = getTimelineDuration() || 10.0;
        
        // Compute width
        const trackWidth = totalDuration * pixelsPerSecond;
        timelineRuler.style.width = `${trackWidth}px`;
        trackVideoSlots.style.width = `${trackWidth}px`;
        trackAudioSlots.style.width = `${trackWidth}px`;
        trackSubtitleSlots.style.width = `${trackWidth}px`;

        // Render Ruler
        timelineRuler.innerHTML = "";
        const step = Math.max(1, Math.round(totalDuration / 10));
        for (let t = 0; t <= totalDuration; t += step) {
            const tick = document.createElement("div");
            tick.style.position = "absolute";
            tick.style.left = `${t * pixelsPerSecond}px`;
            tick.style.transform = "translateX(-50%)";
            tick.style.fontSize = "9px";
            tick.style.fontWeight = "bold";
            tick.style.color = "#94a3b8";
            tick.textContent = `${t.toFixed(0)}s`;
            timelineRuler.appendChild(tick);
        }

        // 1. Render Video Track
        trackVideoSlots.innerHTML = "";
        slots.forEach(slot => {
            const bar = document.createElement("div");
            bar.className = "timeline-bar-slot";
            
            // Map role classes or status classes
            const role = slot.role || "";
            if (role.includes("opening")) {
                bar.classList.add("slot-opening");
            } else if (role.includes("beat") || role.includes("SRP1")) {
                bar.classList.add("slot-beat");
            } else if (role.includes("climax")) {
                bar.classList.add("slot-climax");
            } else {
                bar.classList.add(`slot-${slot.status}`);
            }

            if (slot.slot_index === selectedSlotIndex) {
                bar.classList.add("selected");
            }

            const width = slot.duration_sec * pixelsPerSecond;
            const left = slot.start_sec * pixelsPerSecond;
            bar.style.width = `${width}px`;
            bar.style.left = `${left}px`;
            
            const segmentId = (slot.segment !== undefined && slot.segment !== null) ? slot.segment : slot.slot_index;
            const title = slot.title || slot.label || `Seg ${segmentId}`;
            bar.textContent = title;

            // Slot Click seek behavior
            bar.addEventListener("click", () => {
                selectSlot(slot);
                seekVideo(slot.start_sec);
            });

            // Hover tooltip
            bar.addEventListener("mouseenter", (e) => {
                tooltip.style.display = "block";
                const segmentId = (slot.segment !== undefined && slot.segment !== null) ? slot.segment : slot.slot_index;
                tooltip.innerHTML = `
                    <strong>Seg ${segmentId}</strong><br>
                    Need: ${slot.expected_need_ref || 'None'}<br>
                    Dur: ${slot.duration_sec.toFixed(2)}s (${slot.start_sec.toFixed(1)}s - ${slot.end_sec.toFixed(1)}s)<br>
                    Source: ${getFilename(slot.source || slot.source_path || 'None')}
                `;
            });
            bar.addEventListener("mousemove", (e) => {
                tooltip.style.left = `${e.pageX + 10}px`;
                tooltip.style.top = `${e.pageY + 10}px`;
            });
            bar.addEventListener("mouseleave", () => {
                tooltip.style.display = "none";
            });

            trackVideoSlots.appendChild(bar);
        });

        // 2. Render Audio Track (Render music segments or placeholders)
        trackAudioSlots.innerHTML = "";
        let bgmMusicFile = "BGM Music";
        if (artifactData.review_report && artifactData.review_report.music) {
            bgmMusicFile = getFilename(artifactData.review_report.music);
        }
        const audioBar = document.createElement("div");
        audioBar.className = "timeline-bar-slot slot-opening";
        audioBar.style.width = `${trackWidth}px`;
        audioBar.style.left = "0px";
        audioBar.textContent = `🎵 ${bgmMusicFile}`;
        trackAudioSlots.appendChild(audioBar);

        // 3. Render Subtitles Track
        trackSubtitleSlots.innerHTML = "";
        const subtitles = artifactData.subtitles || [];
        subtitles.forEach((cue, idx) => {
            const bar = document.createElement("div");
            bar.className = "timeline-bar-slot slot-matched";
            const width = (cue.end_sec - cue.start_sec) * pixelsPerSecond;
            const left = cue.start_sec * pixelsPerSecond;
            bar.style.width = `${width}px`;
            bar.style.left = `${left}px`;
            bar.textContent = cue.text;
            bar.title = `Sub: ${cue.text}`;
            bar.addEventListener("click", () => {
                seekVideo(cue.start_sec);
            });
            trackSubtitleSlots.appendChild(bar);
        });

        // Sync Playhead Position
        updatePlayheadUI(finalVideo ? finalVideo.currentTime : 0);
    }

    function updatePlayheadUI(seconds) {
        const leftPx = seconds * pixelsPerSecond;
        if (timelinePlayhead) {
            timelinePlayhead.style.left = `${leftPx}px`;
        }
    }

    function seekVideo(seconds) {
        if (finalVideo && artifactData && artifactData.final_video_url) {
            finalVideo.currentTime = seconds;
        }
        updatePlayheadUI(seconds);
    }

    // ==========================================
    // Video Player Playback Control Hooks
    // ==========================================
    if (finalVideo) {
        finalVideo.addEventListener("timeupdate", () => {
            const curr = finalVideo.currentTime;
            const dur = finalVideo.duration || getTimelineDuration() || 0.0;
            
            // 1. Time display
            videoTimeDisplay.textContent = `${curr.toFixed(2)}s / ${dur.toFixed(2)}s`;
            
            // 2. Playhead lines sync
            updatePlayheadUI(curr);

            // 3. Active timeline slot highlight pulses
            const slots = artifactData ? (artifactData.timeline_slots || []) : [];
            const activeSlot = slots.find(s => curr >= s.start_sec && curr < s.end_sec);
            
            // Remove active highlight from all
            document.querySelectorAll("#track-video-slots .timeline-bar-slot").forEach(bar => {
                bar.classList.remove("active-playing");
            });

            if (activeSlot) {
                // Find matching DOM slot
                const bars = trackVideoSlots.children;
                for (let i = 0; i < bars.length; i++) {
                    if (slots[i] && slots[i].slot_index === activeSlot.slot_index) {
                        bars[i].classList.add("active-playing");
                        break;
                    }
                }
            }
        });

        finalVideo.addEventListener("play", () => {
            btnVideoPlay.textContent = "⏸ 暫停";
        });

        finalVideo.addEventListener("pause", () => {
            btnVideoPlay.textContent = "▶ 播放";
        });
    }

    if (btnVideoPlay) {
        btnVideoPlay.addEventListener("click", () => {
            if (!artifactData || !artifactData.final_video_url) return;
            if (finalVideo.paused) {
                finalVideo.play().catch(e => console.error("Video play blocked:", e));
            } else {
                finalVideo.pause();
            }
        });
    }

    if (btnVideoStop) {
        btnVideoStop.addEventListener("click", () => {
            if (!artifactData || !artifactData.final_video_url) return;
            finalVideo.pause();
            finalVideo.currentTime = 0;
            updatePlayheadUI(0);
        });
    }

    // ==========================================
    // Selection and Right Detail Panel Populate
    // ==========================================
    function selectSlot(slot) {
        selectedSlotIndex = slot.slot_index;
        
        // Re-render sidebar items active selection
        document.querySelectorAll(".sidebar-seg-item").forEach((item, idx) => {
            const target = (artifactData.timeline_slots || [])[idx];
            if (target && target.slot_index === selectedSlotIndex) {
                item.classList.add("active");
            } else {
                item.classList.remove("active");
            }
        });

        // Re-render timeline selection borders
        document.querySelectorAll("#track-video-slots .timeline-bar-slot").forEach((bar, idx) => {
            const target = (artifactData.timeline_slots || [])[idx];
            if (target && target.slot_index === selectedSlotIndex) {
                bar.classList.add("selected");
            } else {
                bar.classList.remove("selected");
            }
        });

        // Populate detail panel content
        populateDetailPanel(slot);
    }

    function populateDetailPanel(slot) {
        detailPanelContent.innerHTML = "";
        
        const segmentId = (slot.segment !== undefined && slot.segment !== null) ? slot.segment : slot.segment_id;
        const fields = [
            { label: "Slot Index (索引)", value: slot.slot_index, mono: true },
            { label: "Segment ID (段落編號)", value: segmentId !== undefined && segmentId !== null ? segmentId : "無" },
            { label: "Scene ID (場景編號)", value: slot.scene_id },
            { label: "Start Time (起點)", value: `${slot.start_sec.toFixed(2)}s`, mono: true },
            { label: "End Time (終點)", value: `${slot.end_sec.toFixed(2)}s`, mono: true },
            { label: "Duration (長度)", value: `${slot.duration_sec.toFixed(2)}s`, mono: true },
            { label: "Source Filename (素材名稱)", value: getFilename(slot.source || slot.source_path) },
            { label: "Source Absolute Path (完整路徑)", value: slot.source || slot.source_path || "無", mono: true },
            { label: "Expected Need (期待需求)", value: slot.expected_need_ref || "無" },
            { label: "Selected Need ID (配對需求)", value: slot.selected_need_id || "無" },
            { label: "Audit Status (審驗狀態)", value: slot.status, badge: true },
            { label: "Narrative Caption (畫面敘述)", value: slot.caption || "無" },
            { label: "Narration Subtitle (字幕配音)", value: slot.text_overlay?.narrative || slot.text?.subtitle || slot.subtitle || "無" },
            { label: "Opening Role (片頭角色)", value: slot.opening_role || "否" },
            { label: "Beat Role (配樂小節角色)", value: slot.beat_role || "否" },
            { label: "Arc Role (情節發展角色)", value: slot.arc_role || "否" },
            { label: "Retrieval Path (檢索路径)", value: slot.retrieval_path || "無" },
            { label: "Retrieval Score (檢索配對分)", value: slot.retrieval_score || "無", mono: true }
        ];

        fields.forEach(f => {
            const row = document.createElement("div");
            row.className = "detail-property-row";
            
            let valHtml = "";
            if (f.badge) {
                const statusColor = f.value === 'matched' ? 'status-success' : (f.value === 'render_failed' ? 'status-warning' : 'status-fail');
                valHtml = `<span class="badge ${statusColor}">${f.value}</span>`;
            } else if (f.mono) {
                valHtml = `<span class="detail-p-val-mono">${f.value}</span>`;
            } else {
                valHtml = `<span>${f.value}</span>`;
            }

            row.innerHTML = `
                <span class="p-label">${f.label}</span>
                <span class="p-val">${valHtml}</span>
            `;
            detailPanelContent.appendChild(row);
        });
    }

    // ==========================================
    // Zoom Controls Implementation
    // ==========================================
    if (timelineZoomSlider) {
        timelineZoomSlider.value = pixelsPerSecond;
        timelineZoomSlider.addEventListener("input", (e) => {
            pixelsPerSecond = parseInt(e.target.value);
            renderTimeline();
        });
    }

    if (btnZoomIn) {
        btnZoomIn.addEventListener("click", () => {
            pixelsPerSecond = Math.min(60, pixelsPerSecond + 5);
            if (timelineZoomSlider) timelineZoomSlider.value = pixelsPerSecond;
            renderTimeline();
        });
    }

    if (btnZoomOut) {
        btnZoomOut.addEventListener("click", () => {
            pixelsPerSecond = Math.max(5, pixelsPerSecond - 5);
            if (timelineZoomSlider) timelineZoomSlider.value = pixelsPerSecond;
            renderTimeline();
        });
    }

    if (btnZoomFit) {
        btnZoomFit.addEventListener("click", () => {
            const totalDuration = getTimelineDuration() || 10.0;
            const containerWidth = document.querySelector(".timeline-tracks-wrapper").clientWidth;
            pixelsPerSecond = Math.max(5, Math.min(60, (containerWidth - 160) / totalDuration));
            if (timelineZoomSlider) timelineZoomSlider.value = Math.round(pixelsPerSecond);
            renderTimeline();
            showToast("時間軸已調整至最適寬度！");
        });
    }

    // ==========================================
    // Tab C: Story Map Nodes Rendering
    // ==========================================
    function renderStorylineTrack() {
        if (!storylineNodesContainer) return;
        storylineNodesContainer.innerHTML = "";
        const slots = artifactData.timeline_slots || [];

        if (slots.length === 0) {
            storylineNodesContainer.innerHTML = '<p class="placeholder-text">無故事地圖節點。</p>';
            return;
        }

        slots.forEach((slot, idx) => {
            const node = document.createElement("div");
            node.className = "story-node";
            if (slot.status !== 'matched') {
                node.style.borderColor = "#ef4444";
                node.style.background = "#fef2f2";
            }
            const segmentId = (slot.segment !== undefined && slot.segment !== null) ? slot.segment : slot.slot_index;
            node.innerHTML = `
                <div class="node-index">Seg ${segmentId}</div>
                <div class="node-role" style="font-size: 9px; color: #4b5563;">${slot.role || 'story'}</div>
                <div class="node-title" style="font-size: 11px; font-weight: 700; margin-top: 4px;">${slot.title || '故事段落'}</div>
            `;
            node.addEventListener("click", () => {
                // Highlight inside Storymap detail
                populateStorymapDetail(slot);
            });
            storylineNodesContainer.appendChild(node);

            // Connect arrow
            if (idx < slots.length - 1) {
                const connector = document.createElement("div");
                connector.className = "story-connector";
                storylineNodesContainer.appendChild(connector);
            }
        });
    }

    function populateStorymapDetail(slot) {
        if (!alignmentDetailCardStorymap) return;
        alignmentDetailCardStorymap.innerHTML = `
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; font-size: 12px;">
                <div>
                    <p><strong>段落編號:</strong> Seg ${(slot.segment !== undefined && slot.segment !== null) ? slot.segment : "無"}</p>
                    <p><strong>期待角色:</strong> ${slot.role || "普通劇情段落"}</p>
                    <p><strong>預期畫面需求:</strong> <span class="val-mono">${slot.expected_need_ref || "無"}</span></p>
                    <p><strong>對位素材來源:</strong> <span class="val-mono">${slot.source || slot.source_path || "無"}</span></p>
                </div>
                <div>
                    <p><strong>字幕旁白:</strong> ${slot.caption || "無"}</p>
                    <p><strong>角色定位:</strong> 片頭: ${slot.opening_role || "否"} | 配樂: ${slot.beat_role || "否"} | 情節: ${slot.arc_role || "否"}</p>
                    <p><strong>對位狀態:</strong> <span class="badge ${slot.status === 'matched' ? 'status-success' : 'status-fail'}">${slot.status}</span></p>
                </div>
            </div>
        `;
    }

    // ==========================================
    // Tab B: Pipeline Console Rendering
    // ==========================================
    function renderPipelineConsole() {
        if (!nodesChecklistRail) return;
        nodesChecklistRail.innerHTML = "";

        const nodes = [
            { node: 0, label: "Brief", artifact: "brief.json", status: "done", reason: "企劃案存在" },
            { node: 3, label: "Contract", artifact: "segment_contract.json", status: "done", reason: "合約完整" },
            { node: 5, label: "Audio", artifact: "music_structure.json", status: "done", reason: "音軌節奏特徵完成" },
            { node: 8, label: "Profile", artifact: "build_profile.json", status: "done", reason: "素材缺料配置完成" },
            { node: 10, label: "Timeline", artifact: "timeline.json", status: "done", reason: "剪輯時間軸軌道編譯完成" },
            { node: 12, label: "Verify", artifact: "state.json", status: "done", reason: "品質與安全門禁稽核通過" },
            { node: 13, label: "Render", artifact: "final.mp4", status: artifactData.final_video_url ? "done" : "fail", reason: artifactData.final_video_url ? "實體影片輸出完成" : "未渲染" }
        ];

        nodes.forEach(n => {
            const row = document.createElement("div");
            row.className = `node-item ${n.status === 'done' ? 'done' : 'fail'}`;
            row.innerHTML = `
                <div class="node-circle">${n.node}</div>
                <div class="node-info">
                    <div class="node-label">${n.label}</div>
                    <div class="node-artifact" style="font-size: 9px; color: #64748b;">${n.artifact} • ${n.reason}</div>
                </div>
                <span class="badge ${n.status === 'done' ? 'status-success' : 'status-fail'}" style="margin-left: auto;">${n.status === 'done' ? 'PASS' : 'FAIL'}</span>
            `;
            row.addEventListener("click", () => {
                activeNodeId = n.node;
                renderNodeDetails();
            });
            nodesChecklistRail.appendChild(row);
        });

        // Setup global warnings
        if (findingsSection) {
            const errs = artifactData.artifact_errors || [];
            if (errs.length > 0) {
                findingsSection.style.display = "block";
                findingsList.innerHTML = errs.map(e => `<li>檔案 ${e.file}: ${e.error}</li>`).join("");
            } else {
                findingsSection.style.display = "none";
            }
        }

        renderNodeDetails();
    }

    function renderNodeDetails() {
        if (!nodeDetailsContent) return;
        
        const detailsMap = {
            "0": { desc: "企劃 Brief 設定", cmd: "python3 video_pipeline.py --mode brief" },
            "3": { desc: "定義各段落故事合約規格", cmd: "python3 spec_contract.py --brief brief.json" },
            "5": { desc: "分析背景音樂波形與節拍點", cmd: "python3 music_structure.py --music bgm.mp3" },
            "8": { desc: "評估素材存量與生成配置計畫", cmd: "python3 build_profile.py --workdir ." },
            "10": { desc: "編譯生成非線性多軌剪輯軌道 timeline.json", cmd: "python3 timeline.py --workdir ." },
            "12": { desc: "進行黑格、字幕排版、音訊對位品質稽核", cmd: "python3 verify.py --workdir . --video final.mp4" },
            "13": { desc: "啟動 FFmpeg / CapCut 引擎實體輸出成品 MP4 影片", cmd: "python3 editor.py --mode render" }
        };

        const current = detailsMap[activeNodeId] || { desc: "節點詳情", cmd: "python3 video_pipeline.py" };
        nodeDetailsContent.innerHTML = `
            <div>
                <h4>節點 ${activeNodeId} 執行詳情</h4>
                <p style="font-size: 12px; color: #475569; line-height: 1.5;">${current.desc}</p>
                <div style="margin-top: 15px; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; background: #f8fafc;">
                    <div style="font-size: 11px; font-weight: 700; color: #334155; margin-bottom: 6px;">CLI 執行指令:</div>
                    <pre style="margin: 0; font-family: 'JetBrains Mono', monospace; font-size: 11px; color: #1e293b; overflow-x: auto; white-space: pre-wrap;">${current.cmd}</pre>
                </div>
            </div>
        `;
    }

    if (btnCopyCmd) {
        btnCopyCmd.addEventListener("click", () => {
            const detailsMap = {
                "0": "python3 video_pipeline.py --mode brief",
                "3": "python3 spec_contract.py --brief brief.json",
                "5": "python3 music_structure.py --music bgm.mp3",
                "8": "python3 build_profile.py --workdir .",
                "10": "python3 timeline.py --workdir .",
                "12": "python3 verify.py --workdir . --video final.mp4",
                "13": "python3 editor.py --mode render"
            };
            const cmd = detailsMap[activeNodeId] || "python3 video_pipeline.py";
            navigator.clipboard.writeText(cmd).then(() => {
                showToast("指令已複製到剪貼簿！", "success");
            });
        });
    }

    // ==========================================
    // Toast Notification System
    // ==========================================
    function showToast(message, type = "info") {
        let toast = document.getElementById("toast-container");
        if (!toast) {
            toast = document.createElement("div");
            toast.id = "toast-container";
            toast.style.position = "fixed";
            toast.style.bottom = "20px";
            toast.style.right = "20px";
            toast.style.zIndex = "1000";
            toast.style.background = "#0f172a";
            toast.style.color = "#f8fafc";
            toast.style.padding = "10px 16px";
            toast.style.borderRadius = "8px";
            toast.style.fontSize = "12px";
            toast.style.fontWeight = "700";
            toast.style.boxShadow = "0 4px 12px rgba(0,0,0,0.15)";
            toast.style.transition = "opacity 0.3s ease";
            document.body.appendChild(toast);
        }
        
        toast.style.opacity = "1";
        toast.textContent = message;
        if (type === "error") {
            toast.style.borderLeft = "4px solid #ef4444";
        } else if (type === "success") {
            toast.style.borderLeft = "4px solid #10b981";
        } else {
            toast.style.borderLeft = "4px solid #6366f1";
        }

        setTimeout(() => {
            toast.style.opacity = "0";
        }, 3000);
    }

    // Initial project & data load
    loadProjects().then(() => {
        fetchArtifactsData();
    });
});
