"use client";

import React, { useState, useRef } from "react";
import { GitCompare, ArrowRight, Layers, Calendar, CheckCircle2, Eye } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

interface CompareSliderViewProps {
  bundle: any;
  onSelectParcelAndNavigate: (parcelId: string, tab: string) => void;
}

export default function CompareSliderView({
  bundle,
  onSelectParcelAndNavigate,
}: CompareSliderViewProps) {
  const [sliderPos, setSliderPos] = useState<number>(50);
  const [rightEpoch, setRightEpoch] = useState<"scene_urban_T1" | "scene_urban_T2">("scene_urban_T2");
  const [activeFilter, setActiveFilter] = useState<string>("ALL");
  const [showVectorOverlay, setShowVectorOverlay] = useState<boolean>(true);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [isDragging, setIsDragging] = useState<boolean>(false);

  const changes: any[] = bundle?.changes || [];
  const parcels: any[] = bundle?.candidate_parcels || [];
  const buildings: any[] = bundle?.buildings || [];

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

  const handleMove = (clientX: number) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const pct = ((clientX - rect.left) / rect.width) * 100;
    setSliderPos(Math.min(Math.max(pct, 4), 96));
  };

  const filteredChanges = changes.filter((c) => {
    if (activeFilter === "ALL") return true;
    return c.change_type.toUpperCase().includes(activeFilter);
  });

  return (
    <div className="space-y-6 animate-page-enter">
      {/* Header */}
      <div className="bg-[#FAF8F3] border border-[#E4DFD5] rounded-2xl p-6 flex flex-wrap items-center justify-between gap-4 shadow-subtle">
        <div className="space-y-1">
          <div className="text-[11px] font-mono uppercase tracking-widest text-[#6B5748]">
            MULTI-TEMPORAL ORTHO & VECTOR COMPARISON • SYNTHETIC DEMO DATA
          </div>
          <h2 className="font-editorial text-3xl sm:text-4xl text-[#171615]">
            Cadastral Change Detection
          </h2>
          <p className="text-xs text-[#5C554E] max-w-2xl">
            Drag the comparison divider across epochs to inspect new building construction, parcel subdivisions, road corridor expansions, and boundary shifts between 2024 (T0) and 2026 (T2).
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2 text-xs">
          <button
            onClick={() => setShowVectorOverlay((v) => !v)}
            className={`px-3 py-1.5 rounded-xl font-mono border transition-colors ${
              showVectorOverlay
                ? "bg-[#24221F] text-[#FAF8F3] border-[#24221F]"
                : "bg-[#F4F1EA] text-[#6B5748] border-[#D2C9BC]"
            }`}
          >
            {showVectorOverlay ? "✓ Vector Deltas Visible" : "Show Vector Deltas"}
          </button>
          <div className="flex items-center bg-[#EEEAE2] p-1 rounded-xl border border-[#D2C9BC]">
            {(
              [
                { id: "scene_urban_T1", label: "T0 vs T1 (2025)" },
                { id: "scene_urban_T2", label: "T0 vs T2 (2026)" },
              ] as const
            ).map((ep) => (
              <button
                key={ep.id}
                onClick={() => setRightEpoch(ep.id)}
                className={`px-3 py-1 rounded-lg font-mono text-[11px] transition-all ${
                  rightEpoch === ep.id
                    ? "bg-[#FAF8F3] text-[#171615] font-semibold shadow-sm"
                    : "text-[#6B5748]"
                }`}
              >
                {ep.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Category Filter Pills */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          {[
            { id: "ALL", label: `All Detected Changes (${changes.length})` },
            { id: "BUILDING", label: "New / Modified Building" },
            { id: "LAND_USE", label: "Changed Parcel / Land Use" },
            { id: "BOUNDARY", label: "Boundary Shift" },
          ].map((f) => (
            <button
              key={f.id}
              onClick={() => setActiveFilter(f.id)}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-mono transition-all ${
                activeFilter === f.id
                  ? "bg-[#24221F] text-[#FAF8F3]"
                  : "bg-[#FAF8F3] text-[#5C554E] border border-[#E4DFD5] hover:border-[#8A735F]"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        <div className="text-xs font-mono text-[#6B5748]">
          Split Position: {sliderPos.toFixed(0)}%
        </div>
      </div>

      {/* Main Comparison Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* LEFT/CENTER: Draggable Before / After Viewport */}
        <div className="lg:col-span-7 bg-[#24221F] border border-[#302C28] rounded-2xl p-4 shadow-elevated space-y-4">
          <div
            ref={containerRef}
            onMouseDown={() => setIsDragging(true)}
            onMouseUp={() => setIsDragging(false)}
            onMouseLeave={() => setIsDragging(false)}
            onMouseMove={(e) => isDragging && handleMove(e.clientX)}
            onTouchMove={(e) => handleMove(e.touches[0].clientX)}
            onClick={(e) => handleMove(e.clientX)}
            className="relative w-full aspect-square rounded-xl overflow-hidden select-none cursor-ew-resize border border-[#3A3530] bg-[#171615]"
          >
            {/* FULL UNDERLAY: AFTER EPOCH (T1 or T2) */}
            <img
              src={`${API_BASE}/api/scenes/${rightEpoch}/rgb.png`}
              alt="After Epoch Ortho"
              className="absolute inset-0 w-full h-full object-cover"
            />

            {/* Vector Overlay on After Image */}
            {showVectorOverlay && (
              <svg viewBox={`0 0 ${VIEW_SIZE} ${VIEW_SIZE}`} className="absolute inset-0 w-full h-full pointer-events-none">
                {parcels.map((p) => {
                  const ring = p.geometry?.coordinates?.[0];
                  if (!ring) return null;
                  return (
                    <polygon
                      key={p.id}
                      points={ringToSvgPoints(ring)}
                      fill="none"
                      stroke="#FAF8F3"
                      strokeWidth="1.5"
                      opacity="0.55"
                    />
                  );
                })}
                {buildings.map((b) => {
                  const ring = b.geometry?.coordinates?.[0];
                  if (!ring) return null;
                  return (
                    <polygon
                      key={b.id}
                      points={ringToSvgPoints(ring)}
                      fill="rgba(184, 154, 120, 0.35)"
                      stroke="#C5AA8C"
                      strokeWidth="1.5"
                    />
                  );
                })}
                {filteredChanges.map((chg) => {
                  const ring = chg.geometry?.coordinates?.[0];
                  if (!ring) return null;
                  return (
                    <polygon
                      key={chg.id}
                      points={ringToSvgPoints(ring)}
                      fill="rgba(158, 62, 55, 0.45)"
                      stroke="#FCA5A5"
                      strokeWidth="2.8"
                    />
                  );
                })}
              </svg>
            )}

            {/* CLIPPED OVERLAY: BEFORE EPOCH (T0 - 2024) */}
            <div
              style={{ clipPath: `inset(0 ${100 - sliderPos}% 0 0)` }}
              className="absolute inset-0 w-full h-full"
            >
              <img
                src={`${API_BASE}/api/scenes/scene_urban_T0/rgb.png`}
                alt="Before Epoch T0 Ortho"
                className="absolute inset-0 w-full h-full object-cover"
              />
              {showVectorOverlay && (
                <svg viewBox={`0 0 ${VIEW_SIZE} ${VIEW_SIZE}`} className="absolute inset-0 w-full h-full pointer-events-none">
                  {parcels.map((p) => {
                    const ring = p.geometry?.coordinates?.[0];
                    if (!ring) return null;
                    return (
                      <polygon
                        key={p.id}
                        points={ringToSvgPoints(ring)}
                        fill="none"
                        stroke="#C5AA8C"
                        strokeWidth="1.4"
                        strokeDasharray="4 3"
                        opacity="0.65"
                      />
                    );
                  })}
                </svg>
              )}
            </div>

            {/* Epoch Labels */}
            <div className="absolute top-3 left-3 px-3 py-1 rounded-lg bg-[#171615]/90 border border-[#3A3530] text-[11px] font-mono text-[#FAF8F3]">
              BEFORE: T0 (2024 Baseline)
            </div>
            <div className="absolute top-3 right-3 px-3 py-1 rounded-lg bg-[#171615]/90 border border-[#6B5748] text-[11px] font-mono text-[#C5AA8C]">
              AFTER: {rightEpoch === "scene_urban_T2" ? "T2 (2026 Current)" : "T1 (2025 Survey)"}
            </div>

            {/* Vertical Divider Handle */}
            <div
              style={{ left: `${sliderPos}%` }}
              className="absolute top-0 bottom-0 w-0.5 bg-[#FAF8F3] shadow-[0_0_12px_rgba(0,0,0,0.6)] pointer-events-none"
            >
              <div className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-9 h-9 rounded-full bg-[#FAF8F3] border-2 border-[#24221F] shadow-lg flex items-center justify-center text-[#171615]">
                <GitCompare className="w-4 h-4" />
              </div>
            </div>
          </div>

          {/* Bottom Timeline Scrubber */}
          <div className="bg-[#171615] border border-[#3A3530] rounded-xl p-3.5 flex items-center justify-between gap-4 text-xs font-mono text-[#E6E0D5]">
            <div className="flex items-center gap-2">
              <Calendar className="w-4 h-4 text-[#C5AA8C]" />
              <span>TEMPORAL EPOCH TIMELINE</span>
            </div>
            <div className="flex items-center gap-3">
              {[
                { ep: "T0", yr: "2024", desc: "Baseline" },
                { ep: "T1", yr: "2025", desc: "Mid-Survey" },
                { ep: "T2", yr: "2026", desc: "Latest Ortho" },
              ].map((item, i) => (
                <React.Fragment key={item.ep}>
                  <button
                    onClick={() =>
                      setRightEpoch(item.ep === "T1" ? "scene_urban_T1" : "scene_urban_T2")
                    }
                    className={`px-3 py-1 rounded-lg border transition-colors ${
                      (item.ep === "T0") ||
                      (item.ep === "T1" && rightEpoch === "scene_urban_T1") ||
                      (item.ep === "T2" && rightEpoch === "scene_urban_T2")
                        ? "bg-[#302C28] border-[#C5AA8C] text-[#FAF8F3]"
                        : "bg-[#24221F] border-[#3A3530] text-[#A18A76]"
                    }`}
                  >
                    {item.yr} ({item.ep})
                  </button>
                  {i < 2 && <span className="text-[#6B5748]">→</span>}
                </React.Fragment>
              ))}
            </div>
          </div>
        </div>

        {/* RIGHT: Detected Change Events List */}
        <div className="lg:col-span-5 space-y-4">
          <div className="bg-[#FAF8F3] border border-[#E4DFD5] rounded-2xl p-5 space-y-4 shadow-subtle">
            <div className="flex items-center justify-between border-b border-[#E4DFD5] pb-3">
              <div>
                <h3 className="font-editorial text-2xl text-[#171615]">
                  Detected Spatial Mutations
                </h3>
                <p className="text-xs text-[#5C554E]">
                  Automated multi-epoch polygon & raster diff analysis
                </p>
              </div>
              <span className="px-2.5 py-1 rounded-lg bg-[#EEEAE2] font-mono text-xs font-semibold text-[#6B5748]">
                {filteredChanges.length} Events
              </span>
            </div>

            <div className="space-y-3 max-h-[540px] overflow-y-auto pr-1">
              {filteredChanges.map((c: any) => (
                <div
                  key={c.id}
                  className="p-4 rounded-xl bg-[#F4F1EA] border border-[#E4DFD5] hover:border-[#B89A78] transition-all space-y-2.5"
                >
                  <div className="flex items-center justify-between">
                    <span className="px-2.5 py-0.5 rounded bg-[#F9ECEB] border border-[#E5B8B5] text-[#9E3E37] font-mono text-[10px] font-semibold">
                      {c.change_type} ({c.from_epoch} → {c.to_epoch})
                    </span>
                    <span className="font-mono text-xs text-[#6B5748]">
                      Conf: {((c.confidence || 0.88) * 100).toFixed(0)}%
                    </span>
                  </div>

                  <div className="font-mono text-xs font-bold text-[#171615]">
                    Parcel: {c.parcel_id}
                  </div>
                  <p className="text-xs text-[#5C554E] leading-relaxed">{c.summary}</p>

                  <div className="pt-1 flex items-center justify-between gap-2">
                    <button
                      onClick={() => onSelectParcelAndNavigate(c.parcel_id, "timemachine")}
                      className="px-3 py-1.5 rounded-lg bg-[#24221F] text-[#FAF8F3] text-xs font-mono flex items-center gap-1.5 hover:bg-[#171615]"
                    >
                      <span>Inspect in Time Machine</span>
                      <ArrowRight className="w-3 h-3" />
                    </button>
                    <button
                      onClick={() => onSelectParcelAndNavigate(c.parcel_id, "workspace")}
                      className="px-3 py-1.5 rounded-lg bg-[#FAF8F3] border border-[#D2C9BC] text-[#24221F] text-xs font-mono hover:bg-[#EEEAE2]"
                    >
                      View on Map
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
