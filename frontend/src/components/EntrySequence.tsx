"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  ArrowRight,
  Compass,
  Layers,
  ShieldCheck,
  CheckCircle2,
  MapPin,
  Cpu,
  Scan,
  Sparkles,
  Lock,
  UserCheck,
  Eye,
  GitCompare,
} from "lucide-react";

export type AppEntryStage = "INTRO_LOADING" | "WELCOME" | "LOGIN" | "WORKSPACE_OPENING" | "APP_READY";

export interface DemoUserProfile {
  name: string;
  role: "Surveyor" | "Demo User" | "Administrator";
  operatorId: string;
  email: string;
  department: string;
  badge: string;
}

export const DEMO_PROFILES: Record<string, DemoUserProfile> = {
  Surveyor: {
    name: "Arjun Mehta",
    role: "Surveyor",
    operatorId: "Surveyor_Verifier_01",
    email: "surveyor.verifier@aerocadastre.demo",
    department: "Cadastral Field Verification Unit • Sector 43N",
    badge: "LEAD SURVEYOR",
  },
  "Demo User": {
    name: "SIH Evaluation Reviewer",
    role: "Demo User",
    operatorId: "SIH26012_Reviewer",
    email: "reviewer@aerocadastre.demo",
    department: "DoLR / MoRD Technical Review Panel",
    badge: "DEMO EVALUATOR",
  },
  Administrator: {
    name: "Dr. Kavita Rao",
    role: "Administrator",
    operatorId: "GeoAI_Admin_01",
    email: "admin.geoai@aerocadastre.demo",
    department: "Spatial Systems & Neural Pipeline Ops",
    badge: "SYSTEM ADMIN",
  },
};

interface EntrySequenceProps {
  stage: AppEntryStage;
  setStage: (stage: AppEntryStage) => void;
  selectedProfile: DemoUserProfile;
  setSelectedProfile: (profile: DemoUserProfile) => void;
  dashboardMetrics?: any;
  sceneId: string;
}

