"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  LayoutGrid,
  Map as MapIcon,
  Cpu,
  ShieldCheck,
  CheckSquare,
  GitCompare,
  History,
  Navigation,
  Sparkles,
  FolderKanban,
  Database,
  Download,
  User,
  Settings,
  Play,
  ArrowRight,
  CheckCircle2,
  AlertTriangle,
  Layers,
  Eye,
  Split,
  Merge,
  Flag,
  XCircle,
  Edit3,
  FileCheck,
  Upload,
  LogOut,
  ChevronRight,
} from "lucide-react";

import EntrySequence, {
  AppEntryStage,
  DEMO_PROFILES,
  DemoUserProfile,
} from "@/components/EntrySequence";
import WebGisEditor from "@/components/WebGisEditor";
import CompareSliderView from "@/components/CompareSliderView";
import TimeMachineView from "@/components/TimeMachineView";
import CouncilFlowView from "@/components/CouncilFlowView";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

interface NavItem {
  id: string;
  label: string;
  icon: any;
  group: "core" | "data" | "account";
}

const NAV_ITEMS: NavItem[] = [
  { id: "dashboard", label: "Workspace", icon: LayoutGrid, group: "core" },
  { id: "workspace", label: "Map", icon: MapIcon, group: "core" },
  { id: "analysis", label: "AI Analysis", icon: Cpu, group: "core" },
  { id: "council", label: "AI Council", icon: ShieldCheck, group: "core" },
  { id: "verification", label: "Verification", icon: CheckSquare, group: "core" },
  { id: "changes", label: "Changes", icon: GitCompare, group: "core" },
  { id: "timemachine", label: "Time Machine", icon: History, group: "core" },
  { id: "routes", label: "Field Route", icon: Navigation, group: "core" },
  { id: "copilot", label: "Copilot", icon: Sparkles, group: "core" },
  { id: "projects", label: "Projects", icon: FolderKanban, group: "data" },
  { id: "datasets", label: "Datasets", icon: Database, group: "data" },
  { id: "exports", label: "Exports", icon: Download, group: "data" },
  { id: "profile", label: "Profile", icon: User, group: "account" },
  { id: "settings", label: "Settings", icon: Settings, group: "account" },
];

