"use client";

import React, { useState, useEffect } from "react";
import { History, ArrowRight, CheckCircle2, Layers, Clock, User } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

interface TimeMachineViewProps {
  bundle: any;
  selectedParcelId: string | null;
  onSelectParcel: (id: string) => void;
  parcelHistory: any[];
  onNavigateTab: (tab: string) => void;
}

export default function TimeMachineView({
  bundle,
  selectedParcelId,
  onSelectParcel,
  parcelHistory,
  onNavigateTab,
}: TimeMachineViewProps) {
  const [selectedYearIdx, setSelectedYearIdx] = useState<number>(1);
  const parcels: any[] = bundle?.candidate_parcels || [];
  const buildings: any[] = bundle?.buildings || [];
  const roads: any[] = bundle?.roads || [];

  const epochs = [
    { year: "2024", epoch: "T0", scene: "scene_urban_T0", label: "Baseline Survey (T0)" },
    { year: "2025", epoch: "T1", scene: "scene_urban_T1", label: "Active Cadastral Extraction (T1)" },
    { year: "2026", epoch: "T2", scene: "scene_urban_T2", label: "Temporal Growth & Mutation (T2)" },
  ];

  // Sync default selected version when history loads
  const [activeVersionId, setActiveVersionId] = useState<string | null>(null);
  useEffect(() => {
    if (parcelHistory.length > 0) {
      setActiveVersionId(parcelHistory[parcelHistory.length - 1].id);
    }
  }, [parcelHistory]);

  const activeEpoch = epochs[selectedYearIdx] || epochs[1];
  const selectedParcel = parcels.find((p) => p.id === selectedParcelId) || parcels[0] || null;
  const activeVersion =
    parcelHistory.find((v) => v.id === activeVersionId) ||
    parcelHistory[parcelHistory.length - 1] ||
    null;

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
    <div className="space-y-6 animate-page-enter">
      {/* Top Header & Parcel Selector */}
      <div className="bg-[#FAF8F3] border border-[#E4DFD5] rounded-2xl p-6 flex flex-wrap items-center justify-between gap-4 shadow-subtle">
        <div className="space-y-1">
          <div className="text-[11px] font-mono uppercase tracking-widest text-[#6B5748]">
            TEMPORAL CADASTRAL LINEAGE • 2024 → 2025 → 2026
          </div>
          <h2 className="font-editorial text-3xl sm:text-4xl text-[#171615]">
            Parcel Time Machine
          </h2>
          <p className="text-xs text-[#5C554E] max-w-2xl">
            Step smoothly through yearly aerial surveys and PostGIS geometry revisions without reloading. Inspect how parcel boundaries, building footprints, and surveyor edits evolve over time.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <label className="text-xs font-mono text-[#6B5748]">Active Parcel:</label>
          <select
            value={selectedParcelId || ""}
            onChange={(e) => onSelectParcel(e.target.value)}
            className="bg-[#FFFFFF] border border-[#D2C9BC] rounded-xl px-3.5 py-2 text-xs font-mono text-[#171615] shadow-sm"
          >
            {parcels.map((p) => (
              <option key={p.id} value={p.id}>
                {p.id} (v{p.version} • {p.area_sqm?.toFixed(0)} m²)
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Interactive Year Timeline Bar (2024 -> 2025 -> 2026) */}
      <div className="bg-[#24221F] text-[#FAF8F3] rounded-2xl p-5 border border-[#302C28] shadow-editorial">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {epochs.map((ep, idx) => {
            const isSelected = idx === selectedYearIdx;
            return (
              <button
                key={ep.year}
                onClick={() => setSelectedYearIdx(idx)}
                className={`p-4 rounded-xl border text-left transition-all flex items-center justify-between ${
                  isSelected
                    ? "bg-[#FAF8F3] text-[#171615] border-[#FAF8F3] shadow-md scale-[1.01]"
                    : "bg-[#171615] text-[#E6E0D5] border-[#3A3530] hover:border-[#8A735F]"
                }`}
              >
                <div>
                  <div
                    className={`text-[10px] font-mono uppercase ${
                      isSelected ? "text-[#6B5748]" : "text-[#C5AA8C]"
                    }`}
                  >
                    EPOCH {ep.epoch}
                  </div>
                  <div className="font-editorial text-3xl mt-0.5">{ep.year}</div>
                  <div
                    className={`text-xs mt-0.5 ${
                      isSelected ? "text-[#5C554E]" : "text-[#A18A76]"
                    }`}
                  >
                    {ep.label}
                  </div>
                </div>
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center font-mono text-xs ${
                    isSelected
                      ? "bg-[#24221F] text-[#FAF8F3]"
                      : "bg-[#24221F] text-[#A18A76]"
                  }`}
                >
                  {idx + 1}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Spatial State & Version Lineage Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* LEFT: Animated Spatial Viewport for Selected Year */}
        <div className="lg:col-span-7 bg-[#24221F] border border-[#302C28] rounded-2xl p-4 shadow-elevated space-y-3">
          <div className="flex items-center justify-between text-xs font-mono text-[#E6E0D5]">
            <span>
              ACTIVE TEMPORAL STATE: <strong className="text-[#C5AA8C]">{activeEpoch.year} ({activeEpoch.epoch})</strong>
            </span>
            <span>SCENE: {activeEpoch.scene}</span>
          </div>

          <div className="relative w-full aspect-square rounded-xl overflow-hidden bg-[#171615] border border-[#3A3530]">
            <img
              key={activeEpoch.scene}
              src={`${API_BASE}/api/scenes/${activeEpoch.scene}/rgb.png`}
              alt={activeEpoch.scene}
              className="absolute inset-0 w-full h-full object-cover opacity-85 transition-opacity duration-300"
            />

            <svg viewBox={`0 0 ${VIEW_SIZE} ${VIEW_SIZE}`} className="relative z-10 w-full h-full">
              {/* Roads */}
              {roads.map((r) => {
                const pts = r.geometry?.coordinates || [];
                if (pts.length < 2) return null;
                const [x1, y1] = lonLatToSvg(pts[0][0], pts[0][1]);
                const [x2, y2] = lonLatToSvg(pts[pts.length - 1][0], pts[pts.length - 1][1]);
                return (
                  <line
                    key={r.id}
                    x1={x1}
                    y1={y1}
                    x2={x2}
                    y2={y2}
                    stroke="#FAF8F3"
                    strokeWidth="1.5"
                    strokeDasharray="6 4"
                    opacity="0.7"
                  />
                );
              })}

              {/* All Scene Parcels */}
              {parcels.map((p) => {
                const ring = p.geometry?.coordinates?.[0];
                if (!ring) return null;
                const isFocused = p.id === selectedParcelId;
                return (
                  <polygon
                    key={p.id}
                    points={ringToSvgPoints(ring)}
                    onClick={() => onSelectParcel(p.id)}
                    fill={
                      isFocused
                        ? "rgba(197, 170, 140, 0.42)"
                        : "rgba(250, 248, 243, 0.12)"
                    }
                    stroke={isFocused ? "#FAF8F3" : "#A18A76"}
                    strokeWidth={isFocused ? 3.2 : 1.4}
                    className="cursor-pointer transition-all duration-300"
                  />
                );
              })}

              {/* Selected Version Geometry Overlay */}
              {activeVersion?.geometry?.coordinates?.[0] && (
                <polygon
                  points={ringToSvgPoints(activeVersion.geometry.coordinates[0])}
                  fill="rgba(61, 107, 82, 0.35)"
                  stroke="#A7F3D0"
                  strokeWidth={3}
                  strokeDasharray="5 3"
                />
              )}

              {/* Buildings */}
              {buildings.map((b) => {
                const ring = b.geometry?.coordinates?.[0];
                if (!ring) return null;
                return (
                  <polygon
                    key={b.id}
                    points={ringToSvgPoints(ring)}
                    fill="rgba(184, 154, 120, 0.45)"
                    stroke="#C5AA8C"
                    strokeWidth="1.3"
                  />
                );
              })}
            </svg>
          </div>
        </div>

        {/* RIGHT: Version History Timeline Cards */}
        <div className="lg:col-span-5 space-y-4">
          <div className="bg-[#FAF8F3] border border-[#E4DFD5] rounded-2xl p-5 space-y-4 shadow-subtle">
            <div className="flex items-center justify-between border-b border-[#E4DFD5] pb-3">
              <div>
                <h3 className="font-editorial text-2xl text-[#171615]">
                  PostGIS Version Lineage
                </h3>
                <p className="text-xs text-[#5C554E] font-mono">
                  {selectedParcel?.id} ({parcelHistory.length} recorded snapshots)
                </p>
              </div>
              <button
                onClick={() => onNavigateTab("workspace")}
                className="px-3 py-1.5 rounded-xl bg-[#24221F] text-[#FAF8F3] text-xs font-mono"
              >
                Edit in Map →
              </button>
            </div>

            <div className="space-y-3 max-h-[540px] overflow-y-auto pr-1">
              {parcelHistory.map((ver) => {
                const isVerActive = ver.id === activeVersion?.id;
                return (
                  <div
                    key={ver.id}
                    onClick={() => {
                      setActiveVersionId(ver.id);
                      if (ver.temporal_epoch === "T0") setSelectedYearIdx(0);
                      else if (ver.temporal_epoch === "T1") setSelectedYearIdx(1);
                      else if (ver.temporal_epoch === "T2") setSelectedYearIdx(2);
                    }}
                    className={`p-4 rounded-xl border cursor-pointer transition-all space-y-2.5 ${
                      isVerActive
                        ? "bg-[#FFFFFF] border-[#24221F] shadow-editorial"
                        : "bg-[#F4F1EA] border-[#E4DFD5] hover:border-[#8A735F]"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-xs font-bold text-[#171615]">
                        Version {ver.version_number} • {ver.temporal_epoch}
                      </span>
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold ${
                          ver.status === "HUMAN_VERIFIED"
                            ? "bg-[#EBF2EE] text-[#3D6B52] border border-[#BDD4C6]"
                            : "bg-[#EEEAE2] text-[#6B5748]"
                        }`}
                      >
                        {ver.status}
                      </span>
                    </div>

                    <div className="grid grid-cols-3 gap-2 text-[11px] font-mono bg-[#FAF8F3] p-2.5 rounded-lg border border-[#E4DFD5]">
                      <div>
                        <span className="text-[#8C8277] block text-[10px]">Area</span>
                        <span className="font-semibold text-[#171615]">
                          {ver.area_sqm?.toFixed(1)} m²
                        </span>
                      </div>
                      <div>
                        <span className="text-[#8C8277] block text-[10px]">Land Use</span>
                        <span className="font-semibold text-[#6B5748]">{ver.land_use_class}</span>
                      </div>
                      <div>
                        <span className="text-[#8C8277] block text-[10px]">Confidence</span>
                        <span className="font-semibold text-[#3D6B52]">
                          {(ver.confidence * 100).toFixed(0)}%
                        </span>
                      </div>
                    </div>

                    <div className="text-xs text-[#5C554E] leading-relaxed">
                      {ver.change_summary}
                    </div>

                    <div className="text-[10px] font-mono text-[#8C8277] flex items-center justify-between pt-1 border-t border-[#E4DFD5]">
                      <span>Actor: {ver.actor}</span>
                      <span>Buildings: {ver.building_count}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
