"use client";

import React, { useState, useRef, useEffect, useCallback, useMemo } from "react";
import {
  MousePointer,
  Hand,
  PenTool,
  Edit3,
  Split,
  Merge,
  Trash2,
  Magnet,
  Ruler,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Layers,
  Search,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Sliders,
  ChevronRight,
  ChevronLeft,
  X,
  ExternalLink,
  ShieldAlert,
  Info,
  Building2,
  Navigation,
  Scan,
  Sparkles,
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

const LAND_USE_PALETTE: Record<string, { fill: string; border: string; label: string }> = {
  residential: { fill: "#E2D9CC", border: "#8A735F", label: "Residential" },
  commercial: { fill: "#D6DFE8", border: "#4F708F", label: "Commercial" },
  industrial: { fill: "#DDD5E5", border: "#7B628F", label: "Industrial" },
  agricultural: { fill: "#E1EAD8", border: "#658252", label: "Agricultural" },
  vegetation: { fill: "#DCE5D8", border: "#51744B", label: "Vegetation / Park" },
  water: { fill: "#D8E6EC", border: "#487994", label: "Water Body" },
  vacant: { fill: "#EBE7E1", border: "#A1998E", label: "Vacant Land" },
  road: { fill: "#E0DDD7", border: "#6D6862", label: "Road Corridor" },
  mixed_use: { fill: "#EDE5D6", border: "#9A7E4F", label: "Mixed Use" },
};

interface WebGisEditorProps {
  bundle: any;
  selectedParcelId: string | null;
  onSelectParcel: (id: string | null) => void;
  highlightedIds: string[];
  onRefreshBundle: () => Promise<void>;
  onNavigateTab?: (tab: string) => void;
  activeRole?: string;
}

export type GisToolMode =
  | "select"
  | "pan"
  | "draw"
  | "aoi_box"
  | "edit"
  | "split"
  | "merge"
  | "delete"
  | "snap"
  | "measure"
  | "verify";

export default function WebGisEditor({
  bundle,
  selectedParcelId,
  onSelectParcel,
  highlightedIds,
  onRefreshBundle,
  onNavigateTab,
  activeRole = "Surveyor_Verifier_01",
}: WebGisEditorProps) {
  const svgRef = useRef<SVGSVGElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);

  // Active Tool Mode
  const [activeTool, setActiveTool] = useState<GisToolMode>("select");

  // Pan & Zoom viewport state
  const [zoom, setZoom] = useState<number>(1);
  const [panOffset, setPanOffset] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState<boolean>(false);
  const [panStart, setPanStart] = useState<{ x: number; y: number }>({ x: 0, y: 0 });

  // Layer visibility stack
  const [layers, setLayers] = useState({
    imagery: false,
    googleSatellite: true,
    candidateParcels: true,
    referenceParcels: true,
    buildings: true,
    roads: true,
    boundaries: true,
    landUse: false,
    dsm: false,
    topology: true,
    anomalies: true,
    changes: false,
    routes: false,
    adminBoundaries: false,
    punePilot: false,
    sentinel2: false,
  });

  // Google Maps JavaScript API State & Ref
  const googleMapRef = useRef<HTMLDivElement | null>(null);
  const mapInstanceRef = useRef<any>(null);
  const [isGoogleMapLoaded, setIsGoogleMapLoaded] = useState<boolean>(false);
  const [googleMapError, setGoogleMapError] = useState<string | null>(null);

  const [colorMode, setColorMode] = useState<"confidence" | "landuse" | "verification">("confidence");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [isSearchOpen, setIsSearchOpen] = useState<boolean>(false);
  const [isLayerDockOpen, setIsLayerDockOpen] = useState<boolean>(true);
  const [statusNotification, setStatusNotification] = useState<{ msg: string; type: "success" | "info" | "error" } | null>(null);
  const [busy, setBusy] = useState<boolean>(false);

  // Interactive vertex editing state
  const [editingVertices, setEditingVertices] = useState<[number, number][]>([]);
  const [selectedVertexIdx, setSelectedVertexIdx] = useState<number>(0);
  const [draggingVertexIdx, setDraggingVertexIdx] = useState<number | null>(null);
  const [editLandUse, setEditLandUse] = useState<string>("residential");
  const [editReason, setEditReason] = useState<string>("Surveyor boundary refinement & verification");
  const [mergeTargetId, setMergeTargetId] = useState<string>("");

  // Polygon Drawing mode state
  const [drawnPoints, setDrawnPoints] = useState<[number, number][]>([]);

  // Interactive AOI Selection & Dynamic AI Parcelling state
  const [aoiBoxPoints, setAoiBoxPoints] = useState<[number, number][]>([]);
  const [dynamicParcels, setDynamicParcels] = useState<any[]>([]);
  const [dynamicMetadata, setDynamicMetadata] = useState<any | null>(null);
  const [isParcellingActive, setIsParcellingActive] = useState<boolean>(false);

  // Interactive Measure Tool state
  const [measurePoints, setMeasurePoints] = useState<[number, number][]>([]);
  const [measuredDistanceM, setMeasuredDistanceM] = useState<number | null>(null);

  // Live cursor coordinates
  const [cursorCoords, setCursorCoords] = useState<{ lon: number; lat: number }>({
    lon: 77.59284,
    lat: 12.97241,
  });

  const [adminData, setAdminData] = useState<any>(null);
  const [puneData, setPuneData] = useState<any>(null);
  const [sentinelData, setSentinelData] = useState<any>(null);

  // Fetch authentic Maharashtra administrative boundaries, Pune pilot layers, and Sentinel-2
  useEffect(() => {
    fetch(`${API_BASE}/api/gis/admin-boundaries`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => d && setAdminData(d))
      .catch(() => {});

    fetch(`${API_BASE}/api/gis/pune-pilot`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => d && setPuneData(d))
      .catch(() => {});

    fetch(`${API_BASE}/api/gis/sentinel2`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => d && setSentinelData(d))
      .catch(() => {});
  }, []);

  // Google Maps JavaScript API SDK Injection & Lifecycle
  useEffect(() => {
    const apiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY;
    if (!apiKey) return;

    // Global listener for Google Maps authentication failures
    (window as any).gm_authFailure = () => {
      console.warn("[Google Maps] Authentication failure (gm_authFailure). Check API key restrictions or billing.");
      setGoogleMapError("Auth failure (check key permissions/billing)");
    };

    if ((window as any).google?.maps) {
      setIsGoogleMapLoaded(true);
      return;
    }

    const scriptId = "google-maps-js-sdk";
    if (document.getElementById(scriptId)) return;

    const script = document.createElement("script");
    script.id = scriptId;
    script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&libraries=geometry`;
    script.async = true;
    script.defer = true;
    script.onload = () => {
      setIsGoogleMapLoaded(true);
    };
    script.onerror = () => {
      console.warn("[Google Maps] Failed to load Google Maps SDK script.");
      setGoogleMapError("Network error loading Google Maps SDK");
    };
    document.head.appendChild(script);
  }, []);

  // Initialize or update the Google Satellite Map instance
  useEffect(() => {
    if (!isGoogleMapLoaded || !googleMapRef.current || !(window as any).google?.maps) {
      return;
    }

    try {
      if (!mapInstanceRef.current) {
        // Center on Pune Historic Core (Kasba Peth)
        const puneCenter = { lat: 18.52043, lng: 73.85674 };
        const map = new (window as any).google.maps.Map(googleMapRef.current, {
          center: puneCenter,
          zoom: 17,
          mapTypeId: "satellite",
          disableDefaultUI: true,
          gestureHandling: "none",
          tilt: 0,
          backgroundColor: "#171615",
        });
        mapInstanceRef.current = map;
      } else if (dynamicMetadata?.aoi_bounds) {
        const [minx, miny, maxx, maxy] = dynamicMetadata.aoi_bounds;
        mapInstanceRef.current.panTo({
          lat: (miny + maxy) / 2,
          lng: (minx + maxx) / 2,
        });
      }
    } catch (err: any) {
      console.warn("[Google Maps] Error initializing Map instance:", err);
      setGoogleMapError(err?.message || "Map initialization failed");
    }
  }, [isGoogleMapLoaded, layers.googleSatellite, dynamicMetadata]);

  // Extract layers from bundle, fusing with any dynamically generated AI candidate parcels
  const baseParcels: any[] = bundle?.candidate_parcels || [];
  const parcels: any[] = dynamicParcels.length > 0 ? dynamicParcels : baseParcels;
  const refParcels: any[] = bundle?.reference_parcels || [];
  const buildings: any[] = bundle?.buildings || [];
  const roads: any[] = bundle?.roads || [];
  const boundaries: any[] = bundle?.boundaries || [];
  const topoIssues: any[] = bundle?.topology_issues || [];
  const anomalies: any[] = bundle?.anomalies || [];
  const changes: any[] = bundle?.changes || [];
  const routes: any[] = bundle?.field_routes || [];

  const selectedParcel = parcels.find((p) => p.id === selectedParcelId) || null;
  const selectedCouncil = (bundle?.council_decisions || []).find((c: any) => c.parcel_id === selectedParcelId) || null;

  // Geographic coordinate projections - dynamically adapts between Pune Google Satellite / Dynamic AI Parcels and synthetic scene bundle
  const isDynamicOrPune = Boolean(
    dynamicParcels.length > 0 ||
    dynamicMetadata?.aoi_bounds ||
    layers.googleSatellite
  );

  const [originLon, originLat, span] = useMemo(() => {
    if (dynamicMetadata?.aoi_bounds) {
      const [minx, miny, maxx, maxy] = dynamicMetadata.aoi_bounds;
      const computedSpan = Math.max(maxx - minx, maxy - miny, 0.001);
      return [minx, miny, computedSpan];
    }
    if (dynamicParcels.length > 0) {
      let minx = Infinity, miny = Infinity, maxx = -Infinity, maxy = -Infinity;
      for (const p of dynamicParcels) {
        const ring = p.geometry?.coordinates?.[0] || [];
        for (const [x, y] of ring) {
          if (x < minx) minx = x;
          if (x > maxx) maxx = x;
          if (y < miny) miny = y;
          if (y > maxy) maxy = y;
        }
      }
      if (minx < Infinity && maxx > -Infinity) {
        const computedSpan = Math.max(maxx - minx, maxy - miny, 0.001);
        return [minx, miny, computedSpan];
      }
    }
    if (layers.googleSatellite) {
      // Pune Historic Core (Kasba Peth) default bounding envelope
      return [73.8540, 18.5180, 0.0050];
    }
    // Synthetic benchmark default
    const oLon = bundle?.metadata?.origin_lonlat?.[0] ?? 77.592;
    const oLat = bundle?.metadata?.origin_lonlat?.[1] ?? 12.972;
    return [oLon, oLat, 0.0024];
  }, [dynamicParcels, dynamicMetadata, layers.googleSatellite, bundle?.metadata?.origin_lonlat]);

  const VIEW_SIZE = 760;

  const lonLatToSvg = useCallback(
    (lon: number, lat: number): [number, number] => {
      const x = ((lon - originLon) / span) * VIEW_SIZE;
      const y = (1.0 - (lat - originLat) / span) * VIEW_SIZE;
      return [x, y];
    },
    [originLon, originLat, span]
  );

  const svgToLonLat = useCallback(
    (x: number, y: number): [number, number] => {
      const lon = originLon + (x / VIEW_SIZE) * span;
      const lat = originLat + (1.0 - y / VIEW_SIZE) * span;
      return [Number(lon.toFixed(7)), Number(lat.toFixed(7))];
    },
    [originLon, originLat, span]
  );

  const ringToSvgPoints = useCallback(
    (ring: number[][]): string => {
      return ring
        .map((pt) => {
          const [x, y] = lonLatToSvg(pt[0], pt[1]);
          return `${x.toFixed(1)},${y.toFixed(1)}`;
        })
        .join(" ");
    },
    [lonLatToSvg]
  );

  // Sync selected parcel vertices when selection changes
  useEffect(() => {
    if (selectedParcel && selectedParcel.geometry?.coordinates?.[0]) {
      const rawRing: number[][] = selectedParcel.geometry.coordinates[0];
      const openRing =
        rawRing.length > 1 &&
        rawRing[0][0] === rawRing[rawRing.length - 1][0] &&
        rawRing[0][1] === rawRing[rawRing.length - 1][1]
          ? rawRing.slice(0, -1)
          : rawRing;
      setEditingVertices(openRing.map((pt) => [pt[0], pt[1]]));
      setSelectedVertexIdx(0);
      setEditLandUse(selectedParcel.land_use_class || "residential");
      const otherParcel = parcels.find((p) => p.id !== selectedParcel.id);
      setMergeTargetId(otherParcel ? otherParcel.id : "");
    } else {
      setEditingVertices([]);
    }
  }, [selectedParcelId, bundle]);

  // Viewport Mouse Handlers
  const handleSvgMouseDown = (e: React.MouseEvent<SVGSVGElement>) => {
    if (activeTool === "pan" || e.button === 1 || (e.altKey && e.button === 0)) {
      setIsPanning(true);
      setPanStart({ x: e.clientX - panOffset.x, y: e.clientY - panOffset.y });
    }
  };

  const handleSvgMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    if (!svgRef.current) return;
    const rect = svgRef.current.getBoundingClientRect();
    const rawX = (e.clientX - rect.left - panOffset.x) / zoom;
    const rawY = (e.clientY - rect.top - panOffset.y) / zoom;
    const scaleX = VIEW_SIZE / (rect.width / zoom);
    const scaleY = VIEW_SIZE / (rect.height / zoom);
    const sx = rawX * scaleX;
    const sy = rawY * scaleY;
    const [lon, lat] = svgToLonLat(sx, sy);
    setCursorCoords({ lon, lat });

    if (isPanning) {
      setPanOffset({
        x: e.clientX - panStart.x,
        y: e.clientY - panStart.y,
      });
    }

    if (draggingVertexIdx !== null && editingVertices.length > 0 && activeTool === "edit") {
      const updated = [...editingVertices];
      updated[draggingVertexIdx] = [lon, lat];
      setEditingVertices(updated);
    }
  };

  const handleSvgMouseUp = () => {
    setIsPanning(false);
    setDraggingVertexIdx(null);
  };

  const handleSvgWheel = (e: React.WheelEvent<SVGSVGElement>) => {
    e.preventDefault();
    const zoomFactor = e.deltaY < 0 ? 1.12 : 0.89;
    setZoom((prev) => Math.min(Math.max(prev * zoomFactor, 0.75), 4.5));
  };

  const handleCanvasClick = (e: React.MouseEvent<SVGSVGElement>) => {
    if (!svgRef.current) return;
    const rect = svgRef.current.getBoundingClientRect();
    const rawX = (e.clientX - rect.left - panOffset.x) / zoom;
    const rawY = (e.clientY - rect.top - panOffset.y) / zoom;
    const scaleX = VIEW_SIZE / (rect.width / zoom);
    const scaleY = VIEW_SIZE / (rect.height / zoom);
    const sx = rawX * scaleX;
    const sy = rawY * scaleY;
    const [lon, lat] = svgToLonLat(sx, sy);

    if (activeTool === "draw") {
      setDrawnPoints((prev) => [...prev, [lon, lat]]);
    } else if (activeTool === "aoi_box") {
      if (aoiBoxPoints.length >= 2) {
        setAoiBoxPoints([[lon, lat]]);
      } else {
        setAoiBoxPoints((prev) => [...prev, [lon, lat]]);
      }
    } else if (activeTool === "measure") {
      if (measurePoints.length >= 2) {
        setMeasurePoints([[lon, lat]]);
        setMeasuredDistanceM(null);
      } else {
        const nextPts: [number, number][] = [...measurePoints, [lon, lat]];
        setMeasurePoints(nextPts);
        if (nextPts.length === 2) {
          // Approximate Euclidean metric distance in UTM Zone 43N
          const dLon = (nextPts[1][0] - nextPts[0][0]) * 108500;
          const dLat = (nextPts[1][1] - nextPts[0][1]) * 111000;
          const dist = Math.sqrt(dLon * dLon + dLat * dLat);
          setMeasuredDistanceM(Number(dist.toFixed(1)));
        }
      }
    }
  };

  // Run Real Multi-Model Dynamic AI Parcelling on selected AOI
  const handleRunDynamicParcelling = async (customBounds?: [number, number, number, number]) => {
    let boundsToUse: [number, number, number, number];
    if (customBounds) {
      boundsToUse = customBounds;
    } else if (aoiBoxPoints.length >= 2) {
      const minLon = Math.min(aoiBoxPoints[0][0], aoiBoxPoints[1][0]);
      const maxLon = Math.max(aoiBoxPoints[0][0], aoiBoxPoints[1][0]);
      const minLat = Math.min(aoiBoxPoints[0][1], aoiBoxPoints[1][1]);
      const maxLat = Math.max(aoiBoxPoints[0][1], aoiBoxPoints[1][1]);
      boundsToUse = [minLon, minLat, maxLon, maxLat];
    } else {
      // Default to visible viewport bounds
      const [tlLon, tlLat] = svgToLonLat(20, 20);
      const [brLon, brLat] = svgToLonLat(VIEW_SIZE - 20, VIEW_SIZE - 20);
      boundsToUse = [
        Math.min(tlLon, brLon),
        Math.min(tlLat, brLat),
        Math.max(tlLon, brLon),
        Math.max(tlLat, brLat),
      ];
    }

    setIsParcellingActive(true);
    setBusy(true);
    setStatusNotification({
      msg: "Executing real multi-model GeoAI inference & parcel synthesis across AOI...",
      type: "info",
    });

    try {
      const res = await fetch(`${API_BASE}/api/parcels/generate-candidates`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          aoi_bounds: boundsToUse,
          project_id: bundle?.project_id || "PROJ_SIH26012_DEMO",
          resolution: 0.5,
          persist_to_postgis: true,
          operator_id: activeRole,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Dynamic AI Parcelling failed");
      }

      const geojsonData = await res.json();
      const extractedParcels = (geojsonData.features || []).map((feat: any) => ({
        ...feat.properties,
        geometry: feat.geometry,
      }));

      setDynamicParcels(extractedParcels);
      setDynamicMetadata(geojsonData.metadata);
      setAoiBoxPoints([]);
      setActiveTool("select");

      if (extractedParcels.length > 0) {
        onSelectParcel(extractedParcels[0].id);
      }

      setStatusNotification({
        msg: `Synthesized ${extractedParcels.length} candidate parcels with mean confidence ${(
          geojsonData.metadata?.mean_confidence * 100
        ).toFixed(1)}% in ${geojsonData.metadata?.processing_time_ms}ms.`,
        type: "success",
      });
    } catch (err: any) {
      setStatusNotification({
        msg: `Parcelling error: ${err.message}`,
        type: "error",
      });
    } finally {
      setIsParcellingActive(false);
      setBusy(false);
    }
  };

  // Nudge active vertex
  const handleNudgeVertex = (dLon: number, dLat: number) => {
    if (editingVertices.length === 0) return;
    const u = [...editingVertices];
    const cur = u[selectedVertexIdx];
    u[selectedVertexIdx] = [
      Number((cur[0] + dLon).toFixed(7)),
      Number((cur[1] + dLat).toFixed(7)),
    ];
    setEditingVertices(u);
  };

  // Add vertex at edge midpoint
  const handleAddVertex = () => {
    if (editingVertices.length < 3) return;
    const idx = selectedVertexIdx % editingVertices.length;
    const nextIdx = (idx + 1) % editingVertices.length;
    const p1 = editingVertices[idx];
    const p2 = editingVertices[nextIdx];
    const mid: [number, number] = [
      Number(((p1[0] + p2[0]) / 2).toFixed(7)),
      Number(((p1[1] + p2[1]) / 2).toFixed(7)),
    ];
    const updated = [
      ...editingVertices.slice(0, idx + 1),
      mid,
      ...editingVertices.slice(idx + 1),
    ];
    setEditingVertices(updated);
    setSelectedVertexIdx(idx + 1);
    setStatusNotification({
      msg: `Added vertex #${idx + 2} at midpoint. Click 'Commit Changes to PostGIS' to persist.`,
      type: "info",
    });
  };

  // Delete selected vertex
  const handleDeleteVertex = () => {
    if (editingVertices.length <= 3) {
      setStatusNotification({
        msg: "A cadastral parcel polygon requires at least 3 vertices.",
        type: "error",
      });
      return;
    }
    const idx = selectedVertexIdx % editingVertices.length;
    const updated = editingVertices.filter((_, i) => i !== idx);
    setEditingVertices(updated);
    setSelectedVertexIdx(0);
    setStatusNotification({
      msg: `Removed vertex #${idx + 1}. Click 'Commit Changes to PostGIS' to persist.`,
      type: "info",
    });
  };

  // Snap to Reference GIS boundary
  const handleSnapToReference = () => {
    if (!selectedParcel) return;
    const refMatch = refParcels.find(
      (r) =>
        r.id.endsWith(selectedParcel.id.split("_P_").pop() || "NONE") ||
        r.parcel_id === selectedParcel.id
    );
    if (!refMatch || !refMatch.geometry?.coordinates?.[0]) {
      setStatusNotification({
        msg: "No matching Reference GIS polygon found for this parcel.",
        type: "error",
      });
      return;
    }
    const ring = refMatch.geometry.coordinates[0].slice(0, -1);
    setEditingVertices(ring.map((pt: number[]) => [pt[0], pt[1]]));
    setStatusNotification({
      msg: `Snapped ${selectedParcel.id} vertices to Reference GIS layer. Click 'Commit Changes to PostGIS' to save.`,
      type: "success",
    });
  };

  // Persist edited geometry & attributes to PostGIS
  const handleSaveParcelEdit = async (overrideStatus?: string) => {
    if (!selectedParcel || editingVertices.length < 3) return;
    setBusy(true);
    try {
      const newStatus = overrideStatus || "ADMIN_EDITED";
      const closedRing = [...editingVertices, editingVertices[0]];
      const res = await fetch(`${API_BASE}/api/parcels/${selectedParcel.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          geometry: { type: "Polygon", coordinates: [closedRing] },
          land_use_class: editLandUse,
          verification_status: newStatus,
          operator_id: activeRole,
          reason: editReason,
        }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to update parcel");
      }
      const updatedData = await res.json();
      // Update local dynamicParcels array if this parcel was part of dynamic parcelling
      setDynamicParcels((prev) =>
        prev.map((p) =>
          p.id === selectedParcel.id
            ? {
                ...p,
                geometry: updatedData.geometry || { type: "Polygon", coordinates: [closedRing] },
                land_use_class: editLandUse,
                verification_status: newStatus,
                version: (p.version || 1) + 1,
              }
            : p
        )
      );
      await onRefreshBundle();
      setStatusNotification({
        msg: `Successfully saved ${selectedParcel.id} to PostGIS (Status: ${newStatus}, v${
          (selectedParcel.version || 1) + 1
        }).`,
        type: "success",
      });
    } catch (err: any) {
      setStatusNotification({ msg: `Error: ${err.message}`, type: "error" });
    } finally {
      setBusy(false);
    }
  };

  // Split parcel
  const handleSplitParcel = async (axis: "VERTICAL" | "HORIZONTAL") => {
    if (!selectedParcel) return;
    setBusy(true);
    try {
      const res = await fetch(`${API_BASE}/api/parcels/${selectedParcel.id}/split`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          split_axis: axis,
          split_ratio: 0.5,
          operator_id: activeRole,
          reason: `${axis} subdivision in Web-GIS Editor`,
        }),
      });
      if (!res.ok) throw new Error("Failed to split parcel");
      const data = await res.json();
      await onRefreshBundle();
      setStatusNotification({
        msg: `Divided ${selectedParcel.id} into ${data.parcel_a.id} & ${data.parcel_b.id}.`,
        type: "success",
      });
    } catch (err: any) {
      setStatusNotification({ msg: `Split error: ${err.message}`, type: "error" });
    } finally {
      setBusy(false);
    }
  };

  // Merge parcels
  const handleMergeParcels = async () => {
    if (!selectedParcel || !mergeTargetId) return;
    setBusy(true);
    try {
      const res = await fetch(`${API_BASE}/api/parcels/merge`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_id: bundle.project_id,
          scene_id: bundle.scene_id,
          parcel_id_a: selectedParcel.id,
          parcel_id_b: mergeTargetId,
          operator_id: activeRole,
          reason: `Merged ${selectedParcel.id} + ${mergeTargetId} in Web-GIS Editor`,
        }),
      });
      if (!res.ok) throw new Error("Failed to merge parcels");
      await onRefreshBundle();
      setStatusNotification({
        msg: `Merged parcels into a single verified geometry.`,
        type: "success",
      });
    } catch (err: any) {
      setStatusNotification({ msg: `Merge error: ${err.message}`, type: "error" });
    } finally {
      setBusy(false);
    }
  };

  // Create new parcel polygon from drawn points
  const handleFinishCreateParcel = async () => {
    if (drawnPoints.length < 3) {
      setStatusNotification({
        msg: "Click at least 3 points on the map canvas to complete polygon.",
        type: "error",
      });
      return;
    }
    setBusy(true);
    try {
      const closed = [...drawnPoints, drawnPoints[0]];
      const res = await fetch(`${API_BASE}/api/parcels`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_id: bundle.project_id,
          scene_id: bundle.scene_id,
          land_use_class: "residential",
          boundary_representation: "HUMAN_VERIFIED",
          geometry: { type: "Polygon", coordinates: [closed] },
          operator_id: activeRole,
          reason: "Surveyor digitized new candidate parcel in Web-GIS",
        }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to create parcel");
      }
      const created = await res.json();
      setDrawnPoints([]);
      setActiveTool("select");
      await onRefreshBundle();
      onSelectParcel(created.id);
      setStatusNotification({
        msg: `Created new parcel ${created.id} (${created.area_sqm?.toFixed(0)} m²) in PostGIS.`,
        type: "success",
      });
    } catch (err: any) {
      setStatusNotification({ msg: `Create error: ${err.message}`, type: "error" });
    } finally {
      setBusy(false);
    }
  };

  // Delete candidate parcel
  const handleDeleteParcel = async () => {
    if (!selectedParcel) return;
    setBusy(true);
    try {
      const delId = selectedParcel.id;
      const res = await fetch(`${API_BASE}/api/parcels/${delId}`, { method: "DELETE" });
      if (!res.ok) throw new Error("Failed to delete parcel");
      onSelectParcel(null);
      await onRefreshBundle();
      setStatusNotification({
        msg: `Deleted candidate parcel ${delId} and logged audit trail.`,
        type: "info",
      });
    } catch (err: any) {
      setStatusNotification({ msg: `Delete error: ${err.message}`, type: "error" });
    } finally {
      setBusy(false);
    }
  };

  // Determine thematic parcel coloring
  const getParcelStyle = (p: any) => {
    if (colorMode === "landuse") {
      const lu = LAND_USE_PALETTE[p.land_use_class] || LAND_USE_PALETTE.residential;
      return { fill: lu.fill, stroke: lu.border };
    }
    if (colorMode === "verification") {
      if (p.verification_status === "HUMAN_VERIFIED")
        return { fill: "rgba(61, 107, 82, 0.40)", stroke: "#3D6B52" };
      if (p.verification_status === "REJECTED")
        return { fill: "rgba(158, 62, 55, 0.35)", stroke: "#9E3E37" };
      if (p.verification_priority === "HIGH")
        return { fill: "rgba(158, 107, 32, 0.42)", stroke: "#9E6B20" };
      return { fill: "rgba(184, 154, 120, 0.32)", stroke: "#8A735F" };
    }
    // Confidence mode
    if (p.confidence >= 0.85)
      return { fill: "rgba(61, 107, 82, 0.32)", stroke: "#3D6B52" };
    if (p.confidence >= 0.7)
      return { fill: "rgba(158, 107, 32, 0.32)", stroke: "#9E6B20" };
    return { fill: "rgba(158, 62, 55, 0.34)", stroke: "#9E3E37" };
  };

  const filteredParcels = parcels.filter(
    (p) =>
      p.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.land_use_class.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.council_decision.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div
      ref={containerRef}
      className="relative w-full flex-1 min-h-0 flex overflow-hidden bg-[#FAF8F3] select-none"
    >
      {/* 1. LEFT TOOL RAIL */}
      <aside className="w-14 sm:w-16 shrink-0 bg-[#24221F] text-[#FAF8F3] border-r border-[#302C28] flex flex-col items-center justify-between py-3.5 z-20 shadow-md">
        <div className="flex flex-col items-center gap-1.5 w-full px-2">
          {[
            { id: "select", icon: MousePointer, label: "Select (V)" },
            { id: "pan", icon: Hand, label: "Pan (H / Alt)" },
            { id: "aoi_box", icon: Scan, label: "Select AOI Box for AI Parcelling" },
            { id: "edit", icon: Edit3, label: "Edit Vertices" },
            { id: "draw", icon: PenTool, label: "Digitize Polygon" },
            { id: "snap", icon: Magnet, label: "Snap to Ref GIS" },
            { id: "measure", icon: Ruler, label: "Measure (M)" },
            { id: "split", icon: Split, label: "Split Parcel" },
            { id: "merge", icon: Merge, label: "Merge Parcel" },
            { id: "verify", icon: CheckCircle2, label: "Verify Status" },
          ].map((tool) => {
            const Icon = tool.icon;
            const isActive = activeTool === tool.id;
            return (
              <button
                key={tool.id}
                onClick={() => {
                  if (tool.id === "snap") {
                    handleSnapToReference();
                  } else if (tool.id === "verify" && selectedParcel) {
                    handleSaveParcelEdit("HUMAN_VERIFIED");
                  } else {
                    setActiveTool(tool.id as GisToolMode);
                  }
                }}
                title={tool.label}
                className={`w-10 h-10 rounded-xl flex items-center justify-center transition-all ${
                  isActive
                    ? "bg-[#FAF8F3] text-[#171615] shadow-sm"
                    : "text-[#C5AA8C] hover:bg-[#302C28] hover:text-[#FAF8F3]"
                }`}
              >
                <Icon className="w-4 h-4" />
              </button>
            );
          })}
        </div>

        {/* Viewport Zoom Controls */}
        <div className="flex flex-col items-center gap-1.5 w-full px-2 pt-2 border-t border-[#302C28]">
          <button
            onClick={() => setZoom((z) => Math.min(z * 1.2, 4.5))}
            title="Zoom In (+)"
            className="w-8 h-8 rounded-lg text-[#C5AA8C] hover:bg-[#302C28] hover:text-[#FAF8F3] flex items-center justify-center"
          >
            <ZoomIn className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => setZoom((z) => Math.max(z * 0.8, 0.75))}
            title="Zoom Out (-)"
            className="w-8 h-8 rounded-lg text-[#C5AA8C] hover:bg-[#302C28] hover:text-[#FAF8F3] flex items-center justify-center"
          >
            <ZoomOut className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => {
              setZoom(1);
              setPanOffset({ x: 0, y: 0 });
            }}
            title="Reset View (R)"
            className="w-8 h-8 rounded-lg text-[#A18A76] hover:bg-[#302C28] hover:text-[#FAF8F3] flex items-center justify-center"
          >
            <RotateCcw className="w-3 h-3" />
          </button>
        </div>
      </aside>

      {/* 2. CENTER CANVAS: LARGE MAP VIEWPORT */}
      <section className="flex-1 min-w-0 relative overflow-hidden bg-[#24221F] flex items-center justify-center">
        {/* Floating Top Telemetry Bar */}
        <div className="absolute top-3 left-4 right-4 z-20 flex flex-wrap items-center justify-between gap-2 pointer-events-none">
          <div className="flex items-center gap-2 pointer-events-auto">
            <span className="px-2.5 py-1 rounded-lg bg-[#FAF8F3]/95 border border-[#D2C9BC] text-[11px] font-mono text-[#6B5748] shadow-sm">
              EPSG:4326 / UTM ZONE 43N (EPSG:32643)
            </span>
            <span className="hidden sm:inline-block px-2.5 py-1 rounded-lg bg-[#FAF8F3]/95 border border-[#D2C9BC] text-[11px] font-mono text-[#171615] shadow-sm">
              Scene: <strong>{bundle?.scene_id}</strong> ({parcels.length} parcels)
            </span>
          </div>

          <div className="flex items-center gap-2 pointer-events-auto">
            {/* Run AI Parcelling on AOI / Viewport */}
            <button
              onClick={() => handleRunDynamicParcelling()}
              disabled={isParcellingActive || busy}
              title="Run real multi-evidence GeoAI inference to generate candidate parcel boundaries"
              className="px-3.5 py-1.5 rounded-lg bg-[#24221F] hover:bg-[#302C28] text-[#FAF8F3] border border-[#302C28] text-xs font-mono flex items-center gap-2 shadow-sm transition-all disabled:opacity-50"
            >
              <Sparkles className={`w-3.5 h-3.5 text-[#C5AA8C] ${isParcellingActive ? "animate-spin" : ""}`} />
              <span className="font-semibold">
                {isParcellingActive ? "Synthesizing AI Parcels..." : "Run AI Parcelling"}
              </span>
            </button>

            {/* Quick Search Button */}
            <div className="relative">
              <button
                onClick={() => setIsSearchOpen((o) => !o)}
                className="px-3 py-1.5 rounded-lg bg-[#FAF8F3] border border-[#D2C9BC] text-xs font-mono text-[#24221F] flex items-center gap-2 shadow-sm hover:bg-[#EEEAE2]"
              >
                <Search className="w-3.5 h-3.5 text-[#6B5748]" />
                <span>Find Parcel</span>
              </button>

              {isSearchOpen && (
                <div className="absolute right-0 top-10 w-72 bg-[#FAF8F3] border border-[#D2C9BC] rounded-xl shadow-elevated p-3 z-30 animate-panel-enter">
                  <div className="flex items-center justify-between pb-2 border-b border-[#E4DFD5]">
                    <span className="text-xs font-mono font-semibold text-[#171615]">
                      Search Parcels
                    </span>
                    <button onClick={() => setIsSearchOpen(false)} className="text-[#8C8277]">
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Filter by ID, class, status..."
                    className="w-full mt-2 px-2.5 py-1.5 rounded-lg bg-[#FFFFFF] border border-[#D2C9BC] text-xs font-mono text-[#171615] focus:outline-none"
                  />
                  <div className="mt-2 max-h-48 overflow-y-auto space-y-1">
                    {filteredParcels.map((p) => (
                      <button
                        key={p.id}
                        onClick={() => {
                          onSelectParcel(p.id);
                          setIsSearchOpen(false);
                        }}
                        className={`w-full text-left px-2.5 py-1.5 rounded-lg text-xs font-mono flex items-center justify-between transition-colors ${
                          p.id === selectedParcelId
                            ? "bg-[#24221F] text-[#FAF8F3]"
                            : "hover:bg-[#EEEAE2] text-[#24221F]"
                        }`}
                      >
                        <span>{p.id.split("_").slice(-2).join("_")}</span>
                        <span className="text-[10px] opacity-75">{p.area_sqm?.toFixed(0)} m²</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Live Cursor Coordinate Pill */}
            <div className="px-3 py-1.5 rounded-lg bg-[#171615]/85 border border-[#3A3530] text-[11px] font-mono text-[#FAF8F3] shadow-sm">
              {cursorCoords.lon.toFixed(6)}° E, {cursorCoords.lat.toFixed(6)}° N
            </div>
          </div>
        </div>

        {/* Google Satellite Configuration Notice Banner */}
        <div className="absolute top-14 left-6 z-20 flex items-center gap-2">
          {!process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY ? (
            <div className="px-3 py-1.5 rounded-xl bg-[#FAF8F3]/95 border border-[#D2C9BC] shadow-elevated flex items-center gap-2 text-xs font-mono text-[#6B5748]">
              <span className="w-2 h-2 rounded-full bg-[#9E6B20] animate-pulse shrink-0" />
              <span>Google Satellite: Not configured (NEXT_PUBLIC_GOOGLE_MAPS_API_KEY unset) — Operating in Sovereign WebGIS Mode</span>
            </div>
          ) : googleMapError ? (
            <div className="px-3 py-1.5 rounded-xl bg-[#FFF5F5]/95 border border-[#E05252] shadow-elevated flex items-center gap-2 text-xs font-mono text-[#E05252]">
              <span className="w-2 h-2 rounded-full bg-[#E05252] shrink-0" />
              <span>Google Satellite: {googleMapError} — Fallback to Sovereign WebGIS Mode</span>
            </div>
          ) : (
            <div className="px-3 py-1.5 rounded-xl bg-[#FAF8F3]/95 border border-[#3D6B52] shadow-elevated flex items-center gap-2 text-xs font-mono text-[#3D6B52]">
              <span className="w-2 h-2 rounded-full bg-[#3D6B52] shrink-0 animate-pulse" />
              <span>Google Satellite: Active (Pune Historic Core 18.52° N, 73.85° E)</span>
            </div>
          )}
        </div>

        {/* Status Notification Banner */}
        {statusNotification && (
          <div className="absolute top-14 left-1/2 -translate-x-1/2 z-30 max-w-lg px-4 py-2 rounded-xl bg-[#FAF8F3] border border-[#D2C9BC] shadow-elevated flex items-center gap-2.5 text-xs text-[#171615] animate-modal-enter">
            {statusNotification.type === "success" && (
              <CheckCircle2 className="w-4 h-4 text-[#3D6B52] shrink-0" />
            )}
            {statusNotification.type === "info" && (
              <Info className="w-4 h-4 text-[#6B5748] shrink-0" />
            )}
            {statusNotification.type === "error" && (
              <AlertTriangle className="w-4 h-4 text-[#9E3E37] shrink-0" />
            )}
            <span className="flex-1 font-mono text-[11px]">{statusNotification.msg}</span>
            <button
              onClick={() => setStatusNotification(null)}
              className="text-[#8C8277] hover:text-[#171615]"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        {/* Measure Tool Readout Banner */}
        {activeTool === "measure" && (
          <div className="absolute top-14 left-6 z-20 px-3.5 py-2 rounded-xl bg-[#FAF8F3] border border-[#D2C9BC] text-xs font-mono text-[#171615] shadow-elevated space-y-1">
            <div className="text-[10px] text-[#6B5748] uppercase tracking-wider">
              Metric Distance Measurement
            </div>
            {measuredDistanceM !== null ? (
              <div className="text-sm font-bold text-[#171615]">
                {measuredDistanceM} meters (Ground Distance)
              </div>
            ) : (
              <div className="text-[11px] text-[#8C8277]">
                Click 2 points on the map to measure linear distance.
              </div>
            )}
          </div>
        )}

        {/* AOI Box Selection Mode Active Banner */}
        {activeTool === "aoi_box" && (
          <div className="absolute top-14 left-6 z-20 px-4 py-2.5 rounded-xl bg-[#FAF8F3] border border-[#8A735F] shadow-elevated text-xs space-y-2">
            <div className="font-mono text-[11px] text-[#8A735F] font-semibold flex items-center gap-2">
              <Scan className="w-3.5 h-3.5" />
              <span>Select AOI: {aoiBoxPoints.length}/2 corners defined</span>
            </div>
            <div className="text-[11px] text-[#6B5748]">
              {aoiBoxPoints.length === 0 && "Click first corner of your Area of Interest."}
              {aoiBoxPoints.length === 1 && "Click opposite corner to define the AOI bounding box."}
              {aoiBoxPoints.length >= 2 && "AOI defined! Click 'Run AI Parcelling' to synthesize candidates."}
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => handleRunDynamicParcelling()}
                disabled={isParcellingActive || aoiBoxPoints.length < 2}
                className="btn-primary-dark px-3 py-1 rounded-lg text-xs font-medium disabled:opacity-50 flex items-center gap-1.5"
              >
                <Sparkles className="w-3 h-3 text-[#C5AA8C]" />
                <span>Run AI Parcelling on AOI</span>
              </button>
              <button
                onClick={() => {
                  setAoiBoxPoints([]);
                  setActiveTool("select");
                }}
                className="px-2.5 py-1 rounded-lg bg-[#EEEAE2] text-[#24221F] text-xs"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Interactive SVG Viewport */}
        <div className="relative w-full h-full flex items-center justify-center overflow-hidden">
          {/* Google Satellite Basemap Background Layer */}
          {Boolean(process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY) && (
            <div
              ref={googleMapRef}
              className={`absolute inset-0 w-full h-full z-0 pointer-events-none transition-opacity duration-300 ${
                layers.googleSatellite ? "opacity-100" : "opacity-0 pointer-events-none"
              }`}
            />
          )}

          <svg
            ref={svgRef}
            viewBox={`0 0 ${VIEW_SIZE} ${VIEW_SIZE}`}
            style={{
              transform: `translate3d(${panOffset.x}px, ${panOffset.y}px, 0) scale(${zoom})`,
              transformOrigin: "center center",
            }}
            className={`w-full h-full max-h-[88vh] max-w-[88vh] select-none z-10 relative ${
              activeTool === "pan" || isPanning
                ? "cursor-grab active:cursor-grabbing"
                : activeTool === "draw" || activeTool === "measure"
                ? "cursor-crosshair"
                : activeTool === "edit"
                ? "cursor-default"
                : "cursor-pointer"
            }`}
            onMouseDown={handleSvgMouseDown}
            onMouseMove={handleSvgMouseMove}
            onMouseUp={handleSvgMouseUp}
            onWheel={handleSvgWheel}
            onClick={handleCanvasClick}
          >
            {/* 1. Drone Ortho RGB Imagery Layer (Synthetic scene raster - mutually exclusive with Google Satellite) */}
            {layers.imagery && !layers.googleSatellite && bundle?.scene_id && (
              <image
                href={`${API_BASE}/api/scenes/${bundle.scene_id}/rgb.png`}
                x={0}
                y={0}
                width={VIEW_SIZE}
                height={VIEW_SIZE}
                preserveAspectRatio="none"
                opacity={1.0}
              />
            )}

            {/* 2. DSM Grid Elevation Lines */}
            {layers.dsm && (
              <g opacity={0.35}>
                {[120, 240, 360, 480, 600].map((pos) => (
                  <React.Fragment key={pos}>
                    <line
                      x1={pos}
                      y1={0}
                      x2={pos}
                      y2={VIEW_SIZE}
                      stroke="#C5AA8C"
                      strokeDasharray="4 4"
                      strokeWidth={1}
                    />
                    <line
                      x1={0}
                      y1={pos}
                      x2={VIEW_SIZE}
                      y2={pos}
                      stroke="#C5AA8C"
                      strokeDasharray="4 4"
                      strokeWidth={1}
                    />
                  </React.Fragment>
                ))}
              </g>
            )}

            {/* 3. Road Corridors Layer */}
            {layers.roads &&
              roads.map((r) => {
                const pts = r.geometry?.coordinates || [];
                if (pts.length < 2) return null;
                const [x1, y1] = lonLatToSvg(pts[0][0], pts[0][1]);
                const [x2, y2] = lonLatToSvg(pts[pts.length - 1][0], pts[pts.length - 1][1]);
                return (
                  <g key={r.id}>
                    <line
                      x1={x1}
                      y1={y1}
                      x2={x2}
                      y2={y2}
                      stroke="#24221F"
                      strokeWidth={r.road_class === "MAIN_ROAD" ? 22 : 14}
                      strokeLinecap="round"
                      opacity={0.65}
                    />
                    <line
                      x1={x1}
                      y1={y1}
                      x2={x2}
                      y2={y2}
                      stroke="#FAF8F3"
                      strokeWidth={1.4}
                      strokeDasharray="6 4"
                      opacity={0.85}
                    />
                  </g>
                );
              })}

            {/* 4. Reference GIS Parcels Layer (Subtle Dotted Line) */}
            {layers.referenceParcels &&
              refParcels.map((rp) => {
                const ring = rp.geometry?.coordinates?.[0];
                if (!ring) return null;
                return (
                  <polygon
                    key={rp.id}
                    points={ringToSvgPoints(ring)}
                    fill="none"
                    stroke="#8A735F"
                    strokeWidth={1.8}
                    strokeDasharray="4 3"
                    opacity={0.7}
                  />
                );
              })}

            {/* 5. Candidate Parcels Layer */}
            {layers.candidateParcels &&
              parcels.map((p) => {
                const ring = p.geometry?.coordinates?.[0];
                if (!ring) return null;
                const isSelected = p.id === selectedParcelId;
                const isHighlighted = highlightedIds.includes(p.id);
                const { fill, stroke } = getParcelStyle(p);
                const [cx, cy] = lonLatToSvg(
                  p.ulpin_ready_metadata?.centroid_lon || ring[0][0],
                  p.ulpin_ready_metadata?.centroid_lat || ring[0][1]
                );

                return (
                  <g
                    key={p.id}
                    onClick={(e) => {
                      e.stopPropagation();
                      if (activeTool === "select" || activeTool === "edit") {
                        onSelectParcel(p.id);
                      }
                    }}
                    className="cursor-pointer"
                  >
                    <polygon
                      points={ringToSvgPoints(ring)}
                      fill={fill}
                      fillOpacity={isSelected ? 0.6 : isHighlighted ? 0.5 : 0.3}
                      stroke={isSelected ? "#FAF8F3" : isHighlighted ? "#FDE68A" : stroke}
                      strokeWidth={isSelected ? 3.2 : isHighlighted ? 2.6 : 1.8}
                      strokeDasharray={
                        p.boundary_representation === "INFERRED" ? "6 3" : undefined
                      }
                    />
                    {/* Centroid Parcel ID badge */}
                    <g transform={`translate(${cx}, ${cy})`}>
                      <rect
                        x="-24"
                        y="-10"
                        width="48"
                        height="20"
                        rx="4"
                        fill="#171615"
                        fillOpacity="0.82"
                        stroke={isSelected ? "#FAF8F3" : "#8A735F"}
                        strokeWidth="1"
                      />
                      <text
                        x="0"
                        y="3"
                        textAnchor="middle"
                        fill="#FAF8F3"
                        fontSize="10"
                        fontFamily="JetBrains Mono, monospace"
                        fontWeight="600"
                        className="pointer-events-none"
                      >
                        {p.id.split("_").slice(-2).join("_")}
                      </text>
                    </g>
                  </g>
                );
              })}

            {/* 6. Extracted Boundaries Layer */}
            {layers.boundaries &&
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
                    stroke={isVis ? "#3D6B52" : "#9E6B20"}
                    strokeWidth={isVis ? 2 : 1.6}
                    strokeDasharray={isVis ? undefined : "5 3"}
                    opacity={0.85}
                  />
                );
              })}

            {/* 7. Building Footprints Layer */}
            {layers.buildings &&
              buildings.map((b) => {
                const ring = b.geometry?.coordinates?.[0];
                if (!ring) return null;
                const isHi = highlightedIds.includes(b.id);
                return (
                  <polygon
                    key={b.id}
                    points={ringToSvgPoints(ring)}
                    fill="rgba(184, 154, 120, 0.45)"
                    stroke={isHi ? "#FAF8F3" : "#C5AA8C"}
                    strokeWidth={isHi ? 2.5 : 1.4}
                  />
                );
              })}

            {/* 8. Topology Issues Layer (OVERLAPS, GAPS) */}
            {layers.topology &&
              topoIssues.map((iss) => {
                const ring = iss.geometry?.coordinates?.[0];
                if (!ring || !Array.isArray(ring[0])) return null;
                return (
                  <polygon
                    key={iss.id}
                    points={ringToSvgPoints(ring)}
                    fill="rgba(158, 62, 55, 0.65)"
                    stroke="#FCA5A5"
                    strokeWidth={2}
                  />
                );
              })}

            {/* 9. GIS Conflicts & Anomalies Layer */}
            {layers.anomalies &&
              anomalies.map((anom) => {
                const ring =
                  anom.geometry?.type === "Polygon"
                    ? anom.geometry.coordinates?.[0]
                    : anom.geometry?.type === "MultiPolygon"
                    ? anom.geometry.coordinates?.[0]?.[0]
                    : null;
                if (!ring) return null;
                return (
                  <polygon
                    key={anom.id}
                    points={ringToSvgPoints(ring)}
                    fill="none"
                    stroke={anom.category === "GIS_CONFLICT" ? "#9E3E37" : "#8A735F"}
                    strokeWidth={2}
                    strokeDasharray="3 3"
                  />
                );
              })}

            {/* 10. Temporal Changes Layer */}
            {layers.changes &&
              changes.map((chg) => {
                const ring = chg.geometry?.coordinates?.[0];
                if (!ring) return null;
                return (
                  <polygon
                    key={chg.id}
                    points={ringToSvgPoints(ring)}
                    fill="rgba(158, 107, 32, 0.4)"
                    stroke="#FDE68A"
                    strokeWidth={2}
                  />
                );
              })}

            {/* 11. Smart Field Route Paths */}
            {layers.routes &&
              routes.map((rt, rIdx) => {
                const pts = rt.geometry?.coordinates || [];
                const svgPts = pts
                  .map((pt: number[]) => lonLatToSvg(pt[0], pt[1]).join(","))
                  .join(" ");
                const strokeCol = rIdx === 0 ? "#C5AA8C" : "#A18A76";
                return (
                  <g key={rt.id}>
                    <polyline
                      points={svgPts}
                      fill="none"
                      stroke={strokeCol}
                      strokeWidth={2.8}
                      strokeDasharray="6 4"
                    />
                    {(rt.ordered_stops || []).map((st: any) => {
                      const [sx, sy] = lonLatToSvg(st.lon, st.lat);
                      return (
                        <g key={st.task_id}>
                          <circle
                            cx={sx}
                            cy={sy}
                            r={9}
                            fill="#24221F"
                            stroke="#FAF8F3"
                            strokeWidth={1.5}
                          />
                          <text
                            x={sx}
                            y={sy + 3.5}
                            textAnchor="middle"
                            fill="#FAF8F3"
                            fontSize="10"
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

            {/* 12. Active Parcel Vertex Handles (when selected and in edit mode) */}
            {selectedParcel && editingVertices.length >= 3 && activeTool === "edit" && (
              <g>
                <polygon
                  points={ringToSvgPoints([...editingVertices, editingVertices[0]])}
                  fill="none"
                  stroke="#FAF8F3"
                  strokeWidth={2.4}
                  strokeDasharray="4 2"
                />
                {editingVertices.map((pt, idx) => {
                  const [vx, vy] = lonLatToSvg(pt[0], pt[1]);
                  const isActive = idx === selectedVertexIdx;
                  return (
                    <g key={idx}>
                      <circle
                        cx={vx}
                        cy={vy}
                        r={isActive ? 7.5 : 5.5}
                        fill={isActive ? "#C5AA8C" : "#FAF8F3"}
                        stroke="#171615"
                        strokeWidth={2}
                        className="cursor-move"
                        onMouseDown={(e) => {
                          e.stopPropagation();
                          setSelectedVertexIdx(idx);
                          setDraggingVertexIdx(idx);
                        }}
                      />
                      <text
                        x={vx + 8}
                        y={vy - 6}
                        fill="#FAF8F3"
                        fontSize="9"
                        fontFamily="JetBrains Mono, monospace"
                        fontWeight="bold"
                        className="pointer-events-none drop-shadow"
                      >
                        v{idx + 1}
                      </text>
                    </g>
                  );
                })}
              </g>
            )}

            {/* 13. Measure Tool Line Preview */}
            {activeTool === "measure" && measurePoints.length > 0 && (
              <g>
                {measurePoints.map((pt, i) => {
                  const [mx, my] = lonLatToSvg(pt[0], pt[1]);
                  return <circle key={i} cx={mx} cy={my} r={5} fill="#FAF8F3" stroke="#171615" strokeWidth={2} />;
                })}
                {measurePoints.length === 2 && (
                  <line
                    x1={lonLatToSvg(measurePoints[0][0], measurePoints[0][1])[0]}
                    y1={lonLatToSvg(measurePoints[0][0], measurePoints[0][1])[1]}
                    x2={lonLatToSvg(measurePoints[1][0], measurePoints[1][1])[0]}
                    y2={lonLatToSvg(measurePoints[1][0], measurePoints[1][1])[1]}
                    stroke="#FAF8F3"
                    strokeWidth={2}
                    strokeDasharray="4 4"
                  />
                )}
              </g>
            )}

            {/* 14. Digitize New Parcel Points Preview */}
            {activeTool === "draw" && drawnPoints.length > 0 && (
              <g>
                <polyline
                  points={ringToSvgPoints(drawnPoints)}
                  fill="rgba(61, 107, 82, 0.25)"
                  stroke="#3D6B52"
                  strokeWidth={2.4}
                />
                {drawnPoints.map((pt, i) => {
                  const [dx, dy] = lonLatToSvg(pt[0], pt[1]);
                  return (
                    <circle
                      key={i}
                      cx={dx}
                      cy={dy}
                      r={5}
                      fill="#C5AA8C"
                      stroke="#171615"
                      strokeWidth={1.5}
                    />
                  );
                })}
              </g>
            )}

            {/* 15. AOI Box Selection Preview */}
            {activeTool === "aoi_box" && aoiBoxPoints.length > 0 && (
              <g>
                {aoiBoxPoints.map((pt, i) => {
                  const [ax, ay] = lonLatToSvg(pt[0], pt[1]);
                  return (
                    <circle
                      key={i}
                      cx={ax}
                      cy={ay}
                      r={6}
                      fill="#F59E0B"
                      stroke="#171615"
                      strokeWidth={2}
                    />
                  );
                })}
                {aoiBoxPoints.length === 2 && (() => {
                  const [p1x, p1y] = lonLatToSvg(aoiBoxPoints[0][0], aoiBoxPoints[0][1]);
                  const [p2x, p2y] = lonLatToSvg(aoiBoxPoints[1][0], aoiBoxPoints[1][1]);
                  const rx = Math.min(p1x, p2x);
                  const ry = Math.min(p1y, p2y);
                  const rw = Math.abs(p2x - p1x);
                  const rh = Math.abs(p2y - p1y);
                  return (
                    <rect
                      x={rx}
                      y={ry}
                      width={rw}
                      height={rh}
                      fill="rgba(245, 158, 11, 0.18)"
                      stroke="#F59E0B"
                      strokeWidth={2.5}
                      strokeDasharray="6 4"
                    />
                  );
                })()}
              </g>
            )}

            {/* 15. Maharashtra Administrative Hierarchy Overlay */}
            {layers.adminBoundaries && adminData?.features && (
              <g id="mh_admin_boundaries_layer" opacity={0.85}>
                {adminData.features.map((feat: any) => {
                  const props = feat.properties || {};
                  const coords = feat.geometry?.coordinates?.[0] || [];
                  if (coords.length < 3) return null;
                  const ptsStr = ringToSvgPoints(coords);
                  const isState = props.admin_level === 1;
                  const isDist = props.admin_level === 2;
                  const strokeCol = isState ? "#171615" : isDist ? "#4F708F" : "#8A735F";
                  const fillCol = isState ? "none" : isDist ? "rgba(79, 112, 143, 0.08)" : "rgba(138, 115, 95, 0.12)";
                  return (
                    <g key={feat.id || props.taluk_name || props.district_name}>
                      <polygon
                        points={ptsStr}
                        fill={fillCol}
                        stroke={strokeCol}
                        strokeWidth={isState ? 3.5 : isDist ? 2.5 : 1.5}
                        strokeDasharray={isState ? "6 3" : undefined}
                      />
                      {props.hq_lon && props.hq_lat && (
                        <g>
                          <circle
                            cx={lonLatToSvg(props.hq_lon, props.hq_lat)[0]}
                            cy={lonLatToSvg(props.hq_lon, props.hq_lat)[1]}
                            r={4.5}
                            fill="#9E3E37"
                            stroke="#FAF8F3"
                            strokeWidth={1.5}
                          />
                          <text
                            x={lonLatToSvg(props.hq_lon, props.hq_lat)[0] + 6}
                            y={lonLatToSvg(props.hq_lon, props.hq_lat)[1] - 4}
                            fill="#171615"
                            fontSize="9"
                            fontFamily="JetBrains Mono, monospace"
                            fontWeight="bold"
                            className="pointer-events-none drop-shadow"
                          >
                            {props.taluk_name || props.district_name} HQ
                          </text>
                        </g>
                      )}
                    </g>
                  );
                })}
              </g>
            )}

            {/* 16. Pune Historic Core Pilot Real Evidence Overlay */}
            {layers.punePilot && puneData && (
              <g id="pune_pilot_evidence_layer">
                {/* Pune Buildings Sample */}
                {(puneData.buildings_geojson?.features || []).slice(0, 300).map((b: any, i: number) => {
                  const coords = b.geometry?.coordinates?.[0] || [];
                  if (coords.length < 3) return null;
                  return (
                    <polygon
                      key={`pune_bldg_${i}`}
                      points={ringToSvgPoints(coords)}
                      fill="rgba(197, 170, 140, 0.65)"
                      stroke="#8A735F"
                      strokeWidth={1.2}
                    />
                  );
                })}
                {/* Pune Roads Sample */}
                {(puneData.roads_geojson?.features || []).slice(0, 150).map((r: any, i: number) => {
                  const pts = r.geometry?.coordinates || [];
                  if (pts.length < 2) return null;
                  const [x1, y1] = lonLatToSvg(pts[0][0], pts[0][1]);
                  const [x2, y2] = lonLatToSvg(pts[pts.length - 1][0], pts[pts.length - 1][1]);
                  return (
                    <line
                      key={`pune_road_${i}`}
                      x1={x1}
                      y1={y1}
                      x2={x2}
                      y2={y2}
                      stroke="#4F708F"
                      strokeWidth={2.5}
                      strokeDasharray="3 3"
                    />
                  );
                })}
              </g>
            )}

            {/* 17. Real Sentinel-2 L2A Contextual Multispectral Evidence Overlay */}
            {layers.sentinel2 && sentinelData?.status === "ACQUIRED_AND_VERIFIED" && (
              <g id="sentinel2_context_overlay" opacity={0.65}>
                {/* 10m Ground Sample Distance Raster Grid Visualization */}
                <rect
                  x={0}
                  y={0}
                  width={VIEW_SIZE}
                  height={VIEW_SIZE}
                  fill="rgba(46, 125, 50, 0.12)"
                  stroke="#2E7D32"
                  strokeWidth={2}
                />
                <text
                  x={14}
                  y={24}
                  fill="#1B5E20"
                  fontSize="11"
                  fontFamily="JetBrains Mono, monospace"
                  fontWeight="bold"
                  className="pointer-events-none drop-shadow"
                >
                  Sentinel-2 L2A (10m Multispectral Context) • B02/B03/B04/B08/NDVI • Item: {sentinelData.tile_id}
                </text>
              </g>
            )}
          </svg>
        </div>

        {/* Floating Bottom Layer & Thematic Styling Dock */}
        <div className="absolute bottom-3 left-4 right-4 z-20 flex justify-center pointer-events-none">
          <div className="bg-[#FAF8F3]/95 backdrop-blur-md border border-[#D2C9BC] rounded-2xl px-3.5 py-2 shadow-elevated flex flex-wrap items-center justify-center gap-2.5 pointer-events-auto max-w-4xl text-xs text-[#24221F]">
            <div className="flex items-center gap-1.5 border-r border-[#D2C9BC] pr-2.5 shrink-0">
              <span className="font-mono text-[10px] text-[#6B5748] uppercase">Thematic:</span>
              {(["confidence", "landuse", "verification"] as const).map((mode) => (
                <button
                  key={mode}
                  onClick={() => setColorMode(mode)}
                  className={`px-2 py-0.5 rounded-md text-[11px] font-mono capitalize transition-colors ${
                    colorMode === mode
                      ? "bg-[#24221F] text-[#FAF8F3]"
                      : "text-[#6B5748] hover:bg-[#EEEAE2]"
                  }`}
                >
                  {mode}
                </button>
              ))}
            </div>

            <div className="flex flex-wrap items-center justify-center gap-1">
              {[
                ["googleSatellite", "Google Satellite"],
                ["imagery", "RGB Ortho"],
                ["candidateParcels", "AI Parcels"],
                ["referenceParcels", "Ref GIS"],
                ["buildings", "Buildings"],
                ["roads", "Roads"],
                ["boundaries", "Boundary Types"],
                ["topology", "Topology"],
                ["anomalies", "Conflicts"],
                ["routes", "Field Routes"],
                ["adminBoundaries", "MH Admin Hierarchy"],
                ["punePilot", "Pune Pilot Vector"],
                ["sentinel2", "Sentinel-2 Multispectral"],
              ].map(([key, label]) => {
                const isEnabled = (layers as any)[key];
                return (
                  <button
                    key={key}
                    onClick={() => {
                      if (key === "googleSatellite") {
                        setLayers((prev) => ({
                          ...prev,
                          googleSatellite: !prev.googleSatellite,
                          imagery: !prev.googleSatellite ? false : prev.imagery,
                        }));
                      } else if (key === "imagery") {
                        setLayers((prev) => ({
                          ...prev,
                          imagery: !prev.imagery,
                          googleSatellite: !prev.imagery ? false : prev.googleSatellite,
                        }));
                      } else {
                        setLayers((prev) => ({ ...prev, [key]: !isEnabled }));
                      }
                    }}
                    className={`px-2 py-0.5 rounded text-[11px] font-mono transition-all whitespace-nowrap ${
                      isEnabled
                        ? "bg-[#EEEAE2] text-[#171615] border border-[#A18A76]"
                        : "text-[#8C8277] hover:bg-[#EEEAE2]/60 line-through opacity-60"
                    }`}
                  >
                    {label}
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </section>

      {/* 3. RIGHT PANEL: CONTEXT INSPECTOR */}
      <aside className="w-80 sm:w-96 shrink-0 bg-[#FAF8F3] border-l border-[#D2C9BC] flex flex-col justify-between overflow-y-auto z-20 shadow-lg">
        {!selectedParcel ? (
          <div className="p-6 text-center space-y-4 my-auto">
            <div className="w-12 h-12 rounded-2xl bg-[#EEEAE2] text-[#6B5748] flex items-center justify-center mx-auto">
              <Navigation className="w-6 h-6" />
            </div>
            <div className="space-y-1">
              <h3 className="font-editorial text-2xl text-[#171615]">Context Inspector</h3>
              <p className="text-xs text-[#5C554E] leading-relaxed">
                Click any candidate parcel polygon on the Web-GIS canvas or use the search drawer to inspect multi-layer AI evidence, topology, and edit geometry.
              </p>
            </div>
            <div className="pt-2 text-[11px] font-mono text-[#8C8277]">
              Active Scene: {bundle?.scene_id || "scene_urban_T1"} • {parcels.length} Candidate Parcels
            </div>
          </div>
        ) : (
          <div className="p-5 space-y-5">
            {/* Header info */}
            <div className="flex items-start justify-between border-b border-[#E4DFD5] pb-3.5">
              <div>
                <span className="text-[10px] font-mono uppercase tracking-wider text-[#6B5748] block">
                  {selectedParcel.verification_status} • v{selectedParcel.version || 1}
                </span>
                <h3 className="font-mono text-base font-bold text-[#171615] mt-0.5">
                  {selectedParcel.id}
                </h3>
              </div>
              <span
                className={`px-2.5 py-1 rounded-lg text-xs font-mono font-semibold ${
                  selectedParcel.confidence >= 0.82
                    ? "bg-[#EBF2EE] text-[#3D6B52] border border-[#BDD4C6]"
                    : "bg-[#F8F1E5] text-[#9E6B20] border border-[#E5CFA8]"
                }`}
              >
                {(selectedParcel.confidence * 100).toFixed(0)}% Conf
              </span>
            </div>

            {/* Metrics grid */}
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="p-2.5 rounded-xl bg-[#F4F1EA] border border-[#E4DFD5]">
                <div className="text-[10px] font-mono text-[#8C8277] uppercase">Metric Area</div>
                <div className="font-mono text-sm font-semibold text-[#171615] mt-0.5">
                  {selectedParcel.area_sqm?.toFixed(1)} m²
                </div>
              </div>
              <div className="p-2.5 rounded-xl bg-[#F4F1EA] border border-[#E4DFD5]">
                <div className="text-[10px] font-mono text-[#8C8277] uppercase">Perimeter</div>
                <div className="font-mono text-sm font-semibold text-[#171615] mt-0.5">
                  {selectedParcel.perimeter_m?.toFixed(1)} m
                </div>
              </div>
              <div className="p-2.5 rounded-xl bg-[#F4F1EA] border border-[#E4DFD5]">
                <div className="text-[10px] font-mono text-[#8C8277] uppercase">Boundary Class</div>
                <div className="font-mono text-xs font-semibold text-[#6B5748] mt-0.5 truncate">
                  {selectedParcel.boundary_representation}
                </div>
              </div>
              <div className="p-2.5 rounded-xl bg-[#F4F1EA] border border-[#E4DFD5]">
                <div className="text-[10px] font-mono text-[#8C8277] uppercase">Topology State</div>
                <div
                  className={`font-mono text-xs font-semibold mt-0.5 ${
                    selectedParcel.topology_status === "VALID"
                      ? "text-[#3D6B52]"
                      : "text-[#9E3E37]"
                  }`}
                >
                  {selectedParcel.topology_status}
                </div>
              </div>
            </div>

            {/* Vertex & Precision Editing Controls */}
            <div className="p-3.5 rounded-xl bg-[#F4F1EA] border border-[#E4DFD5] space-y-3">
              <div className="flex items-center justify-between text-xs">
                <span className="font-mono font-semibold text-[#24221F]">
                  Vertex Refinement ({editingVertices.length} nodes)
                </span>
                <button
                  onClick={() => setActiveTool("edit")}
                  className={`px-2 py-0.5 rounded text-[10px] font-mono ${
                    activeTool === "edit"
                      ? "bg-[#24221F] text-[#FAF8F3]"
                      : "bg-[#EEEAE2] text-[#6B5748]"
                  }`}
                >
                  {activeTool === "edit" ? "Edit Mode Active" : "Toggle Edit"}
                </button>
              </div>

              {/* Cardinal Precision Nudge */}
              {editingVertices.length > 0 && (
                <div className="flex items-center justify-between gap-1 text-[11px] font-mono bg-[#FFFFFF] p-1.5 rounded-lg border border-[#D2C9BC]">
                  <span className="text-[#6B5748] font-semibold pl-1">
                    v{selectedVertexIdx + 1}:
                  </span>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => handleNudgeVertex(-0.00004, 0)}
                      className="px-1.5 py-0.5 rounded bg-[#EEEAE2] hover:bg-[#D2C9BC]"
                    >
                      ← W
                    </button>
                    <button
                      onClick={() => handleNudgeVertex(0.00004, 0)}
                      className="px-1.5 py-0.5 rounded bg-[#EEEAE2] hover:bg-[#D2C9BC]"
                    >
                      E →
                    </button>
                    <button
                      onClick={() => handleNudgeVertex(0, 0.00004)}
                      className="px-1.5 py-0.5 rounded bg-[#EEEAE2] hover:bg-[#D2C9BC]"
                    >
                      ↑ N
                    </button>
                    <button
                      onClick={() => handleNudgeVertex(0, -0.00004)}
                      className="px-1.5 py-0.5 rounded bg-[#EEEAE2] hover:bg-[#D2C9BC]"
                    >
                      ↓ S
                    </button>
                  </div>
                </div>
              )}

              <div className="grid grid-cols-3 gap-1.5 text-xs font-mono">
                <button
                  onClick={handleAddVertex}
                  className="py-1 px-2 rounded-lg bg-[#FAF8F3] hover:bg-[#EEEAE2] border border-[#D2C9BC] text-[#24221F]"
                >
                  + Add Node
                </button>
                <button
                  onClick={handleDeleteVertex}
                  className="py-1 px-2 rounded-lg bg-[#FAF8F3] hover:bg-[#EEEAE2] border border-[#D2C9BC] text-[#9E3E37]"
                >
                  - Delete
                </button>
                <button
                  onClick={handleSnapToReference}
                  className="py-1 px-2 rounded-lg bg-[#FAF8F3] hover:bg-[#EEEAE2] border border-[#D2C9BC] text-[#6B5748]"
                >
                  Snap Ref
                </button>
              </div>

              {/* Land Use & Audit Note */}
              <div className="space-y-2 text-xs pt-1">
                <div>
                  <label className="text-[10px] font-mono text-[#6B5748] block mb-1">
                    Land-Use Category
                  </label>
                  <select
                    value={editLandUse}
                    onChange={(e) => setEditLandUse(e.target.value)}
                    className="w-full bg-[#FFFFFF] border border-[#D2C9BC] rounded-lg px-2.5 py-1 text-xs font-mono text-[#171615]"
                  >
                    {Object.keys(LAND_USE_PALETTE).map((lu) => (
                      <option key={lu} value={lu}>
                        {lu}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-[10px] font-mono text-[#6B5748] block mb-1">
                    Surveyor Verification Audit Reason
                  </label>
                  <input
                    type="text"
                    value={editReason}
                    onChange={(e) => setEditReason(e.target.value)}
                    className="w-full bg-[#FFFFFF] border border-[#D2C9BC] rounded-lg px-2.5 py-1 text-xs font-mono text-[#171615]"
                  />
                </div>
              </div>

              <button
                onClick={() => handleSaveParcelEdit()}
                disabled={busy}
                className="w-full btn-primary-dark py-2 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 shadow-sm"
              >
                <span>Commit Geometry to PostGIS</span>
              </button>
            </div>

            {/* Split / Merge Actions */}
            <div className="p-3.5 rounded-xl bg-[#F4F1EA] border border-[#E4DFD5] space-y-2.5">
              <div className="text-xs font-mono font-semibold text-[#24221F]">
                Subdivision & Merge Operations
              </div>
              <div className="grid grid-cols-2 gap-1.5 text-xs font-mono">
                <button
                  onClick={() => handleSplitParcel("VERTICAL")}
                  disabled={busy}
                  className="py-1.5 px-2 rounded-lg bg-[#FAF8F3] hover:bg-[#EEEAE2] border border-[#D2C9BC] text-[#24221F]"
                >
                  Split (Vertical)
                </button>
                <button
                  onClick={() => handleSplitParcel("HORIZONTAL")}
                  disabled={busy}
                  className="py-1.5 px-2 rounded-lg bg-[#FAF8F3] hover:bg-[#EEEAE2] border border-[#D2C9BC] text-[#24221F]"
                >
                  Split (Horiz.)
                </button>
              </div>

              <div className="flex items-center gap-1.5 pt-1">
                <select
                  value={mergeTargetId}
                  onChange={(e) => setMergeTargetId(e.target.value)}
                  className="flex-1 bg-[#FFFFFF] border border-[#D2C9BC] rounded-lg px-2 py-1 text-xs font-mono text-[#171615]"
                >
                  {parcels
                    .filter((p) => p.id !== selectedParcel.id)
                    .map((p) => (
                      <option key={p.id} value={p.id}>
                        Merge with {p.id.split("_").slice(-2).join("_")}
                      </option>
                    ))}
                </select>
                <button
                  onClick={handleMergeParcels}
                  disabled={busy || !mergeTargetId}
                  className="px-3 py-1 rounded-lg bg-[#24221F] text-[#FAF8F3] text-xs font-mono"
                >
                  Merge
                </button>
                <button
                  onClick={handleDeleteParcel}
                  disabled={busy}
                  className="px-2.5 py-1 rounded-lg bg-[#F9ECEB] border border-[#E5B8B5] text-[#9E3E37] text-xs font-mono"
                >
                  Delete
                </button>
              </div>
            </div>

            {/* Direct Surveyor Verification Actions */}
            <div className="p-3.5 rounded-xl bg-[#FAF8F3] border border-[#D2C9BC] space-y-2">
              <div className="text-xs font-mono font-semibold text-[#171615]">
                Authoritative Surveyor Sign-off
              </div>
              <div className="grid grid-cols-3 gap-1.5 text-xs font-mono">
                <button
                  onClick={() => handleSaveParcelEdit("HUMAN_VERIFIED")}
                  disabled={busy}
                  className="py-2 px-2 rounded-xl bg-[#EBF2EE] hover:bg-[#BDD4C6] border border-[#BDD4C6] text-[#3D6B52] font-semibold text-center"
                >
                  ✓ Verify
                </button>
                <button
                  onClick={() => handleSaveParcelEdit("FIELD_VISIT_REQUESTED")}
                  disabled={busy}
                  className="py-2 px-2 rounded-xl bg-[#F8F1E5] hover:bg-[#E5CFA8] border border-[#E5CFA8] text-[#9E6B20] font-semibold text-center"
                >
                  ⚑ Flag Visit
                </button>
                <button
                  onClick={() => handleSaveParcelEdit("REJECTED")}
                  disabled={busy}
                  className="py-2 px-2 rounded-xl bg-[#F9ECEB] hover:bg-[#E5B8B5] border border-[#E5B8B5] text-[#9E3E37] font-semibold text-center"
                >
                  ✕ Reject
                </button>
              </div>
            </div>

            {/* AI Confidence Breakdown & Provenance Lineage */}
            {selectedParcel.confidence_breakdown && (
              <div className="p-3.5 rounded-xl bg-[#F4F1EA] border border-[#E4DFD5] space-y-2 text-xs">
                <div className="font-mono text-[10px] uppercase tracking-wider text-[#6B5748]">
                  Multi-Modal Confidence Breakdown
                </div>
                <div className="space-y-1.5">
                  {Object.entries(selectedParcel.confidence_breakdown).map(
                    ([k, v]: [string, any]) => (
                      <div key={k} className="space-y-0.5">
                        <div className="flex justify-between font-mono text-[10px]">
                          <span className="text-[#5C554E] capitalize">
                            {k.replace(/_/g, " ")}
                          </span>
                          <span className="font-semibold text-[#171615]">
                            {(Number(v) * 100).toFixed(0)}%
                          </span>
                        </div>
                        <div className="w-full h-1.5 bg-[#E4DFD5] rounded-full overflow-hidden">
                          <div
                            className="h-full bg-[#6B5748] rounded-full"
                            style={{ width: `${Math.min(100, Number(v) * 100)}%` }}
                          />
                        </div>
                      </div>
                    )
                  )}
                </div>
                {selectedParcel.provenance && (
                  <div className="pt-2 border-t border-[#E4DFD5] font-mono text-[10px] text-[#6B5748] space-y-0.5">
                    <div>
                      Source: {(selectedParcel.provenance.source_layers || []).join(" + ")}
                    </div>
                    <div>
                      CRS: {selectedParcel.provenance.crs} ({selectedParcel.provenance.metric_crs})
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* AI Council Summary Link */}
            {selectedCouncil && (
              <div className="p-3 rounded-xl bg-[#F4F1EA] border border-[#E4DFD5] space-y-1.5 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-[10px] uppercase text-[#6B5748]">
                    6-Agent Council Decision
                  </span>
                  {onNavigateTab && (
                    <button
                      onClick={() => onNavigateTab("council")}
                      className="text-[11px] font-mono text-[#8A735F] hover:underline flex items-center gap-1"
                    >
                      <span>Deliberation</span>
                      <ExternalLink className="w-3 h-3" />
                    </button>
                  )}
                </div>
                <div className="font-mono font-bold text-[#171615]">
                  {selectedCouncil.decision}
                </div>
                <div className="text-[11px] text-[#5C554E] leading-relaxed">
                  {selectedCouncil.recommended_action}
                </div>
              </div>
            )}

            {/* AI-Generated Candidate Disclaimer Box */}
            <div className="p-3.5 rounded-xl bg-[#FAF8F3] border border-[#D2C9BC] space-y-1.5 text-xs">
              <div className="flex items-center gap-2 text-[#6B5748] font-mono text-[10px] uppercase font-bold tracking-wider">
                <ShieldAlert className="w-3.5 h-3.5 text-[#9E6B20]" />
                <span>Statutory Survey Disclaimer</span>
              </div>
              <p className="text-[10px] text-[#5C554E] leading-relaxed font-mono">
                {selectedParcel.provenance?.disclaimer ||
                  "AI-GENERATED PRELIMINARY CANDIDATE GEOMETRY. Not an authoritative cadastral survey, title deed, or legal revenue map. Ground verification mandatory."}
              </p>
            </div>
          </div>
        )}
      </aside>
    </div>
  );
}