export default function EntrySequence({
  stage,
  setStage,
  selectedProfile,
  setSelectedProfile,
  dashboardMetrics,
  sceneId,
}: EntrySequenceProps) {
  const [heroLayerMode, setHeroLayerMode] = useState<"composite" | "boundaries" | "council" | "temporal">("composite");
  const [hoveredHeroParcel, setHoveredHeroParcel] = useState<string>("P-002");
  const [parallax, setParallax] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [emailInput, setEmailInput] = useState<string>(selectedProfile.email);
  const [passwordInput, setPasswordInput] = useState<string>("••••••••••••••••");
  const [openingStep, setOpeningStep] = useState<number>(0);
  const showcaseRef = useRef<HTMLDivElement | null>(null);

  // Stage 1: Initial Website Loading Experience (~1.2s fast & smooth)
  useEffect(() => {
    if (stage === "INTRO_LOADING") {
      const timer = setTimeout(() => {
        setStage("WELCOME");
      }, 1250);
      return () => clearTimeout(timer);
    }
  }, [stage, setStage]);

  // Stage 4: Application Opening Experience (~0.95s fast & smooth)
  useEffect(() => {
    if (stage === "WORKSPACE_OPENING") {
      setOpeningStep(0);
      const intervals = [120, 260, 400, 540, 680, 820].map((ms, idx) =>
        setTimeout(() => setOpeningStep(idx + 1), ms)
      );
      const doneTimer = setTimeout(() => {
        setStage("APP_READY");
      }, 980);
      return () => {
        intervals.forEach(clearTimeout);
        clearTimeout(doneTimer);
      };
    }
  }, [stage, setStage]);

  const handleHeroMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const nx = ((e.clientX - rect.left) / rect.width - 0.5) * 10;
    const ny = ((e.clientY - rect.top) / rect.height - 0.5) * 10;
    setParallax({ x: Number(nx.toFixed(2)), y: Number(ny.toFixed(2)) });
  };

  const handleSelectRole = (roleKey: "Surveyor" | "Demo User" | "Administrator") => {
    const prof = DEMO_PROFILES[roleKey];
    setSelectedProfile(prof);
    setEmailInput(prof.email);
  };

  const handleLoginSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setStage("WORKSPACE_OPENING");
  };

  // ============================================================================
  // 1. INITIAL WEBSITE LOADING EXPERIENCE (~1.2s)
  // ============================================================================
  if (stage === "INTRO_LOADING") {
    return (
      <div
        onClick={() => setStage("WELCOME")}
        className="fixed inset-0 z-50 bg-[#171615] text-[#F4F1EA] flex flex-col items-center justify-between p-8 select-none cursor-pointer overflow-hidden"
      >
        {/* Top subtle coordinate bar */}
        <div className="w-full max-w-6xl flex items-center justify-between text-[11px] font-mono tracking-widest text-[#A18A76] opacity-80">
          <span>SIH26012 • DOLR / MORD PROTOTYPE</span>
          <span>12°58&apos;20.6&quot;N 77°35&apos;34.1&quot;E • EPSG:32643</span>
        </div>

        {/* Center animated aerial & parcel geometry */}
        <div className="relative flex flex-col items-center max-w-xl w-full">
          <div className="relative w-64 h-64 mb-8 rounded-2xl overflow-hidden border border-[#302C28] bg-[#24221F] shadow-elevated flex items-center justify-center">
            {/* Faint aerial ortho texture */}
            <img
              src="/scenes/scene_urban_T1/rgb.png"
              alt="Aerial Ortho Texture"
              className="absolute inset-0 w-full h-full object-cover opacity-25 scale-105 transition-transform duration-1000"
            />
            {/* Coordinate grid & parcel lines drawing themselves */}
            <svg viewBox="0 0 240 240" className="relative z-10 w-full h-full p-4">
              <g stroke="#8A735F" strokeWidth="0.5" opacity="0.35" strokeDasharray="3 3">
                <line x1="60" y1="0" x2="60" y2="240" />
                <line x1="120" y1="0" x2="120" y2="240" />
                <line x1="180" y1="0" x2="180" y2="240" />
                <line x1="0" y1="60" x2="240" y2="60" />
                <line x1="0" y1="120" x2="240" y2="120" />
                <line x1="0" y1="180" x2="240" y2="180" />
              </g>
              {/* Animated parcel boundaries */}
              <polygon
                points="24,24 108,24 108,96 24,96"
                fill="rgba(184, 154, 120, 0.08)"
                stroke="#C5AA8C"
                strokeWidth="1.5"
                className="animate-draw-parcel"
              />
              <polygon
                points="116,24 214,24 214,104 116,104"
                fill="rgba(61, 107, 82, 0.12)"
                stroke="#FAF8F3"
                strokeWidth="1.5"
                className="animate-draw-parcel"
              />
              <polygon
                points="24,106 108,106 108,214 24,214"
                fill="rgba(184, 154, 120, 0.06)"
                stroke="#B89A78"
                strokeWidth="1.5"
                className="animate-draw-parcel"
              />
              <polygon
                points="116,114 214,114 214,214 116,214"
                fill="rgba(184, 154, 120, 0.1)"
                stroke="#C5AA8C"
                strokeWidth="1.5"
                strokeDasharray="4 2"
                className="animate-draw-parcel"
              />
              {/* Vertex nodes */}
              {[
                [24, 24],
                [108, 24],
                [116, 104],
                [214, 104],
                [108, 214],
                [214, 214],
              ].map(([cx, cy], idx) => (
                <circle key={idx} cx={cx} cy={cy} r="2.5" fill="#FAF8F3" />
              ))}
            </svg>
          </div>

          <div className="text-center space-y-2 animate-page-enter">
            <h1 className="text-3xl md:text-4xl font-editorial tracking-wide text-[#FAF8F3]">
              AEROCADASTRE
            </h1>
            <p className="text-[11px] font-mono uppercase tracking-[0.28em] text-[#C5AA8C]">
              AI-Assisted Cadastral Intelligence
            </p>
          </div>
        </div>

        {/* Bottom hint */}
        <div className="text-[11px] font-mono text-[#8A735F]">
          INITIALIZING SPATIAL GEOMETRY ENGINE...
        </div>
      </div>
    );
  }

  // ============================================================================
  // 2. WELCOME / LANDING PAGE
  // ============================================================================
  if (stage === "WELCOME") {
    const heroParcels = [
      {
        id: "P-001",
        points: "35,32 215,32 215,195 35,195",
        labelX: 125,
        labelY: 112,
        area: "1,420 m²",
        conf: "94%",
        type: "VISIBLE BOUNDARY",
        verdict: "ACCEPT_FOR_REVIEW",
        fill: "rgba(61, 107, 82, 0.22)",
        stroke: "#FAF8F3",
      },
      {
        id: "P-002",
        points: "225,32 455,32 455,195 225,195",
        labelX: 340,
        labelY: 112,
        area: "1,865 m²",
        conf: "82%",
        type: "INFERRED / GIS CONFLICT",
        verdict: "REQUIRES VERIFICATION",
        fill: "rgba(180, 120, 40, 0.28)",
        stroke: "#FDE68A",
      },
      {
        id: "P-003",
        points: "468,32 685,32 685,235 468,235",
        labelX: 576,
        labelY: 132,
        area: "2,110 m²",
        conf: "91%",
        type: "VISIBLE BOUNDARY",
        verdict: "ACCEPT_FOR_REVIEW",
        fill: "rgba(61, 107, 82, 0.20)",
        stroke: "#FAF8F3",
      },
      {
        id: "P-004",
        points: "35,205 215,205 215,365 35,365",
        labelX: 125,
        labelY: 285,
        area: "1,390 m²",
        conf: "89%",
        type: "VISIBLE BOUNDARY",
        verdict: "ACCEPT_FOR_REVIEW",
        fill: "rgba(184, 154, 120, 0.22)",
        stroke: "#FAF8F3",
      },
      {
        id: "P-005",
        points: "225,205 455,205 455,365 225,365",
        labelX: 340,
        labelY: 285,
        area: "1,780 m²",
        conf: "76%",
        type: "BUILDING ENCROACHMENT",
        verdict: "FIELD VISIT PRIORITY",
        fill: "rgba(168, 66, 59, 0.26)",
        stroke: "#FCA5A5",
      },
      {
        id: "P-006",
        points: "35,435 285,435 285,680 35,680",
        labelX: 160,
        labelY: 558,
        area: "2,440 m²",
        conf: "95%",
        type: "HUMAN VERIFIED",
        verdict: "VERIFIED RECORD",
        fill: "rgba(61, 107, 82, 0.26)",
        stroke: "#A7F3D0",
      },
      {
        id: "P-007",
        points: "310,435 685,435 685,680 310,680",
        labelX: 497,
        labelY: 558,
        area: "3,120 m²",
        conf: "88%",
        type: "VISIBLE BOUNDARY",
        verdict: "ACCEPT_FOR_REVIEW",
        fill: "rgba(184, 154, 120, 0.20)",
        stroke: "#FAF8F3",
      },
    ];

    const activeHeroParcel = heroParcels.find((p) => p.id === hoveredHeroParcel) || heroParcels[1];

    return (
      <div className="min-h-screen bg-[#F4F1EA] text-[#171615] flex flex-col selection:bg-[#B89A78]/30">
        {/* TOP EDITORIAL NAVBAR */}
        <header className="sticky top-0 z-30 bg-[#F4F1EA]/90 backdrop-blur-md border-b border-[#E4DFD5]">
          <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-[#24221F] text-[#FAF8F3] flex items-center justify-center font-editorial text-lg">
                A
              </div>
              <div className="flex items-center gap-2.5">
                <span className="font-semibold tracking-tight text-sm text-[#171615]">
                  AEROCADASTRE
                </span>
                <span className="hidden sm:inline-block text-[10px] font-mono uppercase tracking-wider px-2 py-0.5 rounded bg-[#EEEAE2] text-[#6B5748] border border-[#D2C9BC]">
                  SIH26012 • GeoAI Platform
                </span>
              </div>
            </div>

            <nav className="hidden md:flex items-center gap-8 text-xs font-medium text-[#5C554E]">
              <button
                onClick={() => showcaseRef.current?.scrollIntoView({ behavior: "smooth" })}
                className="hover:text-[#171615] transition-colors"
              >
                Spatial Architecture
              </button>
              <button
                onClick={() => showcaseRef.current?.scrollIntoView({ behavior: "smooth" })}
                className="hover:text-[#171615] transition-colors"
              >
                6-Agent Council
              </button>
              <button
                onClick={() => showcaseRef.current?.scrollIntoView({ behavior: "smooth" })}
                className="hover:text-[#171615] transition-colors"
              >
                Surveyor Verification
              </button>
            </nav>

            <div className="flex items-center gap-3">
              <button
                onClick={() => setStage("LOGIN")}
                className="px-3.5 py-1.5 rounded-lg text-xs font-medium text-[#24221F] hover:bg-[#EEEAE2] transition-colors"
              >
                Sign In
              </button>
              <button
                onClick={() => setStage("LOGIN")}
                className="btn-primary-dark px-4 py-2 rounded-lg text-xs font-medium flex items-center gap-1.5"
              >
                <span>Enter AeroCadastre</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </header>

        {/* HERO SECTION */}
        <section className="relative pt-14 pb-20 px-6 max-w-7xl mx-auto w-full">
          {/* Editorial Headline Block */}
          <div className="max-w-3xl mx-auto text-center space-y-6 animate-page-enter">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#FAF8F3] border border-[#D2C9BC] text-[11px] font-mono text-[#6B5748]">
              <span className="w-1.5 h-1.5 rounded-full bg-[#3D6B52]" />
              <span>AI-ASSISTED CADASTRAL INTELLIGENCE • SYNTHETIC DEMO DATA</span>
            </div>

            <h1 className="font-editorial text-5xl sm:text-6xl md:text-7xl text-[#171615] leading-[1.04] tracking-tight">
              See the city differently.
            </h1>

            <p className="text-base sm:text-lg text-[#5C554E] max-w-2xl mx-auto leading-relaxed font-normal">
              AI-assisted urban parcel mapping and cadastral intelligence for faster, more reliable field verification.
            </p>

            <div className="pt-2 flex flex-wrap items-center justify-center gap-3.5">
              <button
                onClick={() => setStage("LOGIN")}
                className="btn-primary-dark px-6 py-3 rounded-xl text-sm font-medium flex items-center gap-2 shadow-editorial"
              >
                <span>Enter AeroCadastre</span>
                <ArrowRight className="w-4 h-4" />
              </button>
              <button
                onClick={() => showcaseRef.current?.scrollIntoView({ behavior: "smooth" })}
                className="btn-secondary-warm px-6 py-3 rounded-xl text-sm font-medium"
              >
                Explore the Platform
              </button>
            </div>
          </div>

          {/* LARGE VISUAL HERO AREA */}
          <div
            onMouseMove={handleHeroMouseMove}
            onMouseLeave={() => setParallax({ x: 0, y: 0 })}
            className="mt-14 rounded-2xl bg-[#24221F] p-3 sm:p-5 border border-[#302C28] shadow-elevated transition-transform duration-300"
          >
            {/* Top Window Bar inside Hero Visual */}
            <div className="flex flex-wrap items-center justify-between gap-3 pb-3.5 mb-3.5 border-b border-[#3A3530] text-xs text-[#E6E0D5]">
              <div className="flex items-center gap-3">
                <span className="font-mono text-[11px] px-2.5 py-0.5 rounded bg-[#302C28] text-[#C5AA8C] border border-[#6B5748]/50">
                  SCENE: {sceneId}
                </span>
                <span className="hidden sm:inline font-mono text-[11px] text-[#A18A76]">
                  CRS: EPSG:4326 / UTM ZONE 43N (EPSG:32643)
                </span>
              </div>

              {/* Layer Switcher Pills */}
              <div className="flex items-center gap-1.5 bg-[#171615] p-1 rounded-lg border border-[#3A3530]">
                {[
                  { id: "composite", label: "Ortho + Parcels" },
                  { id: "boundaries", label: "Visible vs Inferred" },
                  { id: "council", label: "6-Agent Evidence" },
                  { id: "temporal", label: "2024 → 2026 Shift" },
                ].map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setHeroLayerMode(tab.id as any)}
                    className={`px-2.5 py-1 rounded text-[11px] font-medium transition-all ${
                      heroLayerMode === tab.id
                        ? "bg-[#FAF8F3] text-[#171615] shadow-sm"
                        : "text-[#A18A76] hover:text-[#FAF8F3]"
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Main Visual Canvas + Live Telemetry Overlay */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-stretch">
              {/* Left/Center Aerial & Cadastral Geometry Viewport */}
              <div className="lg:col-span-8 relative rounded-xl overflow-hidden bg-[#171615] border border-[#3A3530] min-h-[380px] sm:min-h-[460px] flex items-center justify-center">
                {/* Real Synthetic Drone Ortho Imagery from Project */}
                <img
                  src={
                    heroLayerMode === "temporal"
                      ? "/scenes/scene_urban_T2/rgb.png"
                      : "/scenes/scene_urban_T1/rgb.png"
                  }
                  alt="AeroCadastre Urban Ortho Scene"
                  style={{
                    transform: `translate3d(${parallax.x * -0.6}px, ${parallax.y * -0.6}px, 0) scale(1.03)`,
                  }}
                  className="absolute inset-0 w-full h-full object-cover opacity-80 transition-transform duration-300 ease-out"
                />

                {/* Subtle Warm Vignette & Cadastral SVG Vector Overlay */}
                <svg
                  viewBox="0 0 720 720"
                  style={{
                    transform: `translate3d(${parallax.x * 0.4}px, ${parallax.y * 0.4}px, 0)`,
                  }}
                  className="relative z-10 w-full h-full max-h-[480px] transition-transform duration-300 ease-out"
                >
                  {/* Coordinate Graticule */}
                  <g stroke="#FAF8F3" strokeWidth="0.6" opacity="0.22" strokeDasharray="4 4">
                    <line x1="180" y1="0" x2="180" y2="720" />
                    <line x1="360" y1="0" x2="360" y2="720" />
                    <line x1="540" y1="0" x2="540" y2="720" />
                    <line x1="0" y1="180" x2="720" y2="180" />
                    <line x1="0" y1="360" x2="720" y2="360" />
                    <line x1="0" y1="540" x2="720" y2="540" />
                  </g>

                  {/* Extracted Road Corridors */}
                  <g opacity="0.85">
                    <line x1="0" y1="400" x2="720" y2="400" stroke="#24221F" strokeWidth="26" />
                    <line
                      x1="0"
                      y1="400"
                      x2="720"
                      y2="400"
                      stroke="#C5AA8C"
                      strokeWidth="1.5"
                      strokeDasharray="8 6"
                    />
                    <line x1="278" y1="0" x2="278" y2="720" stroke="#24221F" strokeWidth="20" />
                    <line
                      x1="278"
                      y1="0"
                      x2="278"
                      y2="720"
                      stroke="#C5AA8C"
                      strokeWidth="1.2"
                      strokeDasharray="8 6"
                    />
                  </g>

                  {/* Interactive Candidate Parcel Polygons */}
                  {heroParcels.map((p) => {
                    const isHovered = p.id === hoveredHeroParcel;
                    return (
                      <g
                        key={p.id}
                        onMouseEnter={() => setHoveredHeroParcel(p.id)}
                        onClick={() => setHoveredHeroParcel(p.id)}
                        className="cursor-pointer transition-opacity"
                      >
                        <polygon
                          points={p.points}
                          fill={isHovered ? "rgba(250, 248, 243, 0.28)" : p.fill}
                          stroke={isHovered ? "#FAF8F3" : p.stroke}
                          strokeWidth={isHovered ? 3 : 1.8}
                          strokeDasharray={
                            heroLayerMode === "boundaries" && p.id === "P-002" ? "7 4" : undefined
                          }
                        />
                        <rect
                          x={p.labelX - 30}
                          y={p.labelY - 12}
                          width="60"
                          height="22"
                          rx="4"
                          fill="#171615"
                          fillOpacity="0.82"
                          stroke={isHovered ? "#C5AA8C" : "#3A3530"}
                          strokeWidth="1"
                        />
                        <text
                          x={p.labelX}
                          y={p.labelY + 3}
                          textAnchor="middle"
                          fill="#FAF8F3"
                          fontSize="11"
                          fontFamily="JetBrains Mono, monospace"
                          fontWeight="600"
                        >
                          {p.id}
                        </text>
                      </g>
                    );
                  })}

                  {/* Building Footprints Overlay when in council or composite mode */}
                  {(heroLayerMode === "composite" || heroLayerMode === "council") && (
                    <g stroke="#FAF8F3" strokeWidth="1.2" fill="rgba(184, 154, 120, 0.45)">
                      <rect x="330" y="55" width="95" height="95" rx="2" />
                      <rect x="525" y="55" width="110" height="90" rx="2" />
                      <rect x="330" y="230" width="90" height="98" rx="2" />
                      <rect x="525" y="465" width="115" height="80" rx="2" />
                    </g>
                  )}
                </svg>

                {/* Bottom Floating Coordinate & Disclaimer Overlay */}
                <div className="absolute bottom-3 left-3 right-3 z-20 flex flex-wrap items-center justify-between gap-2 px-3.5 py-2 rounded-lg bg-[#171615]/90 border border-[#3A3530] text-[11px] font-mono text-[#E6E0D5]">
                  <span>PRELIMINARY CANDIDATE GEOMETRY • HOVER PARCEL TO INSPECT</span>
                  <span className="text-[#C5AA8C]">77.59284° E, 12.97241° N</span>
                </div>
              </div>

              {/* Right Live Spatial Telemetry & Selected Parcel Preview */}
              <div className="lg:col-span-4 flex flex-col justify-between bg-[#171615] border border-[#3A3530] rounded-xl p-5 text-[#FAF8F3] space-y-5">
                <div className="space-y-4">
                  <div className="flex items-center justify-between border-b border-[#302C28] pb-3">
                    <div>
                      <div className="text-[10px] font-mono uppercase tracking-widest text-[#C5AA8C]">
                        ACTIVE PARCEL TELEMETRY
                      </div>
                      <div className="text-xl font-mono font-semibold text-[#FAF8F3] mt-0.5">
                        {sceneId}_{activeHeroParcel.id.replace("-", "_")}
                      </div>
                    </div>
                    <span className="px-2.5 py-1 rounded bg-[#302C28] border border-[#6B5748] font-mono text-xs text-[#FAF8F3]">
                      Conf: {activeHeroParcel.conf}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-2.5 text-xs">
                    <div className="p-3 rounded-lg bg-[#24221F] border border-[#302C28]">
                      <div className="text-[10px] font-mono text-[#A18A76] uppercase">Metric Area</div>
                      <div className="font-mono text-sm font-semibold mt-1">{activeHeroParcel.area}</div>
                    </div>
                    <div className="p-3 rounded-lg bg-[#24221F] border border-[#302C28]">
                      <div className="text-[10px] font-mono text-[#A18A76] uppercase">Boundary Class</div>
                      <div className="font-mono text-xs font-semibold text-[#C5AA8C] mt-1 truncate">
                        {activeHeroParcel.type}
                      </div>
                    </div>
                  </div>

                  {/* 6-Agent Council Mini Status */}
                  <div className="p-3.5 rounded-lg bg-[#24221F] border border-[#302C28] space-y-2.5">
                    <div className="flex items-center justify-between text-[11px] font-mono">
                      <span className="text-[#A18A76] uppercase">6-Agent Council Verdict</span>
                      <span className="text-[#C5AA8C] font-semibold">{activeHeroParcel.verdict}</span>
                    </div>
                    <div className="grid grid-cols-3 gap-1.5 text-[10px] font-mono">
                      {["VISION", "GEOMETRY", "GIS", "ML", "ANOMALY", "FIELD"].map((ag) => (
                        <div
                          key={ag}
                          className="px-2 py-1 rounded bg-[#171615] border border-[#3A3530] text-[#E6E0D5] flex items-center justify-between"
                        >
                          <span>{ag}</span>
                          <span className="w-1.5 h-1.5 rounded-full bg-[#B89A78]" />
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Scene Aggregate Summary */}
                  <div className="pt-1 space-y-2">
                    <div className="text-[10px] font-mono uppercase tracking-wider text-[#A18A76]">
                      Active Urban Scene Summary
                    </div>
                    <div className="grid grid-cols-3 gap-2 text-center">
                      <div className="p-2.5 rounded-lg bg-[#24221F]/70 border border-[#302C28]">
                        <div className="font-mono text-lg font-semibold text-[#FAF8F3]">
                          {dashboardMetrics?.candidate_parcels ?? 16}
                        </div>
                        <div className="text-[10px] text-[#A18A76]">Parcels</div>
                      </div>
                      <div className="p-2.5 rounded-lg bg-[#24221F]/70 border border-[#302C28]">
                        <div className="font-mono text-lg font-semibold text-[#FAF8F3]">
                          {dashboardMetrics?.buildings_detected ?? 7}
                        </div>
                        <div className="text-[10px] text-[#A18A76]">Buildings</div>
                      </div>
                      <div className="p-2.5 rounded-lg bg-[#24221F]/70 border border-[#302C28]">
                        <div className="font-mono text-lg font-semibold text-[#FAF8F3]">
                          {dashboardMetrics?.roads_detected ?? 2}
                        </div>
                        <div className="text-[10px] text-[#A18A76]">Roads</div>
                      </div>
                    </div>
                  </div>
                </div>

                <button
                  onClick={() => setStage("LOGIN")}
                  className="w-full py-3 px-4 rounded-xl bg-[#FAF8F3] hover:bg-[#EEEAE2] text-[#171615] font-medium text-xs flex items-center justify-center gap-2 transition-all"
                >
                  <span>Open Full Mapping Workspace</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>
        </section>

        {/* EDITORIAL STORYTELLING SECTIONS */}
        <section ref={showcaseRef} className="py-20 bg-[#EEEAE2] border-t border-[#E4DFD5] px-6">
          <div className="max-w-7xl mx-auto space-y-16">
            <div className="max-w-2xl space-y-3">
              <div className="text-[11px] font-mono uppercase tracking-widest text-[#6B5748]">
                ARCHITECTURAL WORKFLOW • HUMAN-IN-THE-LOOP GEOAI
              </div>
              <h2 className="font-editorial text-4xl sm:text-5xl text-[#171615] leading-tight">
                Designed for surveyors, GIS engineers, and land administration.
              </h2>
              <p className="text-sm text-[#5C554E] leading-relaxed">
                AeroCadastre transforms high-resolution drone orthophotos and surface elevation models into structured, topological candidate parcels—empowering the surveyor as an authoritative verifier rather than a manual digitizer.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {[
                {
                  step: "01 / EXTRACTION",
                  title: "Multi-Modal GeoAI & Metric Topology",
                  desc: "Fuses 4-channel Drone RGB + normalized DSM height via MicroResUNet models to extract buildings, road corridors, and visible vs. inferred parcel boundaries in metric EPSG:32643.",
                  img: "/scenes/scene_urban_T0/rgb.png",
                  tag: "PyTorch + Shapely ST_*",
                },
                {
                  step: "02 / DELIBERATION",
                  title: "Six-Agent Cadastral AI Council",
                  desc: "Vision, Geometry, GIS Reference, ML Consensus, Anomaly, and Field Verification agents deliberate on every parcel polygon to surface conflicts before field deployment.",
                  img: "/scenes/scene_urban_T1/rgb.png",
                  tag: "6-Agent Consensus",
                },
                {
                  step: "03 / VERIFICATION",
                  title: "Interactive Web-GIS & Time Machine",
                  desc: "Snap vertices to reference GIS layers, subdivide or merge parcels, inspect multi-year changes (2024–2026), and export validated GeoJSON, Shapefile, CSV, and GeoPackage records.",
                  img: "/scenes/scene_urban_T2/rgb.png",
                  tag: "PostGIS Audit Lineage",
                },
              ].map((card, i) => (
                <div
                  key={i}
                  className="card-editorial rounded-2xl overflow-hidden flex flex-col justify-between"
                >
                  <div>
                    <div className="relative h-48 bg-[#24221F] overflow-hidden border-b border-[#E4DFD5]">
                      <img
                        src={card.img}
                        alt={card.title}
                        className="w-full h-full object-cover opacity-85 hover:scale-105 transition-transform duration-500"
                      />
                      <span className="absolute top-3 left-3 px-2.5 py-1 rounded bg-[#171615]/85 text-[#FAF8F3] font-mono text-[10px]">
                        {card.step}
                      </span>
                      <span className="absolute bottom-3 right-3 px-2.5 py-0.5 rounded bg-[#FAF8F3]/90 text-[#24221F] font-mono text-[10px] font-medium">
                        {card.tag}
                      </span>
                    </div>
                    <div className="p-6 space-y-2.5">
                      <h3 className="font-editorial text-2xl text-[#171615]">{card.title}</h3>
                      <p className="text-xs text-[#5C554E] leading-relaxed">{card.desc}</p>
                    </div>
                  </div>
                  <div className="px-6 pb-5 pt-2">
                    <button
                      onClick={() => setStage("LOGIN")}
                      className="text-xs font-medium text-[#6B5748] hover:text-[#171615] flex items-center gap-1.5 transition-colors"
                    >
                      <span>Launch module in workspace</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* FOOTER */}
        <footer className="bg-[#FAF8F3] border-t border-[#E4DFD5] py-10 px-6">
          <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-4 text-xs text-[#5C554E]">
            <div className="flex items-center gap-3">
              <div className="w-6 h-6 rounded bg-[#24221F] text-[#FAF8F3] flex items-center justify-center font-editorial text-sm">
                A
              </div>
              <span className="font-semibold text-[#171615]">AEROCADASTRE (SIH26012)</span>
              <span>•</span>
              <span>Ministry of Rural Development / Department of Land Resources Prototype</span>
            </div>
            <div className="font-mono text-[11px] text-[#8A735F]">
              SYNTHETIC DEMO DATA • PRELIMINARY CANDIDATE GEOMETRY
            </div>
          </div>
        </footer>
      </div>
    );
  }

  // ============================================================================
  // 3. LOGIN EXPERIENCE
  // ============================================================================
  if (stage === "LOGIN") {
    return (
      <div className="min-h-screen bg-[#F4F1EA] text-[#171615] grid grid-cols-1 lg:grid-cols-12">
        {/* LEFT PANEL: LARGE AERIAL / GEOSPATIAL VISUAL */}
        <div className="lg:col-span-7 bg-[#24221F] text-[#FAF8F3] p-8 sm:p-12 flex flex-col justify-between relative overflow-hidden min-h-[380px]">
          <div className="relative z-10 flex items-center justify-between">
            <button
              onClick={() => setStage("WELCOME")}
              className="flex items-center gap-2.5 text-left group"
            >
              <div className="w-8 h-8 rounded-lg bg-[#FAF8F3] text-[#171615] flex items-center justify-center font-editorial text-lg">
                A
              </div>
              <div>
                <div className="text-sm font-semibold tracking-tight text-[#FAF8F3]">
                  AEROCADASTRE
                </div>
                <div className="text-[10px] font-mono text-[#C5AA8C]">← Back to Welcome</div>
              </div>
            </button>
            <span className="px-2.5 py-1 rounded bg-[#302C28] border border-[#6B5748]/50 font-mono text-[10px] text-[#C5AA8C]">
              SYNTHETIC DEMO DATA
            </span>
          </div>

          {/* Center Framed Aerial Visual */}
          <div className="relative z-10 my-8 rounded-2xl overflow-hidden border border-[#3A3530] bg-[#171615] shadow-elevated max-w-xl mx-auto w-full">
            <div className="relative aspect-[16/10] w-full overflow-hidden">
              <img
                src="/scenes/scene_urban_T1/rgb.png"
                alt="Aerial Survey Sector"
                className="w-full h-full object-cover opacity-80"
              />
              <svg viewBox="0 0 400 250" className="absolute inset-0 w-full h-full">
                <g stroke="#FAF8F3" strokeWidth="0.5" opacity="0.25" strokeDasharray="3 3">
                  <line x1="100" y1="0" x2="100" y2="250" />
                  <line x1="200" y1="0" x2="200" y2="250" />
                  <line x1="300" y1="0" x2="300" y2="250" />
                  <line x1="0" y1="80" x2="400" y2="80" />
                  <line x1="0" y1="160" x2="400" y2="160" />
                </g>
                <polygon
                  points="25,20 145,20 145,115 25,115"
                  fill="rgba(61, 107, 82, 0.28)"
                  stroke="#FAF8F3"
                  strokeWidth="1.5"
                />
                <polygon
                  points="160,20 370,20 370,115 160,115"
                  fill="rgba(184, 154, 120, 0.25)"
                  stroke="#FDE68A"
                  strokeWidth="1.5"
                  strokeDasharray="5 3"
                />
                <polygon
                  points="25,140 210,140 210,230 25,230"
                  fill="rgba(184, 154, 120, 0.20)"
                  stroke="#C5AA8C"
                  strokeWidth="1.5"
                />
                <polygon
                  points="225,140 370,140 370,230 225,230"
                  fill="rgba(61, 107, 82, 0.24)"
                  stroke="#FAF8F3"
                  strokeWidth="1.5"
                />
              </svg>
              <div className="absolute bottom-3 left-3 right-3 px-3 py-1.5 rounded bg-[#171615]/90 border border-[#3A3530] flex items-center justify-between text-[10px] font-mono text-[#E6E0D5]">
                <span>SECTOR: URBAN SURVEY 43N ({sceneId})</span>
                <span className="text-[#C5AA8C]">16 CANDIDATE PARCELS READY</span>
              </div>
            </div>
          </div>

          <div className="relative z-10 space-y-2 max-w-lg">
            <p className="font-editorial text-2xl sm:text-3xl text-[#FAF8F3] leading-snug">
              &ldquo;AI turns the cadastral surveyor from a manual digitizer into an authoritative spatial verifier.&rdquo;
            </p>
            <p className="text-xs font-mono text-[#A18A76]">
              SIH26012 • PRELIMINARY CANDIDATE GEOMETRY WORKSPACE
            </p>
          </div>
        </div>

        {/* RIGHT PANEL: LOGIN FORM & DEMO ROLE SELECTION */}
        <div className="lg:col-span-5 bg-[#FAF8F3] p-8 sm:p-12 flex flex-col justify-center">
          <div className="max-w-md w-full mx-auto space-y-7 animate-page-enter">
            <div className="space-y-2">
              <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded bg-[#EEEAE2] border border-[#D2C9BC] text-[10px] font-mono uppercase text-[#6B5748]">
                <Lock className="w-3 h-3" />
                <span>Prototype Demo Authentication</span>
              </div>
              <h2 className="font-editorial text-4xl text-[#171615]">Welcome back.</h2>
              <p className="text-sm text-[#5C554E]">
                Continue to AeroCadastre Cadastral Intelligence Workspace.
              </p>
            </div>

            {/* Role Selector (Surveyor / Demo User / Administrator) */}
            <div className="space-y-2">
              <label className="block text-[11px] font-mono uppercase tracking-wider text-[#6B5748]">
                Select Demo Workspace Role
              </label>
              <div className="grid grid-cols-3 gap-2">
                {(["Surveyor", "Demo User", "Administrator"] as const).map((r) => {
                  const active = selectedProfile.role === r;
                  return (
                    <button
                      key={r}
                      type="button"
                      onClick={() => handleSelectRole(r)}
                      className={`p-2.5 rounded-xl border text-left transition-all ${
                        active
                          ? "bg-[#24221F] text-[#FAF8F3] border-[#24221F] shadow-sm"
                          : "bg-[#F4F1EA] text-[#24221F] border-[#D2C9BC] hover:border-[#8A735F]"
                      }`}
                    >
                      <div className="text-xs font-semibold">{r}</div>
                      <div
                        className={`text-[10px] font-mono mt-0.5 truncate ${
                          active ? "text-[#C5AA8C]" : "text-[#6B5748]"
                        }`}
                      >
                        {DEMO_PROFILES[r].operatorId}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Login Form */}
            <form onSubmit={handleLoginSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-[#24221F] mb-1.5">
                  Workspace Email
                </label>
                <input
                  type="email"
                  value={emailInput}
                  onChange={(e) => setEmailInput(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[#FFFFFF] border border-[#D2C9BC] text-xs font-mono text-[#171615] focus:outline-none focus:border-[#6B5748]"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-[#24221F] mb-1.5">
                  Session Passkey (Demo)
                </label>
                <input
                  type="password"
                  value={passwordInput}
                  onChange={(e) => setPasswordInput(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[#FFFFFF] border border-[#D2C9BC] text-xs font-mono text-[#171615] focus:outline-none focus:border-[#6B5748]"
                />
              </div>

              <div className="pt-2 space-y-2.5">
                <button
                  type="submit"
                  className="w-full btn-primary-dark py-3 px-4 rounded-xl text-xs font-semibold flex items-center justify-center gap-2"
                >
                  <span>Sign In as {selectedProfile.role}</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>

                <button
                  type="button"
                  onClick={() => {
                    handleSelectRole("Surveyor");
                    setStage("WORKSPACE_OPENING");
                  }}
                  className="w-full btn-secondary-warm py-3 px-4 rounded-xl text-xs font-semibold flex items-center justify-center gap-2"
                >
                  <UserCheck className="w-3.5 h-3.5 text-[#6B5748]" />
                  <span>Continue as Demo Surveyor</span>
                </button>
              </div>
            </form>

            {/* Clear Prototype Attribution */}
            <div className="p-3.5 rounded-xl bg-[#F4F1EA] border border-[#E4DFD5] text-[11px] text-[#5C554E] leading-relaxed">
              <strong className="text-[#24221F]">Demo Session Notice:</strong> This prototype uses local role state connected to the embedded PostGIS / Spatial SQLite database (`D:\SIH26012_AeroCadastre`). No external government credentials are required.
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ============================================================================
  // 4. APPLICATION OPENING EXPERIENCE (~0.95s)
  // ============================================================================
  if (stage === "WORKSPACE_OPENING") {
    const items = [
      { key: "PROJECT", val: "PROJ_SIH26012_DEMO" },
      { key: "SCENE", val: sceneId },
      { key: "GIS LAYERS", val: "EPSG:4326 / UTM 43N" },
      { key: "AI MODELS", val: "MicroResUNet RGB+nDSM" },
      { key: "COUNCIL", val: "6-Agent Deliberation Ready" },
      { key: "VERIFICATION", val: selectedProfile.operatorId },
    ];

    return (
      <div
        onClick={() => setStage("APP_READY")}
        className="fixed inset-0 z-50 bg-[#F4F1EA] text-[#171615] flex flex-col items-center justify-center p-6 select-none cursor-pointer"
      >
        <div className="max-w-md w-full space-y-6 animate-page-enter">
          <div className="text-center space-y-1.5">
            <div className="w-10 h-10 rounded-xl bg-[#24221F] text-[#FAF8F3] flex items-center justify-center font-editorial text-xl mx-auto mb-3">
              A
            </div>
            <h2 className="font-editorial text-3xl text-[#171615]">
              Preparing your workspace...
            </h2>
            <p className="text-xs font-mono text-[#6B5748]">
              Authenticated as {selectedProfile.name} ({selectedProfile.role})
            </p>
          </div>

          <div className="bg-[#FAF8F3] border border-[#E4DFD5] rounded-2xl p-4 space-y-2 shadow-editorial">
            {items.map((item, idx) => {
              const active = openingStep > idx;
              return (
                <div
                  key={item.key}
                  className={`flex items-center justify-between px-3 py-2 rounded-lg text-xs font-mono transition-all duration-150 ${
                    active
                      ? "bg-[#F4F1EA] text-[#171615] border border-[#D2C9BC]"
                      : "text-[#8C8277] opacity-50"
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span
                      className={`w-2 h-2 rounded-full ${
                        active ? "bg-[#3D6B52]" : "bg-[#D2C9BC]"
                      }`}
                    />
                    <span className="font-semibold">{item.key}</span>
                  </div>
                  <span className="text-[11px] text-[#6B5748]">{item.val}</span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    );
  }

  return null;
}