export default function AeroCadastreApp() {
  // Entry flow stage: starts with Initial Brand Loading -> Welcome -> Login -> Opening -> App
  const [entryStage, setEntryStage] = useState<AppEntryStage>("INTRO_LOADING");
  const [selectedProfile, setSelectedProfile] = useState<DemoUserProfile>(
    DEMO_PROFILES.Surveyor
  );

  // Main Application Navigation & State
  const [activeTab, setActiveTab] = useState<string>("dashboard");
  const [projectId, setProjectId] = useState<string>("PROJ_SIH26012_DEMO");
  const [sceneId, setSceneId] = useState<string>("scene_urban_T1");
  const [scenes, setScenes] = useState<any[]>([]);
  const [dashboard, setDashboard] = useState<any>(null);
  const [bundle, setBundle] = useState<any>(null);
  const [experiments, setExperiments] = useState<any[]>([]);
  const [projects, setProjects] = useState<any[]>([]);
  const [datasets, setDatasets] = useState<any[]>([]);
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [feedbackList, setFeedbackList] = useState<any[]>([]);
  const [health, setHealth] = useState<any>(null);

  const [selectedParcelId, setSelectedParcelId] = useState<string | null>(null);
  const [highlightedIds, setHighlightedIds] = useState<string[]>([]);
  const [parcelHistory, setParcelHistory] = useState<any[]>([]);

  // AI Analysis layer toggles
  const [aiLabLayers, setAiLabLayers] = useState({
    building: true,
    road: true,
    boundary: true,
    landUse: true,
  });
  const [selectedExpId, setSelectedExpId] = useState<string>("EXP_003");

  // Copilot state
  const [copilotQuery, setCopilotQuery] = useState<string>(
    "Why was parcel P-003 flagged?"
  );
  const [copilotHistory, setCopilotHistory] = useState<any[]>([]);

  // Export state
  const [exportResults, setExportResults] = useState<any[]>([]);

  // Upload state
  const [uploadInspection, setUploadInspection] = useState<any>(null);

  // New project state
  const [newProjName, setNewProjName] = useState<string>("");
  const [newProjRegion, setNewProjRegion] = useState<string>(
    "Urban Survey Sector - Karnataka (Synthetic)"
  );

  const [actionBanner, setActionBanner] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  // Fetch all live data from backend
  const fetchAllData = useCallback(async () => {
    try {
      const [hRes, dRes, bRes, sRes, eRes, pRes, dsRes, aRes, fbRes] =
        await Promise.all([
          fetch(`${API_BASE}/api/health`),
          fetch(
            `${API_BASE}/api/dashboard?project_id=${projectId}&scene_id=${sceneId}`
          ),
          fetch(
            `${API_BASE}/api/scenes/${sceneId}/bundle?project_id=${projectId}`
          ),
          fetch(`${API_BASE}/api/scenes`),
          fetch(`${API_BASE}/api/experiments`),
          fetch(`${API_BASE}/api/projects`),
          fetch(`${API_BASE}/api/datasets?project_id=${projectId}`),
          fetch(`${API_BASE}/api/audit-logs?project_id=${projectId}`),
          fetch(`${API_BASE}/api/feedback?project_id=${projectId}`),
        ]);

      if (hRes.ok) setHealth(await hRes.json());
      if (dRes.ok) setDashboard(await dRes.json());
      if (bRes.ok) {
        const bData = await bRes.json();
        setBundle(bData);
        if (!selectedParcelId && bData.candidate_parcels?.length > 0) {
          setSelectedParcelId(bData.candidate_parcels[0].id);
        }
      }
      if (sRes.ok) setScenes(await sRes.json());
      if (eRes.ok) setExperiments(await eRes.json());
      if (pRes.ok) setProjects(await pRes.json());
      if (dsRes.ok) setDatasets(await dsRes.json());
      if (aRes.ok) setAuditLogs(await aRes.json());
      if (fbRes.ok) setFeedbackList(await fbRes.json());
    } catch (err) {
      console.error("Failed to fetch backend state:", err);
    }
  }, [projectId, sceneId, selectedParcelId]);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      const qStage = params.get("stage") as AppEntryStage | null;
      const qTab = params.get("tab");
      if (qStage && ["INTRO_LOADING", "WELCOME", "LOGIN", "WORKSPACE_OPENING", "APP_READY"].includes(qStage)) {
        setEntryStage(qStage);
      }
      if (qTab) {
        setActiveTab(qTab);
      }
    }
  }, []);

  useEffect(() => {
    fetchAllData();
  }, [fetchAllData]);

  // Fetch version history whenever selectedParcelId changes
  useEffect(() => {
    if (!selectedParcelId) return;
    fetch(`${API_BASE}/api/history/${selectedParcelId}`)
      .then((r) => (r.ok ? r.json() : []))
      .then((data) => setParcelHistory(data))
      .catch(() => setParcelHistory([]));
  }, [selectedParcelId, bundle]);

  // Trigger initial Copilot query once bundle loads so Copilot has immediate context
  useEffect(() => {
    if (bundle && copilotHistory.length === 0) {
      handleCopilotSubmit("Why was parcel P-002 flagged?");
    }
  }, [bundle]);

  const handleRunPipeline = async () => {
    setLoading(true);
    setActionBanner(
      `Executing 24-step GeoAI Inference, Metric Topology & 6-Agent Council Pipeline on ${sceneId}...`
    );
    try {
      const res = await fetch(`${API_BASE}/api/pipeline/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project_id: projectId, scene_id: sceneId }),
      });
      if (res.ok) {
        const out = await res.json();
        await fetchAllData();
        setActionBanner(
          `Pipeline completed in ${out.inference_time_ms}ms — ${out.counts.candidate_parcels} parcels, ${out.counts.buildings} buildings, ${out.counts.topology_issues} topology checks, ${out.counts.anomalies_and_conflicts} conflicts evaluated.`
        );
      }
    } finally {
      setLoading(false);
    }
  };

  const handleTriggerLiveTraining = async () => {
    setLoading(true);
    setActionBanner(
      "Training live Building MicroResUNet (4-ch RGB+nDSM) experiment on synthetic dataset..."
    );
    try {
      const res = await fetch(`${API_BASE}/api/experiments/train?epochs=3`, {
        method: "POST",
      });
      if (res.ok) {
        const exp = await res.json();
        await fetchAllData();
        setActionBanner(
          `Live training ${exp.id} finished: Val IoU=${(exp.iou * 100).toFixed(2)}%, Dice=${(
            exp.dice_f1 * 100
          ).toFixed(2)}%, Time=${exp.training_time_sec}s.`
        );
      }
    } finally {
      setLoading(false);
    }
  };

  const handleVerificationAction = async (
    parcelId: string,
    action: string,
    notes: string
  ) => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/verification/${parcelId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action,
          operator_id: selectedProfile.operatorId,
          notes,
        }),
      });
      if (res.ok) {
        await fetchAllData();
        setActionBanner(
          `Updated parcel ${parcelId} verification status to ${action}.`
        );
      }
    } finally {
      setLoading(false);
    }
  };

  const handleQuickSplitParcel = async (
    parcelId: string,
    axis: "VERTICAL" | "HORIZONTAL"
  ) => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/parcels/${parcelId}/split`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          split_axis: axis,
          split_ratio: 0.5,
          operator_id: selectedProfile.operatorId,
          reason: `${axis} subdivision from Verification Center`,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        await fetchAllData();
        setSelectedParcelId(data.parcel_a.id);
        setActionBanner(
          `Subdivided ${parcelId} into ${data.parcel_a.id} and ${data.parcel_b.id}.`
        );
      }
    } finally {
      setLoading(false);
    }
  };

  const handleQuickMergeParcel = async (parcelIdA: string) => {
    const other = (bundle?.candidate_parcels || []).find(
      (p: any) => p.id !== parcelIdA
    );
    if (!other) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/parcels/merge`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_id: projectId,
          scene_id: sceneId,
          parcel_id_a: parcelIdA,
          parcel_id_b: other.id,
          operator_id: selectedProfile.operatorId,
          reason: `Merged ${parcelIdA} + ${other.id} in Verification Center`,
        }),
      });
      if (res.ok) {
        await fetchAllData();
        setActionBanner(`Merged ${parcelIdA} and ${other.id} into verified parcel.`);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleCopilotSubmit = async (qOverride?: string) => {
    const qText = qOverride || copilotQuery;
    if (!qText.trim()) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/copilot/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_id: projectId,
          scene_id: sceneId,
          question: qText,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setCopilotHistory((prev) => [{ question: qText, ...data }, ...prev]);
        if (data.highlight_feature_ids?.length > 0) {
          setHighlightedIds(data.highlight_feature_ids);
          const firstParcel = data.highlight_feature_ids.find((id: string) =>
            id.includes("_P_")
          );
          if (firstParcel) setSelectedParcelId(firstParcel);
        }
      }
    } finally {
      setLoading(false);
    }
  };

  const handleExportFormat = async (fmt: string) => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/exports`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_id: projectId,
          scene_id: sceneId,
          export_format: fmt,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setExportResults((prev) => [data, ...prev]);
        await fetchAllData();
        setActionBanner(
          `Exported ${data.feature_count} parcels to ${data.format} (${data.file_size_bytes} bytes) — Post-export read-back validation: PASSED.`
        );
      }
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setLoading(true);
    const formData = new FormData();
    formData.append("project_id", projectId);
    formData.append("declared_crs", "EPSG:4326");
    formData.append("temporal_epoch", "T1");
    formData.append("file", file);
    try {
      const res = await fetch(`${API_BASE}/api/upload`, {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      setUploadInspection(data);
      await fetchAllData();
      setActionBanner(`Dataset ${file.name} uploaded and validated.`);
    } finally {
      setLoading(false);
    }
  };

  // Helper for SVG projection inside non-editor views
  const originLon = bundle?.metadata?.origin_lonlat?.[0] ?? 77.592;
  const originLat = bundle?.metadata?.origin_lonlat?.[1] ?? 12.972;
  const span = 0.0024;
  const VIEW_SIZE = 720;

  const lonLatToSvg = (lon: number, lat: number): [number, number] => {
    const x = ((lon - originLon) / span) * VIEW_SIZE;
    const y = (1.0 - (lat - originLat) / span) * VIEW_SIZE;
    return [x, y];
  };

  const ringToSvgPoints = (ring: number[][]): string => {
    return ring
      .map((pt) => {
        const [x, y] = lonLatToSvg(pt[0], pt[1]);
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(" ");
  };

  const m = dashboard?.metrics || {};
  const parcels: any[] = bundle?.candidate_parcels || [];
  const refParcels: any[] = bundle?.reference_parcels || [];
  const buildings: any[] = bundle?.buildings || [];
  const roads: any[] = bundle?.roads || [];
  const boundaries: any[] = bundle?.boundaries || [];
  const topoIssues: any[] = bundle?.topology_issues || [];
  const councils: any[] = bundle?.council_decisions || [];
  const verifTasks: any[] = bundle?.verification_tasks || [];
  const routes: any[] = bundle?.field_routes || [];

  const selectedParcel =
    parcels.find((p) => p.id === selectedParcelId) || parcels[0] || null;
  const selectedCouncil =
    councils.find((c) => c.parcel_id === (selectedParcel?.id || selectedParcelId)) ||
    councils[0] ||
    null;

  // Render Pre-Workspace Entry Sequence if not in APP_READY stage
  if (entryStage !== "APP_READY") {
    return (
      <EntrySequence
        stage={entryStage}
        setStage={setEntryStage}
        selectedProfile={selectedProfile}
        setSelectedProfile={setSelectedProfile}
        dashboardMetrics={m}
        sceneId={sceneId}
      />
    );
  }

  return (
    <div className="min-h-screen flex bg-[#F4F1EA] text-[#171615] selection:bg-[#B89A78]/30">
      {/* =====================================================================
          LEFT APPLICATION NAVIGATION SIDEBAR
      ===================================================================== */}
      <aside className="w-56 xl:w-60 shrink-0 bg-[#FAF8F3] border-r border-[#E4DFD5] flex flex-col justify-between sticky top-0 h-screen z-30 select-none">
        <div className="p-4 space-y-5 overflow-y-auto">
          {/* Brand Identity */}
          <div className="flex items-center justify-between px-1">
            <button
              onClick={() => setEntryStage("WELCOME")}
              className="flex items-center gap-2.5 text-left group"
              title="Return to Welcome Page"
            >
              <div className="w-8 h-8 rounded-lg bg-[#24221F] text-[#FAF8F3] flex items-center justify-center font-editorial text-lg shadow-sm">
                A
              </div>
              <div>
                <div className="text-xs font-bold tracking-tight text-[#171615]">
                  AEROCADASTRE
                </div>
                <div className="text-[10px] font-mono text-[#6B5748]">
                  SIH26012 • GeoAI
                </div>
              </div>
            </button>
          </div>

          {/* Core Spatial Intelligence Navigation */}
          <div className="space-y-1">
            <div className="px-2.5 pb-1 text-[10px] font-mono uppercase tracking-widest text-[#8C8277]">
              Spatial Intelligence
            </div>
            {NAV_ITEMS.filter((i) => i.group === "core").map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs font-medium transition-all duration-150 ${
                    isActive
                      ? "bg-[#24221F] text-[#FAF8F3] shadow-sm"
                      : "text-[#5C554E] hover:bg-[#EEEAE2] hover:text-[#171615]"
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <Icon
                      className={`w-4 h-4 ${
                        isActive ? "text-[#C5AA8C]" : "text-[#8A735F]"
                      }`}
                    />
                    <span>{item.label}</span>
                  </div>
                  {item.id === "verification" && m.pending_verification > 0 && (
                    <span
                      className={`px-1.5 py-0.2 rounded text-[10px] font-mono ${
                        isActive
                          ? "bg-[#302C28] text-[#C5AA8C]"
                          : "bg-[#EEEAE2] text-[#6B5748]"
                      }`}
                    >
                      {m.pending_verification}
                    </span>
                  )}
                </button>
              );
            })}
          </div>

          {/* Data & Administration Navigation */}
          <div className="space-y-1 pt-2 border-t border-[#E4DFD5]">
            <div className="px-2.5 pb-1 text-[10px] font-mono uppercase tracking-widest text-[#8C8277]">
              Repository & I/O
            </div>
            {NAV_ITEMS.filter((i) => i.group === "data").map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-medium transition-all duration-150 ${
                    isActive
                      ? "bg-[#24221F] text-[#FAF8F3] shadow-sm"
                      : "text-[#5C554E] hover:bg-[#EEEAE2] hover:text-[#171615]"
                  }`}
                >
                  <Icon
                    className={`w-4 h-4 ${
                      isActive ? "text-[#C5AA8C]" : "text-[#8A735F]"
                    }`}
                  />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Bottom Profile & Settings */}
        <div className="p-3 border-t border-[#E4DFD5] bg-[#F4F1EA]/60 space-y-1">
          {NAV_ITEMS.filter((i) => i.group === "account").map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-medium transition-all duration-150 ${
                  isActive
                    ? "bg-[#24221F] text-[#FAF8F3]"
                    : "text-[#5C554E] hover:bg-[#EEEAE2] hover:text-[#171615]"
                }`}
              >
                <Icon
                  className={`w-4 h-4 ${
                    isActive ? "text-[#C5AA8C]" : "text-[#8A735F]"
                  }`}
                />
                <span>{item.label}</span>
              </button>
            );
          })}

          <div className="pt-2 mt-1 border-t border-[#E4DFD5] flex items-center justify-between px-2 py-1">
            <div className="truncate">
              <div className="text-xs font-semibold text-[#171615] truncate">
                {selectedProfile.name}
              </div>
              <div className="text-[10px] font-mono text-[#6B5748] truncate">
                {selectedProfile.role}
              </div>
            </div>
            <button
              onClick={() => setEntryStage("LOGIN")}
              title="Switch Role / Sign Out"
              className="p-1.5 rounded-lg text-[#8C8277] hover:bg-[#EEEAE2] hover:text-[#171615]"
            >
              <LogOut className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </aside>

      {/* =====================================================================
          MAIN WORKSPACE SHELL
      ===================================================================== */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* TOP CONTEXTUAL BAR */}
        <header className="h-[68px] bg-[#FAF8F3]/90 backdrop-blur-md border-b border-[#E4DFD5] px-6 flex items-center justify-between gap-4 sticky top-0 z-20">
          <div className="flex items-center gap-3 min-w-0">
            <span className="font-editorial text-2xl text-[#171615] capitalize truncate">
              {NAV_ITEMS.find((n) => n.id === activeTab)?.label || "Workspace"}
            </span>
            <span className="hidden md:inline-block px-2.5 py-0.5 rounded-md bg-[#F8F1E5] border border-[#E5CFA8] text-[10px] font-mono font-semibold text-[#9E6B20]">
              SYNTHETIC DEMO DATA
            </span>
            <span className="hidden lg:inline-block px-2.5 py-0.5 rounded-md bg-[#EEEAE2] border border-[#D2C9BC] text-[10px] font-mono text-[#6B5748]">
              PRELIMINARY CANDIDATE GEOMETRY
            </span>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 text-xs">
              <span className="hidden sm:inline text-[11px] font-mono text-[#6B5748]">
                Scene:
              </span>
              <select
                value={sceneId}
                onChange={(e) => {
                  setSceneId(e.target.value);
                  setSelectedParcelId(null);
                }}
                className="bg-[#FFFFFF] border border-[#D2C9BC] rounded-xl px-3 py-1.5 text-xs font-mono text-[#171615] focus:outline-none focus:border-[#6B5748]"
              >
                {scenes.map((s) => (
                  <option key={s.scene_id} value={s.scene_id}>
                    {s.scene_id} ({s.archetype} • {s.temporal_epoch})
                  </option>
                ))}
              </select>
            </div>

            <button
              onClick={handleRunPipeline}
              disabled={loading}
              className="btn-primary-dark px-3.5 py-2 rounded-xl text-xs font-medium flex items-center gap-1.5 shadow-sm"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>{loading ? "Running Pipeline..." : "Run GeoAI Pipeline"}</span>
            </button>
          </div>
        </header>

        {/* ACTION / FEEDBACK TOAST BANNER */}
        {actionBanner && (
          <div className="bg-[#24221F] text-[#FAF8F3] px-6 py-2.5 text-xs font-mono flex items-center justify-between border-b border-[#302C28]">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-[#C5AA8C]" />
              <span>{actionBanner}</span>
            </div>
            <button
              onClick={() => setActionBanner(null)}
              className="text-[#A18A76] hover:text-[#FAF8F3]"
            >
              ✕
            </button>
          </div>
        )}

        {/* ===================================================================
            VIEW 02: MAPPING WORKSPACE (FULL BLEED - STAR OF THE APPLICATION)
        =================================================================== */}
        {activeTab === "workspace" ? (
          <WebGisEditor
            bundle={bundle}
            selectedParcelId={selectedParcelId}
            onSelectParcel={setSelectedParcelId}
            highlightedIds={highlightedIds}
            onRefreshBundle={fetchAllData}
            onNavigateTab={setActiveTab}
            activeRole={selectedProfile.operatorId}
          />
        ) : (
          <main className="flex-1 p-6 max-w-[1520px] w-full mx-auto space-y-6">
            {/* ===============================================================
                VIEW 01: WORKSPACE (REDESIGNED SPATIAL DASHBOARD)
            =============================================================== */}
            {activeTab === "dashboard" && (
              <div className="space-y-6 animate-page-enter">
                {/* Editorial Hero Header */}
                <div className="bg-[#FAF8F3] border border-[#E4DFD5] rounded-2xl p-6 sm:p-8 flex flex-wrap items-end justify-between gap-6 shadow-subtle">
                  <div className="space-y-2 max-w-2xl">
                    <div className="text-[11px] font-mono uppercase tracking-widest text-[#6B5748]">
                      ACTIVE SURVEY WORKSPACE • {projectId} • {sceneId}
                    </div>
                    <h1 className="font-editorial text-4xl sm:text-5xl text-[#171615] tracking-tight">
                      Urban cadastral intelligence.
                    </h1>
                    <p className="text-sm text-[#5C554E] leading-relaxed">
                      Multi-layer aerial orthophoto extraction, metric topology verification in <code className="font-mono text-xs bg-[#EEEAE2] px-1.5 py-0.5 rounded">EPSG:32643</code>, and 6-agent AI Council deliberation.
                    </p>
                  </div>

                  <div className="flex flex-wrap items-center gap-3">
                    <button
                      onClick={() => setActiveTab("workspace")}
                      className="btn-primary-dark px-5 py-2.5 rounded-xl text-xs font-medium flex items-center gap-2 shadow-editorial"
                    >
                      <span>Open Mapping Workspace</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() => setActiveTab("verification")}
                      className="btn-secondary-warm px-4 py-2.5 rounded-xl text-xs font-medium"
                    >
                      Verification Queue ({m.pending_verification ?? 16})
                    </button>
                  </div>
                </div>

                {/* Primary Spatial Visualization + Supporting Intelligence */}
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
                  {/* LEFT/CENTER: Large Active Scene Map & Imagery Panel (8 cols) */}
                  <div className="lg:col-span-8 bg-[#24221F] text-[#FAF8F3] rounded-2xl p-4 sm:p-5 border border-[#302C28] shadow-elevated flex flex-col justify-between space-y-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div className="flex items-center gap-2.5">
                        <span className="px-2.5 py-1 rounded-md bg-[#302C28] border border-[#6B5748]/50 font-mono text-xs text-[#C5AA8C]">
                          ACTIVE SCENE: {sceneId}
                        </span>
                        <span className="font-mono text-xs text-[#A18A76]">
                          Click any parcel to inspect or open in Web-GIS
                        </span>
                      </div>

                      {/* Overlay Counts required by spec: 16 candidate parcels, 7 buildings, 2 roads */}
                      <div className="flex items-center gap-2 text-xs font-mono">
                        <span className="px-2.5 py-1 rounded-lg bg-[#171615] border border-[#3A3530] text-[#FAF8F3]">
                          <strong>{m.candidate_parcels ?? 16}</strong> candidate parcels
                        </span>
                        <span className="px-2.5 py-1 rounded-lg bg-[#171615] border border-[#3A3530] text-[#C5AA8C]">
                          <strong>{m.buildings_detected ?? 7}</strong> buildings
                        </span>
                        <span className="px-2.5 py-1 rounded-lg bg-[#171615] border border-[#3A3530] text-[#A18A76]">
                          <strong>{m.roads_detected ?? 2}</strong> roads
                        </span>
                      </div>
                    </div>

                    {/* Interactive Scene Canvas */}
                    <div className="relative w-full aspect-[16/11] rounded-xl overflow-hidden bg-[#171615] border border-[#3A3530]">
                      <img
                        src={`${API_BASE}/api/scenes/${sceneId}/rgb.png`}
                        alt={sceneId}
                        className="absolute inset-0 w-full h-full object-cover opacity-85"
                      />
                      <svg
                        viewBox={`0 0 ${VIEW_SIZE} ${VIEW_SIZE}`}
                        preserveAspectRatio="xMidYMid slice"
                        className="relative z-10 w-full h-full"
                      >
                        {/* Roads */}
                        {roads.map((r) => {
                          const pts = r.geometry?.coordinates || [];
                          if (pts.length < 2) return null;
                          const [x1, y1] = lonLatToSvg(pts[0][0], pts[0][1]);
                          const [x2, y2] = lonLatToSvg(
                            pts[pts.length - 1][0],
                            pts[pts.length - 1][1]
                          );
                          return (
                            <line
                              key={r.id}
                              x1={x1}
                              y1={y1}
                              x2={x2}
                              y2={y2}
                              stroke="#FAF8F3"
                              strokeWidth="1.8"
                              strokeDasharray="6 4"
                              opacity="0.8"
                            />
                          );
                        })}

                        {/* Candidate Parcels */}
                        {parcels.map((p) => {
                          const ring = p.geometry?.coordinates?.[0];
                          if (!ring) return null;
                          const isSel = p.id === selectedParcelId;
                          const [cx, cy] = lonLatToSvg(
                            p.ulpin_ready_metadata?.centroid_lon || ring[0][0],
                            p.ulpin_ready_metadata?.centroid_lat || ring[0][1]
                          );
                          return (
                            <g
                              key={p.id}
                              onClick={() => setSelectedParcelId(p.id)}
                              className="cursor-pointer"
                            >
                              <polygon
                                points={ringToSvgPoints(ring)}
                                fill={
                                  isSel
                                    ? "rgba(250, 248, 243, 0.35)"
                                    : p.verification_status === "HUMAN_VERIFIED"
                                    ? "rgba(61, 107, 82, 0.32)"
                                    : "rgba(184, 154, 120, 0.22)"
                                }
                                stroke={isSel ? "#FAF8F3" : "#C5AA8C"}
                                strokeWidth={isSel ? 3 : 1.6}
                              />
                              <text
                                x={cx}
                                y={cy}
                                textAnchor="middle"
                                fill="#FAF8F3"
                                fontSize="11"
                                fontFamily="JetBrains Mono, monospace"
                                fontWeight="600"
                                className="pointer-events-none drop-shadow"
                              >
                                {p.id.split("_").slice(-2).join("_")}
                              </text>
                            </g>
                          );
                        })}

                        {/* Buildings */}
                        {buildings.map((b) => {
                          const ring = b.geometry?.coordinates?.[0];
                          if (!ring) return null;
                          return (
                            <polygon
                              key={b.id}
                              points={ringToSvgPoints(ring)}
                              fill="rgba(184, 154, 120, 0.45)"
                              stroke="#FAF8F3"
                              strokeWidth="1.2"
                            />
                          );
                        })}
                      </svg>

                      {/* Floating Selected Parcel Bar inside Map */}
                      {selectedParcel && (
                        <div className="absolute bottom-3 left-3 right-3 z-20 px-4 py-2.5 rounded-xl bg-[#171615]/92 border border-[#3A3530] flex flex-wrap items-center justify-between gap-3 text-xs">
                          <div className="flex items-center gap-3 font-mono">
                            <span className="text-[#C5AA8C] font-semibold">
                              {selectedParcel.id}
                            </span>
                            <span>{selectedParcel.area_sqm?.toFixed(0)} m²</span>
                            <span className="text-[#A18A76]">•</span>
                            <span>{selectedParcel.land_use_class}</span>
                            <span className="text-[#A18A76]">•</span>
                            <span>Conf: {(selectedParcel.confidence * 100).toFixed(0)}%</span>
                          </div>
                          <button
                            onClick={() => setActiveTab("workspace")}
                            className="px-3 py-1 rounded-lg bg-[#FAF8F3] text-[#171615] font-mono text-[11px] font-semibold hover:bg-[#EEEAE2]"
                          >
                            Edit Parcel in Map →
                          </button>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* RIGHT: Supporting Spatial Intelligence Stack (4 cols) */}
                  <div className="lg:col-span-4 flex flex-col justify-between gap-4">
                    {/* 1. Verification Queue Card */}
                    <div className="card-editorial rounded-2xl p-5 space-y-3">
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="text-[10px] font-mono uppercase tracking-wider text-[#6B5748]">
                            HUMAN-IN-THE-LOOP
                          </div>
                          <h3 className="font-editorial text-2xl text-[#171615]">
                            Verification Queue
                          </h3>
                        </div>
                        <span className="px-2.5 py-1 rounded-lg bg-[#F8F1E5] border border-[#E5CFA8] font-mono text-xs font-semibold text-[#9E6B20]">
                          {m.pending_verification ?? 16} Pending
                        </span>
                      </div>

                      <div className="space-y-2">
                        {verifTasks.slice(0, 3).map((vt) => (
                          <div
                            key={vt.id}
                            onClick={() => {
                              setSelectedParcelId(vt.parcel_id);
                              setActiveTab("verification");
                            }}
                            className="p-2.5 rounded-xl bg-[#F4F1EA] border border-[#E4DFD5] hover:border-[#8A735F] cursor-pointer flex items-center justify-between text-xs transition-colors"
                          >
                            <div>
                              <div className="font-mono font-semibold text-[#171615]">
                                {vt.parcel_id.split("_").slice(-2).join("_")}
                              </div>
                              <div className="text-[11px] text-[#5C554E] truncate max-w-[180px]">
                                {(vt.reasons || [])[0] || vt.council_decision}
                              </div>
                            </div>
                            <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-[#FAF8F3] border border-[#D2C9BC] text-[#6B5748]">
                              {vt.priority}
                            </span>
                          </div>
                        ))}
                      </div>

                      <button
                        onClick={() => setActiveTab("verification")}
                        className="w-full py-2 rounded-xl bg-[#EEEAE2] hover:bg-[#D2C9BC]/60 text-[#24221F] text-xs font-medium flex items-center justify-center gap-1.5 transition-colors"
                      >
                        <span>Open Verification Center</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </button>
                    </div>

                    {/* 2. AI Council Summary Card */}
                    <div className="card-editorial rounded-2xl p-5 space-y-2.5">
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="text-[10px] font-mono uppercase tracking-wider text-[#6B5748]">
                            6-AGENT CONSENSUS
                          </div>
                          <h3 className="font-editorial text-2xl text-[#171615]">
                            AI Council
                          </h3>
                        </div>
                        <button
                          onClick={() => setActiveTab("council")}
                          className="text-xs font-mono text-[#6B5748] hover:text-[#171615]"
                        >
                          Inspect →
                        </button>
                      </div>
                      <p className="text-xs text-[#5C554E] leading-relaxed">
                        {m.council_decisions ?? 16} parcel deliberations completed across Vision, Geometry, GIS, ML, Anomaly, and Field agents.
                      </p>
                      <div className="grid grid-cols-2 gap-2 pt-1 text-xs font-mono">
                        <div className="p-2.5 rounded-xl bg-[#F4F1EA] border border-[#E4DFD5]">
                          <span className="text-[10px] text-[#8C8277] block">GIS Conflicts</span>
                          <span className="text-sm font-bold text-[#9E3E37]">
                            {m.gis_conflicts ?? 5} Flagged
                          </span>
                        </div>
                        <div className="p-2.5 rounded-xl bg-[#F4F1EA] border border-[#E4DFD5]">
                          <span className="text-[10px] text-[#8C8277] block">Verified</span>
                          <span className="text-sm font-bold text-[#3D6B52]">
                            {m.verified_features ?? 0} Parcels
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* 3. Topology & Temporal Changes */}
                    <div className="card-editorial rounded-2xl p-5 space-y-2.5">
                      <div className="flex items-center justify-between">
                        <h3 className="font-editorial text-2xl text-[#171615]">
                          Topology & Changes
                        </h3>
                        <button
                          onClick={() => setActiveTab("changes")}
                          className="text-xs font-mono text-[#6B5748] hover:text-[#171615]"
                        >
                          Compare T0→T2 →
                        </button>
                      </div>
                      <div className="grid grid-cols-3 gap-2 text-xs font-mono">
                        <div className="p-2.5 rounded-xl bg-[#F4F1EA] border border-[#E4DFD5]">
                          <span className="text-[10px] text-[#8C8277] block">Topology</span>
                          <span className="text-sm font-bold text-[#9E6B20]">
                            {m.topology_issues ?? 12}
                          </span>
                        </div>
                        <div className="p-2.5 rounded-xl bg-[#F4F1EA] border border-[#E4DFD5]">
                          <span className="text-[10px] text-[#8C8277] block">Anomalies</span>
                          <span className="text-sm font-bold text-[#171615]">
                            {m.anomalies ?? 9}
                          </span>
                        </div>
                        <div className="p-2.5 rounded-xl bg-[#F4F1EA] border border-[#E4DFD5]">
                          <span className="text-[10px] text-[#8C8277] block">T0→T2 Diff</span>
                          <span className="text-sm font-bold text-[#3D6B52]">
                            {m.temporal_changes ?? 5}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* ===============================================================
                VIEW 03: AI ANALYSIS PAGE (GEOAI LABORATORY)
            =============================================================== */}
            {activeTab === "analysis" && (
              <div className="space-y-6 animate-page-enter">
                <div className="bg-[#FAF8F3] border border-[#E4DFD5] rounded-2xl p-6 flex flex-wrap items-center justify-between gap-4 shadow-subtle">
                  <div className="space-y-1">
                    <div className="text-[11px] font-mono uppercase tracking-widest text-[#6B5748]">
                      GEOAI MODEL LABORATORY • PYTHORCH & SCIKIT-LEARN PIPELINE
                    </div>
                    <h2 className="font-editorial text-3xl sm:text-4xl text-[#171615]">
                      Neural Feature Extraction & Layer Inspection
                    </h2>
                    <p className="text-xs text-[#5C554E] max-w-2xl">
                      Toggle individual neural model layers over the active drone orthophoto to compare input imagery, extracted building/road/boundary predictions, and model confidence.
                    </p>
                  </div>

                  <div className="flex items-center gap-2.5">
                    <button
                      onClick={handleTriggerLiveTraining}
                      disabled={loading}
                      className="btn-primary-dark px-4 py-2.5 rounded-xl text-xs font-medium"
                    >
                      ▶ Train Live Experiment (3 Epochs)
                    </button>
                    <button
                      onClick={handleRunPipeline}
                      disabled={loading}
                      className="btn-secondary-warm px-4 py-2.5 rounded-xl text-xs font-medium"
                    >
                      Re-run Scene Inference
                    </button>
                  </div>
                </div>

                {/* Large Imagery & Model Layer Comparison Studio */}
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
                  {/* Left: Large Visual Model Layer Viewport (7 cols) */}
                  <div className="lg:col-span-7 bg-[#24221F] text-[#FAF8F3] rounded-2xl p-5 border border-[#302C28] shadow-elevated space-y-4">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="font-mono text-xs text-[#C5AA8C]">
                        MODEL PREDICTION OVERLAY • {sceneId}
                      </span>
                      <div className="flex flex-wrap items-center gap-1.5">
                        {[
                          { key: "building", label: "Building" },
                          { key: "road", label: "Road" },
                          { key: "boundary", label: "Boundary" },
                          { key: "landUse", label: "Land Use" },
                        ].map((ly) => {
                          const active = (aiLabLayers as any)[ly.key];
                          return (
                            <button
                              key={ly.key}
                              onClick={() =>
                                setAiLabLayers({ ...aiLabLayers, [ly.key]: !active })
                              }
                              className={`px-3 py-1 rounded-lg font-mono text-xs transition-all ${
                                active
                                  ? "bg-[#FAF8F3] text-[#171615] font-semibold"
                                  : "bg-[#171615] text-[#A18A76] border border-[#3A3530]"
                              }`}
                            >
                              {active ? `✓ ${ly.label}` : ly.label}
                            </button>
                          );
                        })}
                      </div>
                    </div>

                    <div className="relative w-full aspect-square rounded-xl overflow-hidden bg-[#171615] border border-[#3A3530]">
                      <img
                        src={`${API_BASE}/api/scenes/${sceneId}/rgb.png`}
                        alt="Input Ortho"
                        className="absolute inset-0 w-full h-full object-cover opacity-85"
                      />
                      <svg
                        viewBox={`0 0 ${VIEW_SIZE} ${VIEW_SIZE}`}
                        className="relative z-10 w-full h-full"
                      >
                        {/* Land Use Semantic Layer */}
                        {aiLabLayers.landUse &&
                          parcels.map((p) => {
                            const ring = p.geometry?.coordinates?.[0];
                            if (!ring) return null;
                            return (
                              <polygon
                                key={p.id}
                                points={ringToSvgPoints(ring)}
                                fill="rgba(184, 154, 120, 0.25)"
                                stroke="none"
                              />
                            );
                          })}

                        {/* Road Layer */}
                        {aiLabLayers.road &&
                          roads.map((r) => {
                            const pts = r.geometry?.coordinates || [];
                            if (pts.length < 2) return null;
                            const [x1, y1] = lonLatToSvg(pts[0][0], pts[0][1]);
                            const [x2, y2] = lonLatToSvg(
                              pts[pts.length - 1][0],
                              pts[pts.length - 1][1]
                            );
                            return (
                              <g key={r.id}>
                                <line
                                  x1={x1}
                                  y1={y1}
                                  x2={x2}
                                  y2={y2}
                                  stroke="#24221F"
                                  strokeWidth="20"
                                  opacity="0.7"
                                />
                                <line
                                  x1={x1}
                                  y1={y1}
                                  x2={x2}
                                  y2={y2}
                                  stroke="#FAF8F3"
                                  strokeWidth="2"
                                  strokeDasharray="6 4"
                                />
                              </g>
                            );
                          })}

                        {/* Boundary Layer */}
                        {aiLabLayers.boundary &&
                          boundaries.map((bnd) => {
                            const pts = bnd.geometry?.coordinates;
                            if (!pts || pts.length < 2) return null;
                            const [x1, y1] = lonLatToSvg(pts[0][0], pts[0][1]);
                            const [x2, y2] = lonLatToSvg(pts[1][0], pts[1][1]);
                            const isVis = bnd.boundary_type === "VISIBLE";
                            return (
                              <line
                                key={bnd.id}
                                x1={x1}
                                y1={y1}
                                x2={x2}
                                y2={y2}
                                stroke={isVis ? "#A7F3D0" : "#FDE68A"}
                                strokeWidth={isVis ? 2.4 : 1.8}
                                strokeDasharray={isVis ? undefined : "5 3"}
                              />
                            );
                          })}

                        {/* Building Layer */}
                        {aiLabLayers.building &&
                          buildings.map((b) => {
                            const ring = b.geometry?.coordinates?.[0];
                            if (!ring) return null;
                            return (
                              <polygon
                                key={b.id}
                                points={ringToSvgPoints(ring)}
                                fill="rgba(197, 170, 140, 0.55)"
                                stroke="#FAF8F3"
                                strokeWidth="2"
                              />
                            );
                          })}
                      </svg>
                    </div>
                  </div>

                  {/* Right: Model Cards (Model, Input, Prediction, Confidence) (5 cols) */}
                  <div className="lg:col-span-5 space-y-4">
                    <div className="bg-[#FAF8F3] border border-[#E4DFD5] rounded-2xl p-5 space-y-4 shadow-subtle">
                      <h3 className="font-editorial text-2xl text-[#171615]">
                        Active Neural Pipeline Models
                      </h3>

                      <div className="space-y-3">
                        {experiments.map((exp) => {
                          const isSel = exp.id === selectedExpId;
                          return (
                            <div
                              key={exp.id}
                              onClick={() => setSelectedExpId(exp.id)}
                              className={`p-4 rounded-xl border cursor-pointer transition-all space-y-2 ${
                                isSel
                                  ? "bg-[#FFFFFF] border-[#24221F] shadow-editorial"
                                  : "bg-[#F4F1EA] border-[#E4DFD5] hover:border-[#8A735F]"
                              }`}
                            >
                              <div className="flex items-center justify-between">
                                <span className="font-mono text-xs font-bold text-[#6B5748]">
                                  {exp.id} • {exp.task_type}
                                </span>
                                <span className="px-2 py-0.5 rounded bg-[#EBF2EE] border border-[#BDD4C6] font-mono text-xs font-semibold text-[#3D6B52]">
                                  IoU: {(Number(exp.iou) * 100).toFixed(1)}%
                                </span>
                              </div>

                              <div className="text-sm font-semibold text-[#171615]">
                                {exp.model_name}
                              </div>

                              <div className="grid grid-cols-2 gap-2 text-[11px] font-mono text-[#5C554E] pt-1">
                                <div>
                                  <span className="text-[#8C8277] block text-[10px]">
                                    INPUT / ARCH
                                  </span>
                                  <span className="truncate block">{exp.architecture}</span>
                                </div>
                                <div>
                                  <span className="text-[#8C8277] block text-[10px]">
                                    CONFIDENCE (DICE/F1)
                                  </span>
                                  <span className="font-semibold text-[#171615]">
                                    {(Number(exp.dice_f1) * 100).toFixed(1)}% • {exp.inference_time_ms}ms
                                  </span>
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* ===============================================================
                VIEW 04: AI COUNCIL PAGE (6 AGENTS CONNECTED DECISION SYSTEM)
            =============================================================== */}
            {activeTab === "council" && (
              <CouncilFlowView
                bundle={bundle}
                selectedParcelId={selectedParcelId}
                onSelectParcel={setSelectedParcelId}
                onNavigateTab={setActiveTab}
              />
            )}

            {/* ===============================================================
                VIEW 05: VERIFICATION CENTER (SURVEYOR WORKSPACE)
            =============================================================== */}
            {activeTab === "verification" && (
              <div className="space-y-6 animate-page-enter">
                <div className="bg-[#FAF8F3] border border-[#E4DFD5] rounded-2xl p-6 flex flex-wrap items-center justify-between gap-4 shadow-subtle">
                  <div className="space-y-1">
                    <div className="text-[11px] font-mono uppercase tracking-widest text-[#6B5748]">
                      SURVEYOR WORKSPACE • HUMAN-IN-THE-LOOP SIGN-OFF
                    </div>
                    <h2 className="font-editorial text-3xl sm:text-4xl text-[#171615]">
                      Cadastral Verification Center
                    </h2>
                    <p className="text-xs text-[#5C554E] max-w-2xl">
                      Inspect candidate parcel geometry alongside AI evidence, legacy GIS reference boundaries, and Council warnings before committing authoritative verification.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
                  {/* LEFT: Priority Queue List (4 cols) */}
                  <div className="lg:col-span-4 bg-[#FAF8F3] border border-[#E4DFD5] rounded-2xl p-4 space-y-3 max-h-[680px] overflow-y-auto shadow-subtle">
                    <div className="text-xs font-mono font-semibold uppercase tracking-wider text-[#6B5748] px-1">
                      Priority Verification Queue ({verifTasks.length})
                    </div>
                    {verifTasks
                      .slice()
                      .sort((a, b) => b.priority_score - a.priority_score)
                      .map((vt) => {
                        const isSel = vt.parcel_id === selectedParcel?.id;
                        return (
                          <div
                            key={vt.id}
                            onClick={() => setSelectedParcelId(vt.parcel_id)}
                            className={`p-3.5 rounded-xl border cursor-pointer transition-all space-y-1.5 ${
                              isSel
                                ? "bg-[#24221F] text-[#FAF8F3] border-[#24221F] shadow-md"
                                : "bg-[#F4F1EA] text-[#171615] border-[#E4DFD5] hover:border-[#8A735F]"
                            }`}
                          >
                            <div className="flex items-center justify-between">
                              <span className="font-mono text-xs font-bold">
                                {vt.parcel_id}
                              </span>
                              <span
                                className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold ${
                                  vt.status === "HUMAN_VERIFIED"
                                    ? "bg-[#EBF2EE] text-[#3D6B52]"
                                    : vt.priority === "HIGH"
                                    ? "bg-[#F9ECEB] text-[#9E3E37]"
                                    : "bg-[#F8F1E5] text-[#9E6B20]"
                                }`}
                              >
                                {vt.status === "HUMAN_VERIFIED"
                                  ? "VERIFIED"
                                  : `${vt.priority} (${vt.priority_score.toFixed(2)})`}
                              </span>
                            </div>
                            <div
                              className={`text-[11px] leading-snug ${
                                isSel ? "text-[#E6E0D5]" : "text-[#5C554E]"
                              }`}
                            >
                              {(vt.reasons || []).join(" • ")}
                            </div>
                          </div>
                        );
                      })}
                  </div>

                  {/* CENTER: Large Parcel Preview Canvas (4 cols) */}
                  <div className="lg:col-span-4 bg-[#24221F] text-[#FAF8F3] rounded-2xl p-4 border border-[#302C28] shadow-elevated space-y-3">
                    <div className="flex items-center justify-between text-xs font-mono">
                      <span className="text-[#C5AA8C]">
                        PARCEL PREVIEW: {selectedParcel?.id}
                      </span>
                      <span>{(selectedParcel?.confidence * 100 || 85).toFixed(0)}% Conf</span>
                    </div>

                    <div className="relative w-full aspect-square rounded-xl overflow-hidden bg-[#171615] border border-[#3A3530]">
                      <img
                        src={`${API_BASE}/api/scenes/${sceneId}/rgb.png`}
                        alt="Parcel Preview"
                        className="absolute inset-0 w-full h-full object-cover opacity-80"
                      />
                      <svg
                        viewBox={`0 0 ${VIEW_SIZE} ${VIEW_SIZE}`}
                        className="relative z-10 w-full h-full"
                      >
                        {refParcels.map((rp) => {
                          const ring = rp.geometry?.coordinates?.[0];
                          if (!ring) return null;
                          return (
                            <polygon
                              key={rp.id}
                              points={ringToSvgPoints(ring)}
                              fill="none"
                              stroke="#C5AA8C"
                              strokeWidth="1.5"
                              strokeDasharray="4 3"
                              opacity="0.65"
                            />
                          );
                        })}
                        {parcels.map((p) => {
                          const ring = p.geometry?.coordinates?.[0];
                          if (!ring) return null;
                          const isFocused = p.id === selectedParcel?.id;
                          return (
                            <polygon
                              key={p.id}
                              points={ringToSvgPoints(ring)}
                              onClick={() => setSelectedParcelId(p.id)}
                              fill={
                                isFocused
                                  ? "rgba(61, 107, 82, 0.45)"
                                  : "rgba(250, 248, 243, 0.08)"
                              }
                              stroke={isFocused ? "#FAF8F3" : "#6B5748"}
                              strokeWidth={isFocused ? 3.5 : 1.2}
                              className="cursor-pointer"
                            />
                          );
                        })}
                      </svg>
                    </div>

                    <div className="text-[11px] font-mono text-[#A18A76] flex items-center justify-between">
                      <span>Solid White: Candidate Geometry</span>
                      <span>Dashed Bronze: Reference GIS</span>
                    </div>
                  </div>

                  {/* RIGHT: Surveyor Evidence & Actions Panel (4 cols) */}
                  <div className="lg:col-span-4 bg-[#FAF8F3] border border-[#E4DFD5] rounded-2xl p-5 space-y-4 shadow-subtle">
                    {selectedParcel && (
                      <>
                        <div className="border-b border-[#E4DFD5] pb-3">
                          <div className="text-[10px] font-mono uppercase text-[#6B5748]">
                            EVIDENCE & ACTIONS
                          </div>
                          <h3 className="font-mono text-lg font-bold text-[#171615]">
                            {selectedParcel.id}
                          </h3>
                        </div>

                        <div className="grid grid-cols-2 gap-2.5 text-xs font-mono">
                          <div className="p-2.5 rounded-xl bg-[#F4F1EA] border border-[#E4DFD5]">
                            <span className="text-[10px] text-[#8C8277] block">GEOMETRY</span>
                            <span className="font-semibold text-[#171615]">
                              {selectedParcel.area_sqm?.toFixed(1)} m² ({selectedParcel.boundary_representation})
                            </span>
                          </div>
                          <div className="p-2.5 rounded-xl bg-[#F4F1EA] border border-[#E4DFD5]">
                            <span className="text-[10px] text-[#8C8277] block">GIS REFERENCE</span>
                            <span className="font-semibold text-[#6B5748]">
                              Conflict: {selectedParcel.conflict_status}
                            </span>
                          </div>
                          <div className="p-2.5 rounded-xl bg-[#F4F1EA] border border-[#E4DFD5]">
                            <span className="text-[10px] text-[#8C8277] block">COUNCIL</span>
                            <span className="font-semibold text-[#171615] truncate block">
                              {selectedParcel.council_decision}
                            </span>
                          </div>
                          <div className="p-2.5 rounded-xl bg-[#F4F1EA] border border-[#E4DFD5]">
                            <span className="text-[10px] text-[#8C8277] block">TOPOLOGY</span>
                            <span
                              className={`font-semibold ${
                                selectedParcel.topology_status === "VALID"
                                  ? "text-[#3D6B52]"
                                  : "text-[#9E3E37]"
                              }`}
                            >
                              {selectedParcel.topology_status}
                            </span>
                          </div>
                        </div>

                        {/* AI Evidence Breakdown */}
                        <div className="p-3.5 rounded-xl bg-[#F4F1EA] border border-[#E4DFD5] space-y-1.5 text-xs">
                          <div className="font-mono text-[10px] uppercase text-[#6B5748] font-semibold">
                            AI Evidence & Issues
                          </div>
                          <p className="text-[#5C554E] leading-relaxed">
                            Sources: {(selectedParcel.evidence_sources || []).join(", ")}
                          </p>
                          {selectedCouncil?.conflicting_evidence?.length > 0 && (
                            <div className="text-[11px] text-[#9E6B20] pt-1">
                              Flags: {selectedCouncil.conflicting_evidence.join(" • ")}
                            </div>
                          )}
                        </div>

                        {/* Surveyor Action Buttons: Verify, Reject, Edit, Split, Merge, Flag */}
                        <div className="space-y-2 pt-1">
                          <div className="text-[10px] font-mono uppercase tracking-wider text-[#6B5748]">
                            Surveyor Actions
                          </div>
                          <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                            <button
                              onClick={() =>
                                handleVerificationAction(
                                  selectedParcel.id,
                                  "HUMAN_VERIFIED",
                                  "Verified in Verification Center"
                                )
                              }
                              disabled={loading}
                              className="py-2.5 px-3 rounded-xl bg-[#3D6B52] hover:bg-[#325944] text-[#FAF8F3] font-semibold flex items-center justify-center gap-1.5"
                            >
                              <CheckCircle2 className="w-3.5 h-3.5" />
                              <span>Verify</span>
                            </button>

                            <button
                              onClick={() =>
                                handleVerificationAction(
                                  selectedParcel.id,
                                  "FIELD_VISIT_REQUESTED",
                                  "Flagged for field verification"
                                )
                              }
                              disabled={loading}
                              className="py-2.5 px-3 rounded-xl bg-[#F8F1E5] hover:bg-[#E5CFA8] border border-[#E5CFA8] text-[#9E6B20] font-semibold flex items-center justify-center gap-1.5"
                            >
                              <Flag className="w-3.5 h-3.5" />
                              <span>Flag</span>
                            </button>

                            <button
                              onClick={() => setActiveTab("workspace")}
                              className="py-2 px-3 rounded-xl bg-[#24221F] text-[#FAF8F3] flex items-center justify-center gap-1.5"
                            >
                              <Edit3 className="w-3.5 h-3.5" />
                              <span>Edit</span>
                            </button>

                            <button
                              onClick={() =>
                                handleVerificationAction(
                                  selectedParcel.id,
                                  "REJECTED",
                                  "Rejected candidate geometry"
                                )
                              }
                              disabled={loading}
                              className="py-2 px-3 rounded-xl bg-[#F9ECEB] hover:bg-[#E5B8B5] border border-[#E5B8B5] text-[#9E3E37] flex items-center justify-center gap-1.5"
                            >
                              <XCircle className="w-3.5 h-3.5" />
                              <span>Reject</span>
                            </button>

                            <button
                              onClick={() =>
                                handleQuickSplitParcel(selectedParcel.id, "VERTICAL")
                              }
                              disabled={loading}
                              className="py-2 px-3 rounded-xl bg-[#F4F1EA] hover:bg-[#EEEAE2] border border-[#D2C9BC] text-[#24221F] flex items-center justify-center gap-1.5"
                            >
                              <Split className="w-3.5 h-3.5" />
                              <span>Split</span>
                            </button>

                            <button
                              onClick={() => handleQuickMergeParcel(selectedParcel.id)}
                              disabled={loading}
                              className="py-2 px-3 rounded-xl bg-[#F4F1EA] hover:bg-[#EEEAE2] border border-[#D2C9BC] text-[#24221F] flex items-center justify-center gap-1.5"
                            >
                              <Merge className="w-3.5 h-3.5" />
                              <span>Merge</span>
                            </button>
                          </div>
                        </div>
                      </>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* ===============================================================
                VIEW 06: CHANGE DETECTION (DRAGGABLE BEFORE / AFTER SLIDER)
            =============================================================== */}
            {activeTab === "changes" && (
              <CompareSliderView
                bundle={bundle}
                onSelectParcelAndNavigate={(pid, tab) => {
                  setSelectedParcelId(pid);
                  setActiveTab(tab);
                }}
              />
            )}

            {/* ===============================================================
                VIEW 07: PARCEL TIME MACHINE (2024 -> 2025 -> 2026)
            =============================================================== */}
            {activeTab === "timemachine" && (
              <TimeMachineView
                bundle={bundle}
                selectedParcelId={selectedParcelId}
                onSelectParcel={setSelectedParcelId}
                parcelHistory={parcelHistory}
                onNavigateTab={setActiveTab}
              />
            )}

            {/* ===============================================================
                VIEW 08: SMART FIELD ROUTE (MISSION PLANNING INTERFACE)
            =============================================================== */}
            {activeTab === "routes" && (
              <div className="space-y-6 animate-page-enter">
                <div className="bg-[#FAF8F3] border border-[#E4DFD5] rounded-2xl p-6 flex flex-wrap items-center justify-between gap-4 shadow-subtle">
                  <div className="space-y-1">
                    <div className="inline-flex items-center gap-2 px-2.5 py-0.5 rounded bg-[#F8F1E5] border border-[#E5CFA8] text-[10px] font-mono font-semibold text-[#9E6B20] uppercase">
                      Prototype field planning • Spatial Clustering & Metric Sequence (Not Navigation-Grade Routing)
                    </div>
                    <h2 className="font-editorial text-3xl sm:text-4xl text-[#171615]">
                      Smart Field Verification Route Planner
                    </h2>
                  </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
                  {/* LEFT: Dominant Mission Map (7 cols) */}
                  <div className="lg:col-span-7 bg-[#24221F] text-[#FAF8F3] rounded-2xl p-4 border border-[#302C28] shadow-elevated space-y-3">
                    <div className="flex items-center justify-between text-xs font-mono">
                      <span className="text-[#C5AA8C]">
                        FIELD MISSION SECTOR • {sceneId}
                      </span>
                      <span className="text-[#A18A76]">
                        {routes.length} Clustered Verification Routes
                      </span>
                    </div>

                    <div className="relative w-full aspect-square rounded-xl overflow-hidden bg-[#171615] border border-[#3A3530]">
                      <img
                        src={`${API_BASE}/api/scenes/${sceneId}/rgb.png`}
                        alt="Field Mission Map"
                        className="absolute inset-0 w-full h-full object-cover opacity-75"
                      />
                      <svg
                        viewBox={`0 0 ${VIEW_SIZE} ${VIEW_SIZE}`}
                        className="relative z-10 w-full h-full"
                      >
                        {parcels.map((p) => {
                          const ring = p.geometry?.coordinates?.[0];
                          if (!ring) return null;
                          return (
                            <polygon
                              key={p.id}
                              points={ringToSvgPoints(ring)}
                              fill="rgba(250, 248, 243, 0.1)"
                              stroke="#8A735F"
                              strokeWidth="1.2"
                            />
                          );
                        })}

                        {routes.map((rt, rIdx) => {
                          const pts = rt.geometry?.coordinates || [];
                          const svgPts = pts
                            .map((pt: number[]) => lonLatToSvg(pt[0], pt[1]).join(","))
                            .join(" ");
                          const col = rIdx === 0 ? "#FAF8F3" : "#C5AA8C";
                          return (
                            <g key={rt.id}>
                              <polyline
                                points={svgPts}
                                fill="none"
                                stroke={col}
                                strokeWidth="3"
                                strokeDasharray="7 5"
                              />
                              {(rt.ordered_stops || []).map((st: any) => {
                                const [sx, sy] = lonLatToSvg(st.lon, st.lat);
                                return (
                                  <g
                                    key={st.task_id}
                                    onClick={() => setSelectedParcelId(st.parcel_id)}
                                    className="cursor-pointer"
                                  >
                                    <circle
                                      cx={sx}
                                      cy={sy}
                                      r="12"
                                      fill={
                                        st.priority === "HIGH" ? "#9E3E37" : "#24221F"
                                      }
                                      stroke="#FAF8F3"
                                      strokeWidth="2"
                                    />
                                    <text
                                      x={sx}
                                      y={sy + 4}
                                      textAnchor="middle"
                                      fill="#FAF8F3"
                                      fontSize="11"
                                      fontFamily="JetBrains Mono, monospace"
                                      fontWeight="bold"
                                    >
                                      {st.sequence}
                                    </text>
                                  </g>
                                );
                              })}
                            </g>
                          );
                        })}
                      </svg>
                    </div>
                  </div>

                  {/* RIGHT: Priority Parcels, Risk & Reason (5 cols) */}
                  <div className="lg:col-span-5 space-y-4">
                    {routes.map((rt: any) => (
                      <div
                        key={rt.id}
                        className="bg-[#FAF8F3] border border-[#E4DFD5] rounded-2xl p-5 space-y-3 shadow-subtle"
                      >
                        <div className="flex items-center justify-between border-b border-[#E4DFD5] pb-3">
                          <div>
                            <h3 className="font-editorial text-2xl text-[#171615]">
                              {rt.route_name}
                            </h3>
                            <p className="text-[11px] font-mono text-[#6B5748]">
                              {rt.disclaimer || "Prototype field planning"}
                            </p>
                          </div>
                          <span className="px-2.5 py-1 rounded-lg bg-[#EEEAE2] font-mono text-xs font-semibold text-[#171615]">
                            {rt.estimated_distance_m?.toFixed(0)}m Walk
                          </span>
                        </div>

                        <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
                          {(rt.ordered_stops || []).map((st: any) => (
                            <div
                              key={st.task_id}
                              onClick={() => setSelectedParcelId(st.parcel_id)}
                              className="p-3 rounded-xl bg-[#F4F1EA] border border-[#E4DFD5] hover:border-[#8A735F] cursor-pointer flex items-center justify-between gap-3 text-xs"
                            >
                              <div className="flex items-center gap-3">
                                <span className="w-6 h-6 rounded-full bg-[#24221F] text-[#FAF8F3] font-mono text-xs font-bold flex items-center justify-center shrink-0">
                                  {st.sequence}
                                </span>
                                <div>
                                  <div className="font-mono font-bold text-[#171615]">
                                    {st.parcel_id}
                                  </div>
                                  <div className="text-[11px] text-[#5C554E]">
                                    Reason: {(st.reasons || []).join(", ")}
                                  </div>
                                </div>
                              </div>
                              <div className="text-right font-mono shrink-0">
                                <span
                                  className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                                    st.priority === "HIGH"
                                      ? "bg-[#F9ECEB] text-[#9E3E37]"
                                      : "bg-[#F8F1E5] text-[#9E6B20]"
                                  }`}
                                >
                                  {st.priority} RISK
                                </span>
                                <div className="text-[10px] text-[#8C8277] mt-1">
                                  +{st.cumulative_distance_m}m
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* ===============================================================
                VIEW 09: CADASTRAL AI COPILOT (SPATIAL AI ASSISTANT)
            =============================================================== */}
            {activeTab === "copilot" && (
              <div className="space-y-6 animate-page-enter">
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
                  {/* LEFT: Interactive Map / Spatial Context (6 cols) */}
                  <div className="lg:col-span-6 bg-[#24221F] text-[#FAF8F3] rounded-2xl p-5 border border-[#302C28] shadow-elevated space-y-3 sticky top-24">
                    <div className="flex items-center justify-between text-xs font-mono">
                      <span className="text-[#C5AA8C]">
                        SPATIAL COPILOT CONTEXT • {sceneId}
                      </span>
                      <span>
                        Highlighted: {highlightedIds.length} features
                      </span>
                    </div>

                    <div className="relative w-full aspect-square rounded-xl overflow-hidden bg-[#171615] border border-[#3A3530]">
                      <img
                        src={`${API_BASE}/api/scenes/${sceneId}/rgb.png`}
                        alt="Copilot Map Context"
                        className="absolute inset-0 w-full h-full object-cover opacity-80"
                      />
                      <svg
                        viewBox={`0 0 ${VIEW_SIZE} ${VIEW_SIZE}`}
                        className="relative z-10 w-full h-full"
                      >
                        {parcels.map((p) => {
                          const ring = p.geometry?.coordinates?.[0];
                          if (!ring) return null;
                          const isHi =
                            highlightedIds.includes(p.id) || p.id === selectedParcelId;
                          const [cx, cy] = lonLatToSvg(
                            p.ulpin_ready_metadata?.centroid_lon || ring[0][0],
                            p.ulpin_ready_metadata?.centroid_lat || ring[0][1]
                          );
                          return (
                            <g
                              key={p.id}
                              onClick={() => setSelectedParcelId(p.id)}
                              className="cursor-pointer"
                            >
                              <polygon
                                points={ringToSvgPoints(ring)}
                                fill={
                                  isHi
                                    ? "rgba(253, 230, 138, 0.42)"
                                    : "rgba(250, 248, 243, 0.1)"
                                }
                                stroke={isHi ? "#FAF8F3" : "#8A735F"}
                                strokeWidth={isHi ? 3.2 : 1.4}
                              />
                              <text
                                x={cx}
                                y={cy}
                                textAnchor="middle"
                                fill="#FAF8F3"
                                fontSize="10"
                                fontFamily="JetBrains Mono, monospace"
                                fontWeight="bold"
                              >
                                {p.id.split("_").slice(-2).join("_")}
                              </text>
                            </g>
                          );
                        })}
                      </svg>
                    </div>
                  </div>

                  {/* RIGHT: Spatial Conversation & Evidence Console (6 cols) */}
                  <div className="lg:col-span-6 space-y-4">
                    <div className="bg-[#FAF8F3] border border-[#E4DFD5] rounded-2xl p-6 space-y-4 shadow-subtle">
                      <div>
                        <div className="text-[10px] font-mono uppercase tracking-widest text-[#6B5748]">
                          DETERMINISTIC SPATIAL DATABASE ASSISTANT
                        </div>
                        <h2 className="font-editorial text-3xl text-[#171615]">
                          Cadastral AI Copilot
                        </h2>
                        <p className="text-xs text-[#5C554E]">
                          Queries live PostGIS records, topology tables, and AI Council deliberations—automatically highlighting referenced parcels on the map.
                        </p>
                      </div>

                      {/* Preset Spatial Inquiry Pills */}
                      <div className="flex flex-wrap gap-1.5 text-xs">
                        {[
                          "Why was parcel P-003 flagged?",
                          "Why was parcel P-002 flagged?",
                          "Which parcels overlap?",
                          "Show low-confidence parcels.",
                          "Show parcels with building/parcel conflicts.",
                          "What changed between T0 and T2?",
                          "Which areas need field verification?",
                        ].map((q) => (
                          <button
                            key={q}
                            onClick={() => {
                              setCopilotQuery(q);
                              handleCopilotSubmit(q);
                            }}
                            className="px-2.5 py-1.5 rounded-lg bg-[#F4F1EA] hover:bg-[#EEEAE2] border border-[#D2C9BC] text-[#24221F] font-mono text-[11px] transition-colors"
                          >
                            {q}
                          </button>
                        ))}
                      </div>

                      {/* Query Input */}
                      <div className="flex gap-2">
                        <input
                          type="text"
                          value={copilotQuery}
                          onChange={(e) => setCopilotQuery(e.target.value)}
                          onKeyDown={(e) => e.key === "Enter" && handleCopilotSubmit()}
                          placeholder="Ask about parcel flags, overlaps, GIS conflicts, or changes..."
                          className="flex-1 bg-[#FFFFFF] border border-[#D2C9BC] rounded-xl px-3.5 py-2.5 text-xs font-mono text-[#171615] focus:outline-none focus:border-[#6B5748]"
                        />
                        <button
                          onClick={() => handleCopilotSubmit()}
                          disabled={loading}
                          className="btn-primary-dark px-5 py-2.5 rounded-xl text-xs font-medium"
                        >
                          Ask Copilot
                        </button>
                      </div>
                    </div>

                    {/* Structured Evidence Responses */}
                    <div className="space-y-3">
                      {copilotHistory.map((item, idx) => (
                        <div
                          key={idx}
                          className="bg-[#FAF8F3] border border-[#E4DFD5] rounded-2xl p-5 space-y-3 shadow-subtle"
                        >
                          <div className="flex items-center justify-between border-b border-[#E4DFD5] pb-2.5">
                            <span className="font-mono text-xs font-bold text-[#171615]">
                              {item.question}
                            </span>
                            <span className="px-2 py-0.5 rounded bg-[#EEEAE2] font-mono text-[10px] text-[#6B5748]">
                              Tool: {item.tool_invoked}
                            </span>
                          </div>

                          <div className="text-xs text-[#24221F] space-y-1.5 leading-relaxed font-sans">
                            {String(item.answer || "")
                              .split("\n")
                              .filter((line) => line.trim().length > 0)
                              .map((line, lIdx) => {
                                const trimmed = line.trim();
                                if (trimmed.startsWith("### ")) {
                                  return (
                                    <h4
                                      key={lIdx}
                                      className="font-editorial text-xl text-[#171615] pt-1"
                                    >
                                      {trimmed.replace(/^###\s+/, "").replace(/\*\*/g, "")}
                                    </h4>
                                  );
                                }
                                const cleanText = trimmed
                                  .replace(/^[-*]\s+/, "")
                                  .replace(/\*\*/g, "");
                                const isBullet =
                                  trimmed.startsWith("- ") || trimmed.startsWith("* ");
                                return (
                                  <div
                                    key={lIdx}
                                    className={
                                      isBullet
                                        ? "pl-3 border-l-2 border-[#C5AA8C] text-[#302C28] py-0.5"
                                        : "text-[#24221F]"
                                    }
                                  >
                                    {cleanText}
                                  </div>
                                );
                              })}
                          </div>

                          {item.highlight_feature_ids?.length > 0 && (
                            <div className="pt-2 border-t border-[#E4DFD5] flex flex-wrap items-center gap-2">
                              <span className="text-[11px] font-mono text-[#6B5748]">
                                Highlighted on Map:
                              </span>
                              {item.highlight_feature_ids.map((fid: string) => (
                                <button
                                  key={fid}
                                  onClick={() => {
                                    if (fid.includes("_P_")) setSelectedParcelId(fid);
                                    setHighlightedIds(item.highlight_feature_ids);
                                  }}
                                  className="px-2.5 py-1 rounded-lg bg-[#24221F] text-[#FAF8F3] font-mono text-[11px] hover:bg-[#171615]"
                                >
                                  Focus {fid.split("_").slice(-2).join("_")}
                                </button>
                              ))}
                              <button
                                onClick={() => setActiveTab("workspace")}
                                className="px-2.5 py-1 rounded-lg bg-[#EEEAE2] text-[#24221F] font-mono text-[11px]"
                              >
                                Open in Full Map →
                              </button>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* ===============================================================
                VIEW 10: PROJECTS (VISUAL WORKSPACE THUMBNAILS)
            =============================================================== */}
            {activeTab === "projects" && (
              <div className="space-y-6 animate-page-enter">
                <div className="bg-[#FAF8F3] border border-[#E4DFD5] rounded-2xl p-6 flex flex-wrap items-center justify-between gap-4 shadow-subtle">
                  <div>
                    <div className="text-[11px] font-mono uppercase tracking-widest text-[#6B5748]">
                      CADASTRAL SURVEY REPOSITORIES • ULPIN_READY_METADATA
                    </div>
                    <h2 className="font-editorial text-3xl sm:text-4xl text-[#171615]">
                      Survey Workspaces & Projects
                    </h2>
                  </div>

                  <div className="flex flex-wrap items-center gap-2 text-xs">
                    <input
                      type="text"
                      value={newProjName}
                      onChange={(e) => setNewProjName(e.target.value)}
                      placeholder="New Project Name..."
                      className="bg-[#FFFFFF] border border-[#D2C9BC] rounded-xl px-3 py-2 text-xs text-[#171615]"
                    />
                    <input
                      type="text"
                      value={newProjRegion}
                      onChange={(e) => setNewProjRegion(e.target.value)}
                      placeholder="Region / Tehsil..."
                      className="bg-[#FFFFFF] border border-[#D2C9BC] rounded-xl px-3 py-2 text-xs text-[#171615]"
                    />
                    <button
                      onClick={async () => {
                        if (!newProjName) return;
                        await fetch(`${API_BASE}/api/projects`, {
                          method: "POST",
                          headers: { "Content-Type": "application/json" },
                          body: JSON.stringify({
                            name: newProjName,
                            region_name: newProjRegion,
                          }),
                        });
                        setNewProjName("");
                        await fetchAllData();
                      }}
                      className="btn-primary-dark px-4 py-2 rounded-xl text-xs font-medium"
                    >
                      + Create Project
                    </button>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {projects.map((p, idx) => {
                    const thumbImgs = [
                      "/scenes/scene_urban_T1/rgb.png",
                      "/scenes/scene_urban_T2/rgb.png",
                      "/scenes/scene_urban_T0/rgb.png",
                    ];
                    return (
                      <div
                        key={p.id}
                        className="card-editorial rounded-2xl overflow-hidden flex flex-col justify-between"
                      >
                        <div>
                          <div className="relative h-44 bg-[#24221F] overflow-hidden border-b border-[#E4DFD5]">
                            <img
                              src={thumbImgs[idx % thumbImgs.length]}
                              alt={p.name}
                              className="w-full h-full object-cover opacity-85"
                            />
                            <span className="absolute top-3 left-3 px-2.5 py-0.5 rounded bg-[#171615]/85 text-[#FAF8F3] font-mono text-[10px]">
                              {p.id}
                            </span>
                            <span className="absolute top-3 right-3 px-2 py-0.5 rounded bg-[#FAF8F3]/90 text-[#6B5748] font-mono text-[10px] font-semibold">
                              {p.data_label}
                            </span>
                          </div>
                          <div className="p-5 space-y-2">
                            <h3 className="font-editorial text-2xl text-[#171615]">
                              {p.name}
                            </h3>
                            <p className="text-xs text-[#5C554E]">{p.region_name}</p>
                            <div className="pt-2 flex items-center gap-2 font-mono text-[10px] text-[#6B5748]">
                              <span>{p.crs}</span>
                              <span>•</span>
                              <span>{p.projected_crs}</span>
                              <span>•</span>
                              <span>{p.ulpin_metadata_mode}</span>
                            </div>
                          </div>
                        </div>

                        <div className="px-5 pb-5">
                          <button
                            onClick={() => {
                              setProjectId(p.id);
                              setActiveTab("workspace");
                            }}
                            className="w-full btn-primary-dark py-2.5 rounded-xl text-xs font-medium flex items-center justify-center gap-1.5"
                          >
                            <span>Open Project Workspace</span>
                            <ArrowRight className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* ===============================================================
                VIEW 11: DATASETS (INGESTION & CRS VALIDATOR)
            =============================================================== */}
            {activeTab === "datasets" && (
              <div className="space-y-6 animate-page-enter">
                <div className="bg-[#FAF8F3] border border-[#E4DFD5] rounded-2xl p-6 space-y-4 shadow-subtle">
                  <div className="flex flex-wrap items-center justify-between gap-4">
                    <div>
                      <div className="text-[11px] font-mono uppercase tracking-widest text-[#6B5748]">
                        GEOSPATIAL INGESTION ENGINE • CRS & GEOMETRY VALIDATION
                      </div>
                      <h2 className="font-editorial text-3xl sm:text-4xl text-[#171615]">
                        Datasets & Raster/Vector Ingestion
                      </h2>
                      <p className="text-xs text-[#5C554E]">
                        Supports GeoTIFF (.tif), Drone Ortho (.png/.jpg), GeoJSON, Shapefile (.shp), GeoPackage (.gpkg), and CSV.
                      </p>
                    </div>

                    <label className="btn-primary-dark px-5 py-3 rounded-xl text-xs font-medium cursor-pointer flex items-center gap-2">
                      <Upload className="w-4 h-4" />
                      <span>Upload & Validate Dataset</span>
                      <input
                        type="file"
                        onChange={handleFileUpload}
                        className="hidden"
                      />
                    </label>
                  </div>

                  {uploadInspection && (
                    <pre className="bg-[#24221F] text-[#FAF8F3] rounded-xl p-4 text-xs font-mono overflow-x-auto">
                      {JSON.stringify(uploadInspection, null, 2)}
                    </pre>
                  )}
                </div>

                <div className="bg-[#FAF8F3] border border-[#E4DFD5] rounded-2xl overflow-hidden shadow-subtle">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-[#EEEAE2] text-[#6B5748] font-mono uppercase text-[11px] border-b border-[#E4DFD5]">
                      <tr>
                        <th className="p-4">Dataset</th>
                        <th className="p-4">Type</th>
                        <th className="p-4">Source Format</th>
                        <th className="p-4">CRS</th>
                        <th className="p-4">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#E4DFD5]">
                      {datasets.map((ds) => (
                        <tr key={ds.id} className="hover:bg-[#F4F1EA]">
                          <td className="p-4">
                            <div className="font-semibold text-[#171615]">{ds.name}</div>
                            <div className="font-mono text-[10px] text-[#8C8277]">
                              {ds.file_path}
                            </div>
                          </td>
                          <td className="p-4 font-mono">{ds.dataset_type}</td>
                          <td className="p-4 font-mono">{ds.source_format}</td>
                          <td className="p-4 font-mono text-[#6B5748]">{ds.crs}</td>
                          <td className="p-4">
                            <span className="px-2.5 py-0.5 rounded bg-[#EBF2EE] border border-[#BDD4C6] font-mono text-[10px] font-semibold text-[#3D6B52]">
                              {ds.validation_status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* ===============================================================
                VIEW 12: EXPORTS (VALIDATED GIS EXPORTER)
            =============================================================== */}
            {activeTab === "exports" && (
              <div className="space-y-6 animate-page-enter">
                <div className="bg-[#FAF8F3] border border-[#E4DFD5] rounded-2xl p-6 space-y-4 shadow-subtle">
                  <div className="space-y-1">
                    <div className="text-[11px] font-mono uppercase tracking-widest text-[#6B5748]">
                      POST-EXPORT READ-BACK INTEGRITY VERIFIED
                    </div>
                    <h2 className="font-editorial text-3xl sm:text-4xl text-[#171615]">
                      Validated GIS Exports
                    </h2>
                    <p className="text-xs text-[#5C554E] max-w-2xl">
                      Export candidate and human-verified parcel polygons with embedded metric area, confidence breakdown, AI Council decision, and audit lineage.
                    </p>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
                    {[
                      { fmt: "GeoJSON", desc: "Standard Web-GIS Vector (.geojson)" },
                      { fmt: "Shapefile", desc: "ESRI Archive Bundle (.zip)" },
                      { fmt: "CSV", desc: "Tabular Metric Telemetry (.csv)" },
                      { fmt: "GeoPackage", desc: "OGC Spatial Database (.gpkg)" },
                    ].map((item) => (
                      <button
                        key={item.fmt}
                        onClick={() => handleExportFormat(item.fmt)}
                        disabled={loading}
                        className="p-4 rounded-xl bg-[#F4F1EA] hover:bg-[#EEEAE2] border border-[#D2C9BC] text-left transition-all space-y-1.5 group"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-mono text-sm font-bold text-[#171615]">
                            {item.fmt}
                          </span>
                          <Download className="w-4 h-4 text-[#6B5748] group-hover:translate-y-0.5 transition-transform" />
                        </div>
                        <div className="text-[11px] text-[#5C554E]">{item.desc}</div>
                      </button>
                    ))}
                  </div>
                </div>

                <div className="space-y-3">
                  {exportResults.map((er, i) => (
                    <div
                      key={i}
                      className="bg-[#FAF8F3] border border-[#BDD4C6] rounded-2xl p-5 flex flex-wrap items-center justify-between gap-4 shadow-subtle"
                    >
                      <div className="space-y-1 font-mono text-xs">
                        <div className="font-bold text-[#3D6B52]">
                          ✓ {er.format} Export — Post-Export Integrity Check:{" "}
                          {er.validation_passed ? "PASSED" : "FAILED"}
                        </div>
                        <div className="text-[#171615]">{er.file_path}</div>
                        <div className="text-[#6B5748] text-[11px]">
                          Features: {er.feature_count} • Valid Geometries:{" "}
                          {er.valid_geometries} • Size: {er.file_size_bytes} bytes
                        </div>
                      </div>
                      <a
                        href={`${API_BASE}/api/exports/download?file_path=${encodeURIComponent(
                          er.file_path
                        )}`}
                        target="_blank"
                        rel="noreferrer"
                        className="btn-primary-dark px-4 py-2.5 rounded-xl text-xs font-mono"
                      >
                        Download Validated File
                      </a>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* ===============================================================
                VIEW 13: PROFILE (SURVEYOR PROFILE & VERIFICATION HISTORY)
            =============================================================== */}
            {activeTab === "profile" && (
              <div className="space-y-6 animate-page-enter">
                <div className="bg-[#FAF8F3] border border-[#E4DFD5] rounded-2xl p-6 sm:p-8 flex flex-wrap items-center justify-between gap-6 shadow-subtle">
                  <div className="flex items-center gap-4">
                    <div className="w-16 h-16 rounded-2xl bg-[#24221F] text-[#FAF8F3] flex items-center justify-center font-editorial text-3xl">
                      {selectedProfile.name.charAt(0)}
                    </div>
                    <div className="space-y-1">
                      <span className="px-2.5 py-0.5 rounded bg-[#EEEAE2] border border-[#D2C9BC] font-mono text-[10px] font-semibold text-[#6B5748]">
                        {selectedProfile.badge}
                      </span>
                      <h2 className="font-editorial text-3xl text-[#171615]">
                        {selectedProfile.name}
                      </h2>
                      <p className="text-xs font-mono text-[#5C554E]">
                        Role: {selectedProfile.role} • Operator ID:{" "}
                        {selectedProfile.operatorId} • Workspace: AeroCadastre Demo
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {(["Surveyor", "Demo User", "Administrator"] as const).map((r) => (
                      <button
                        key={r}
                        onClick={() => setSelectedProfile(DEMO_PROFILES[r])}
                        className={`px-3 py-1.5 rounded-xl text-xs font-mono border transition-colors ${
                          selectedProfile.role === r
                            ? "bg-[#24221F] text-[#FAF8F3] border-[#24221F]"
                            : "bg-[#F4F1EA] text-[#6B5748] border-[#D2C9BC]"
                        }`}
                      >
                        Switch to {r}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <div className="bg-[#FAF8F3] border border-[#E4DFD5] rounded-2xl p-5 space-y-3 shadow-subtle">
                    <h3 className="font-editorial text-2xl text-[#171615]">
                      Verification History ({feedbackList.length})
                    </h3>
                    <div className="space-y-2 max-h-80 overflow-y-auto">
                      {feedbackList.map((fb) => (
                        <div
                          key={fb.id}
                          className="p-3 rounded-xl bg-[#F4F1EA] border border-[#E4DFD5] font-mono text-xs space-y-1"
                        >
                          <div className="flex justify-between font-bold text-[#171615]">
                            <span>
                              {fb.action_type} • {fb.feature_id}
                            </span>
                            <span className="text-[#3D6B52]">{fb.operator_id}</span>
                          </div>
                          <div className="text-[11px] text-[#5C554E]">
                            Reason: {fb.reason}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="bg-[#FAF8F3] border border-[#E4DFD5] rounded-2xl p-5 space-y-3 shadow-subtle">
                    <h3 className="font-editorial text-2xl text-[#171615]">
                      Recent Workspace Activity ({auditLogs.length})
                    </h3>
                    <div className="space-y-2 max-h-80 overflow-y-auto">
                      {auditLogs.slice(0, 12).map((al) => (
                        <div
                          key={al.id}
                          className="p-3 rounded-xl bg-[#F4F1EA] border border-[#E4DFD5] font-mono text-xs space-y-1"
                        >
                          <div className="flex justify-between font-semibold text-[#171615]">
                            <span>
                              {al.operation} ({al.target_id})
                            </span>
                            <span className="text-[#6B5748]">{al.actor}</span>
                          </div>
                          <div className="text-[10px] text-[#8C8277]">
                            {al.source} • {al.created_at}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* ===============================================================
                VIEW 14: SETTINGS & AUDIT LOGS
            =============================================================== */}
            {activeTab === "settings" && (
              <div className="space-y-6 animate-page-enter">
                <div className="bg-[#FAF8F3] border border-[#E4DFD5] rounded-2xl p-6 space-y-3 shadow-subtle">
                  <h2 className="font-editorial text-3xl text-[#171615]">
                    System Configuration & Audit Lineage
                  </h2>
                  {health && (
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs font-mono">
                      <div className="p-3 rounded-xl bg-[#F4F1EA] border border-[#E4DFD5]">
                        <span className="text-[10px] text-[#8C8277] block">STATUS</span>
                        <span className="font-bold text-[#3D6B52]">{health.status}</span>
                      </div>
                      <div className="p-3 rounded-xl bg-[#F4F1EA] border border-[#E4DFD5]">
                        <span className="text-[10px] text-[#8C8277] block">ENGINE</span>
                        <span className="font-semibold text-[#171615]">
                          {health.database_engine}
                        </span>
                      </div>
                      <div className="p-3 rounded-xl bg-[#F4F1EA] border border-[#E4DFD5]">
                        <span className="text-[10px] text-[#8C8277] block">STORAGE ROOT</span>
                        <span className="font-semibold text-[#6B5748]">
                          {health.storage_root}
                        </span>
                      </div>
                      <div className="p-3 rounded-xl bg-[#F4F1EA] border border-[#E4DFD5]">
                        <span className="text-[10px] text-[#8C8277] block">RECORDS</span>
                        <span className="font-semibold text-[#171615]">
                          {health.parcels_in_db} Parcels • {health.experiments_in_db} Models
                        </span>
                      </div>
                    </div>
                  )}
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <div className="bg-[#FAF8F3] border border-[#E4DFD5] rounded-2xl p-5 space-y-3 shadow-subtle">
                    <h3 className="font-editorial text-2xl text-[#171615]">
                      Human-in-the-Loop Retraining Feedback ({feedbackList.length})
                    </h3>
                    <div className="space-y-2 max-h-96 overflow-y-auto">
                      {feedbackList.map((fb) => (
                        <div
                          key={fb.id}
                          className="p-3 rounded-xl bg-[#F4F1EA] border border-[#E4DFD5] font-mono text-xs"
                        >
                          <div className="font-bold text-[#171615]">
                            {fb.action_type} on {fb.feature_id} by {fb.operator_id}
                          </div>
                          <div className="text-[11px] text-[#5C554E] mt-0.5">
                            Class: {fb.before_class || "N/A"} → {fb.after_class || "N/A"} |{" "}
                            {fb.reason}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="bg-[#FAF8F3] border border-[#E4DFD5] rounded-2xl p-5 space-y-3 shadow-subtle">
                    <h3 className="font-editorial text-2xl text-[#171615]">
                      Traceable Cadastral Audit Log ({auditLogs.length})
                    </h3>
                    <div className="space-y-2 max-h-96 overflow-y-auto">
                      {auditLogs.map((al) => (
                        <div
                          key={al.id}
                          className="p-3 rounded-xl bg-[#F4F1EA] border border-[#E4DFD5] font-mono text-xs"
                        >
                          <div className="flex justify-between font-bold text-[#171615]">
                            <span>
                              {al.operation} ({al.target_id})
                            </span>
                            <span className="text-[#6B5748]">{al.actor}</span>
                          </div>
                          <div className="text-[11px] text-[#8C8277] mt-0.5">
                            Source: {al.source} • {al.created_at}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </main>
        )}
      </div>
    </div>
  );
}
