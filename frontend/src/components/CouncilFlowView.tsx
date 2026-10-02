"use client";

import React from "react";
import {
  ShieldCheck,
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Eye,
  Compass,
  Layers,
  Cpu,
  MapPin,
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

interface CouncilFlowViewProps {
  bundle: any;
  selectedParcelId: string | null;
  onSelectParcel: (id: string) => void;
  onNavigateTab: (tab: string) => void;
}

export default function CouncilFlowView({
  bundle,
  selectedParcelId,
  onSelectParcel,
  onNavigateTab,
}: CouncilFlowViewProps) {
  const parcels: any[] = bundle?.candidate_parcels || [];
  const councils: any[] = bundle?.council_decisions || [];
  const selectedCouncil =
    councils.find((c) => c.parcel_id === selectedParcelId) || councils[0] || null;
  const selectedParcel =
    parcels.find((p) => p.id === (selectedCouncil?.parcel_id || selectedParcelId)) ||
    parcels[0] ||
    null;

  const agentOrder = [
    { key: "VISION_AGENT", label: "VISION", domain: "Drone RGB + Edge Clarity" },
    { key: "GEOMETRY_AGENT", label: "GEOMETRY", domain: "Compactness & Topology" },
    { key: "GIS_AGENT", label: "GIS", domain: "Reference Layer Alignment" },
    { key: "ML_AGENT", label: "ML", domain: "Multi-Model Agreement" },
    { key: "ANOMALY_AGENT", label: "ANOMALY", domain: "Encroachment & Conflict" },
    { key: "FIELD_VERIFICATION_AGENT", label: "FIELD VERIFICATION", domain: "Survey Priority & Risk" },
  ];

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

  return (
    <div className="space-y-4 animate-page-enter">
      {/* Top Header & Parcel Selector */}
      <div className="bg-[#FAF8F3] border border-[#E4DFD5] rounded-2xl p-5 flex flex-wrap items-center justify-between gap-4 shadow-subtle">
        <div className="space-y-0.5">
          <div className="text-[10px] font-mono uppercase tracking-widest text-[#6B5748]">
            MULTI-AGENT DELIBERATIVE DECISION SYSTEM • ADVISORY EVIDENCE FUSION
          </div>
          <h2 className="font-editorial text-3xl text-[#171615]">
            Six-Agent Cadastral AI Council
          </h2>
        </div>

        <div className="flex items-center gap-3">
          <label className="text-xs font-mono text-[#6B5748]">Deliberating Parcel:</label>
          <select
            value={selectedParcel?.id || ""}
            onChange={(e) => onSelectParcel(e.target.value)}
            className="bg-[#FFFFFF] border border-[#D2C9BC] rounded-xl px-3.5 py-2 text-xs font-mono text-[#171615] shadow-sm"
          >
            {parcels.map((p) => (
              <option key={p.id} value={p.id}>
                {p.id} • {(p.confidence * 100).toFixed(0)}% Conf • {p.council_decision}
              </option>
            ))}
          </select>
        </div>
      </div>

      {selectedCouncil && (
        <div className="space-y-3">
          {/* STAGE 1: EVIDENCE LAYER INPUTS */}
          <div className="bg-[#FAF8F3] border border-[#E4DFD5] rounded-2xl p-4">
            <div className="flex items-center justify-between mb-2.5">
              <span className="text-[10px] font-mono uppercase tracking-widest text-[#6B5748] font-semibold">
                01 • MULTI-MODAL EVIDENCE INPUTS ({selectedCouncil.parcel_id})
              </span>
              <span className="text-[10px] font-mono text-[#8C8277]">
                EPSG:4326 / Metric EPSG:32643
              </span>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5 text-xs">
              {[
                {
                  title: "Drone Ortho Imagery",
                  detail: "0.1m/px Ground Sampling",
                  val: `Vision Score: ${(selectedCouncil.vision_score * 100).toFixed(0)}%`,
                },
                {
                  title: "DSM Surface Elevation",
                  detail: `Mean Elev: ${selectedParcel?.dsm_mean_elevation_m ?? 215}m`,
                  val: `Buildings: ${selectedParcel?.building_count ?? 0}`,
                },
                {
                  title: "Legacy Reference GIS",
                  detail: `Conflict: ${selectedParcel?.conflict_status || "NONE"}`,
                  val: `GIS Score: ${(selectedCouncil.gis_score * 100).toFixed(0)}%`,
                },
                {
                  title: "PostGIS Metric Topology",
                  detail: `Area: ${selectedParcel?.area_sqm?.toFixed(1)} m²`,
                  val: `Topology: ${selectedParcel?.topology_status || "VALID"}`,
                },
              ].map((ev, i) => (
                <div
                  key={i}
                  className="p-3 rounded-xl bg-[#F4F1EA] border border-[#E4DFD5] flex items-center justify-between gap-2"
                >
                  <div>
                    <div className="font-semibold text-[#171615] text-xs">{ev.title}</div>
                    <div className="text-[10px] text-[#5C554E]">{ev.detail}</div>
                  </div>
                  <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-[#FAF8F3] border border-[#D2C9BC] text-[#6B5748] font-semibold whitespace-nowrap">
                    {ev.val}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Connector 1 */}
          <div className="flex items-center justify-center">
            <span className="px-3 py-0.5 rounded-full bg-[#EEEAE2] border border-[#D2C9BC] text-[10px] font-mono uppercase text-[#6B5748]">
              ↓ 02 • Parallel 6-Agent Domain Evaluation ↓
            </span>
          </div>

          {/* STAGE 2: 6 SPECIALIZED AGENTS */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {agentOrder.map((ag) => {
              const rep =
                selectedCouncil.agent_reports?.[ag.key] ||
                selectedCouncil.agent_reports?.[ag.key.toLowerCase()] ||
                {};
              const warnings: string[] = rep.warnings || [];
              const hasWarning = warnings.length > 0 || rep.priority === "HIGH";
              const scorePct =
                rep.confidence !== undefined
                  ? Math.round(rep.confidence * 100)
                  : rep.priority_score !== undefined
                  ? Math.round(rep.priority_score * 100)
                  : Math.round((selectedCouncil.final_evidence_score || 0.8) * 100);

              const bullets: string[] = rep.evidence || rep.reasons || [];

              return (
                <div
                  key={ag.key}
                  className={`rounded-2xl p-4 border transition-all flex flex-col justify-between ${
                    hasWarning
                      ? "bg-[#FAF8F3] border-[#E5CFA8] shadow-subtle"
                      : "bg-[#FAF8F3] border-[#E4DFD5] shadow-subtle"
                  }`}
                >
                  <div className="space-y-2">
                    <div className="flex items-center justify-between border-b border-[#E4DFD5] pb-2">
                      <div>
                        <div className="font-mono text-xs font-bold text-[#171615]">
                          {ag.label}
                        </div>
                        <div className="text-[10px] text-[#6B5748]">{ag.domain}</div>
                      </div>
                      <span
                        className={`px-2 py-0.5 rounded-lg font-mono text-[11px] font-semibold ${
                          rep.priority === "HIGH"
                            ? "bg-[#F9ECEB] text-[#9E3E37] border border-[#E5B8B5]"
                            : scorePct >= 80
                            ? "bg-[#EBF2EE] text-[#3D6B52] border border-[#BDD4C6]"
                            : "bg-[#F8F1E5] text-[#9E6B20] border border-[#E5CFA8]"
                        }`}
                      >
                        {rep.confidence !== undefined
                          ? `${scorePct}% Conf`
                          : `Priority: ${rep.priority || "HIGH"}`}
                      </span>
                    </div>

                    {/* Confidence bar */}
                    <div className="w-full h-1.5 bg-[#EEEAE2] rounded-full overflow-hidden">
                      <div
                        style={{ width: `${Math.min(100, Math.max(15, scorePct))}%` }}
                        className={`h-full rounded-full ${
                          rep.priority === "HIGH"
                            ? "bg-[#9E3E37]"
                            : scorePct >= 80
                            ? "bg-[#3D6B52]"
                            : "bg-[#9E6B20]"
                        }`}
                      />
                    </div>

                    <div className="text-[11px] font-mono text-[#24221F] font-semibold">
                      Status: {rep.decision || "EVALUATED"}
                    </div>

                    {bullets.length > 0 && (
                      <ul className="text-[11px] text-[#5C554E] space-y-0.5 list-disc list-inside">
                        {bullets.slice(0, 3).map((ev: string, idx: number) => (
                          <li key={idx} className="truncate" title={ev}>
                            {ev}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>

                  {warnings.length > 0 && (
                    <div className="mt-2.5 px-2.5 py-1.5 rounded-xl bg-[#F8F1E5] border border-[#E5CFA8] text-[10px] text-[#9E6B20] flex items-center gap-1.5">
                      <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                      <span className="truncate" title={warnings[0]}>
                        {warnings[0]}
                      </span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Connector 2 */}
          <div className="flex items-center justify-center">
            <span className="px-3.5 py-0.5 rounded-full bg-[#24221F] text-[#FAF8F3] text-[10px] font-mono uppercase">
              ↓ 03 • Council Evidence Fusion & Verdict ↓
            </span>
          </div>

          {/* STAGE 3: LARGE COUNCIL DECISION BANNER + PARCEL VISUAL */}
          <div className="bg-[#24221F] text-[#FAF8F3] rounded-2xl p-6 border border-[#302C28] shadow-elevated grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
            {/* Verdict Headline */}
            <div className="lg:col-span-4 space-y-2.5 border-b lg:border-b-0 lg:border-r border-[#3A3530] pb-4 lg:pb-0 lg:pr-5">
              <div className="text-[10px] font-mono uppercase tracking-widest text-[#C5AA8C]">
                COUNCIL DECISION • {selectedCouncil.parcel_id}
              </div>
              <div className="font-editorial text-4xl text-[#FAF8F3] leading-none">
                {selectedCouncil.decision === "ACCEPT_FOR_REVIEW"
                  ? "ACCEPT FOR REVIEW"
                  : "REQUIRES VERIFICATION"}
              </div>
              <div className="text-xs font-mono text-[#A18A76]">
                Code: <strong className="text-[#FAF8F3]">{selectedCouncil.decision}</strong>
              </div>
              <div className="flex flex-wrap items-center gap-2 pt-1">
                <span className="px-2.5 py-1 rounded-lg bg-[#302C28] border border-[#6B5748] font-mono text-xs text-[#FAF8F3]">
                  Confidence: {(selectedCouncil.final_evidence_score * 100).toFixed(0)}%
                </span>
                <span className="px-2.5 py-1 rounded-lg bg-[#171615] border border-[#3A3530] font-mono text-xs text-[#C5AA8C]">
                  Action: Surveyor review
                </span>
              </div>
            </div>

            {/* Supporting & Conflicting Evidence */}
            <div className="lg:col-span-5 space-y-2.5 text-xs">
              <div>
                <div className="font-mono text-[10px] uppercase tracking-wider text-[#A7F3D0] mb-1">
                  Supporting Evidence
                </div>
                <ul className="space-y-0.5 text-[#E6E0D5] list-disc list-inside text-[11px]">
                  {(selectedCouncil.supporting_evidence || []).slice(0, 3).map((s: string, i: number) => (
                    <li key={i} className="truncate" title={s}>
                      {s}
                    </li>
                  ))}
                </ul>
              </div>

              {(selectedCouncil.conflicting_evidence || []).length > 0 && (
                <div className="pt-2 border-t border-[#3A3530]">
                  <div className="font-mono text-[10px] uppercase tracking-wider text-[#FDE68A] mb-1">
                    Disagreements & Warnings
                  </div>
                  <ul className="space-y-0.5 text-[#FDE68A] list-disc list-inside text-[11px]">
                    {selectedCouncil.conflicting_evidence.slice(0, 3).map((c: string, i: number) => (
                      <li key={i} className="truncate" title={c}>
                        {c}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {/* Mini Spatial Preview + Actions */}
            <div className="lg:col-span-3 flex flex-col gap-2">
              <div className="relative h-28 rounded-xl overflow-hidden bg-[#171615] border border-[#3A3530]">
                <img
                  src={`${API_BASE}/api/scenes/${bundle?.scene_id || "scene_urban_T1"}/rgb.png`}
                  alt="Council Parcel Preview"
                  className="absolute inset-0 w-full h-full object-cover opacity-75"
                />
                <svg viewBox={`0 0 ${VIEW_SIZE} ${VIEW_SIZE}`} className="relative z-10 w-full h-full">
                  {parcels.map((p) => {
                    const ring = p.geometry?.coordinates?.[0];
                    if (!ring) return null;
                    const isFoc = p.id === selectedCouncil.parcel_id;
                    return (
                      <polygon
                        key={p.id}
                        points={ringToSvgPoints(ring)}
                        fill={isFoc ? "rgba(253, 230, 138, 0.45)" : "none"}
                        stroke={isFoc ? "#FAF8F3" : "#8A735F"}
                        strokeWidth={isFoc ? 4 : 1.2}
                      />
                    );
                  })}
                </svg>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => onNavigateTab("verification")}
                  className="py-2 px-3 rounded-xl bg-[#FAF8F3] hover:bg-[#EEEAE2] text-[#171615] font-medium text-xs text-center"
                >
                  Verify Parcel →
                </button>
                <button
                  onClick={() => onNavigateTab("workspace")}
                  className="py-2 px-3 rounded-xl bg-[#302C28] hover:bg-[#3A3530] text-[#FAF8F3] font-mono text-xs text-center"
                >
                  Open Map
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
