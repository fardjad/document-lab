import { createRoot } from "react-dom/client";
import { useEffect, useRef, useState } from "react";
import type { MouseEvent as ReactMouseEvent, PointerEvent as ReactPointerEvent } from "react";
import { createTheme, ThemeProvider } from "@mui/material/styles";
import { SimpleTreeView } from "@mui/x-tree-view/SimpleTreeView";
import { TreeItem } from "@mui/x-tree-view/TreeItem";
import "./style.css";

type Rectangle = { x: number; y: number; width: number; height: number };
type Trim = { top: number; right: number; bottom: number; left: number };
type Region = { id: number; name: string; rectangle: Rectangle; rotation: number; straighten: number; trim: Trim };
const emptyTrim = (): Trim => ({ top: 0, right: 0, bottom: 0, left: 0 });
const trimValue = (region: Region) => region.trim ?? emptyTrim();
type Project = { id: string; name: string; imageUrl: string; regions: Region[]; regionsLoading?: boolean; regionsError?: string };
type EditorMode = { kind: "create" } | { kind: "edit"; region: Region };

const API = "http://localhost:8000/api";

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  if (!response.ok) throw new Error(`Request failed (${response.status})`);
  return response.status === 204 ? (undefined as T) : response.json();
}

function normalizeProject(id: string): Project {
  return { id, name: id, imageUrl: `${API}/projects/${encodeURIComponent(id)}/image`, regions: [] };
}

function rotatedBounds(rectangle: Rectangle, rotation: number) {
  const radians = rotation * Math.PI / 180;
  return { width: Math.ceil(Math.abs(rectangle.width * Math.cos(radians)) + Math.abs(rectangle.height * Math.sin(radians))), height: Math.ceil(Math.abs(rectangle.width * Math.sin(radians)) + Math.abs(rectangle.height * Math.cos(radians))) };
}

function parseStraighten(value: string) {
  if (/^[+-]?(?:\d+(?:\.\d)?|\.\d)$/.test(value.trim()) === false) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) && Math.abs(parsed) <= 45 ? Math.round(parsed * 10) / 10 : null;
}

const formatStraighten = (value: number) => `${value >= 0 ? "+" : ""}${value.toFixed(1)}`;
const parsePixels = (value: string) => /^\d+$/.test(value) ? Number(value) : null;

type ViewerControls = { fit: () => void; fitWidth: () => void; actualSize: () => void; zoomOut: () => void; zoomIn: () => void };

function Viewer({ project, region, editor, saving, straightenDraft, trimDraft, rootSelection, onTrimValidity, onConfirm, onCancel, onControlsReady }: { project?: Project; region?: Region; editor: EditorMode | null; saving: boolean; straightenDraft: number | null; trimDraft: Trim | null; rootSelection: number; onTrimValidity: (valid: boolean) => void; onConfirm: (rectangle: Rectangle) => void; onCancel: () => void; onControlsReady: (controls: ViewerControls | null) => void }) {
  const zoom = useRef(1);
  const offset = useRef({ x: 0, y: 0 });
  const viewport = useRef<HTMLDivElement>(null);
  const windowRef = useRef<HTMLDivElement>(null);
  const surfaceRef = useRef<HTMLDivElement>(null);
  const draftElement = useRef<HTMLDivElement>(null);
  const image = useRef<HTMLImageElement>(null);
  const dragging = useRef(false);
  const drawing = useRef(false);
  const movingDraft = useRef(false);
  const moveBase = useRef<Rectangle | null>(null);
  const moveStart = useRef({ x: 0, y: 0 });
  const spaceHeld = useRef(false);
  const resizing = useRef<"top" | "right" | "bottom" | "left" | null>(null);
  const resizeBase = useRef<Rectangle | null>(null);
  const start = useRef({ x: 0, y: 0 });
  const viewportSize = useRef<{ width: number; height: number } | null>(null);
  const [zoomReadout, setZoomReadout] = useState(100);
  const [draft, setDraft] = useState<Rectangle | null>(null);

  const imageRectangle = (rectangle: Rectangle): Rectangle | undefined => {
    const source = image.current;
    if (!source?.naturalWidth || !source.naturalHeight) return undefined;
    return { x: rectangle.x * source.naturalWidth, y: rectangle.y * source.naturalHeight, width: rectangle.width * source.naturalWidth, height: rectangle.height * source.naturalHeight };
  };
  const normalizedRectangle = (rectangle: Rectangle): Rectangle | undefined => {
    const source = image.current;
    if (!source?.naturalWidth || !source.naturalHeight) return undefined;
    return { x: rectangle.x / source.naturalWidth, y: rectangle.y / source.naturalHeight, width: rectangle.width / source.naturalWidth, height: rectangle.height / source.naturalHeight };
  };
  const displayRect = editor ? undefined : region ? imageRectangle(region.rectangle) : undefined;
  const rotation = displayRect && region && !editor ? ((region.rotation + (straightenDraft ?? region.straighten)) % 360 + 360) % 360 : 0;
  const activeTrim = displayRect && region && !editor ? (trimDraft ?? trimValue(region)) : emptyTrim();
  const updateDraftOverlay = () => {
    if (!draftElement.current || !draft) return;
    draftElement.current.style.left = `${offset.current.x + draft.x * zoom.current}px`;
    draftElement.current.style.top = `${offset.current.y + draft.y * zoom.current}px`;
    draftElement.current.style.width = `${draft.width * zoom.current}px`;
    draftElement.current.style.height = `${draft.height * zoom.current}px`;
  };
  const geometry = () => {
    const imageElement = image.current;
    if (!imageElement) return undefined;
    const source = displayRect ?? { x: 0, y: 0, width: imageElement.naturalWidth, height: imageElement.naturalHeight };
    const rotated = displayRect ? rotatedBounds(source, rotation) : source;
    return { source, rotated, view: displayRect ? { x: 0, y: 0, width: rotated.width - activeTrim.left - activeTrim.right, height: rotated.height - activeTrim.top - activeTrim.bottom } : source };
  };
  const update = () => {
    const imageElement = image.current;
    const windowElement = windowRef.current;
    const viewGeometry = geometry();
    if (!imageElement || !windowElement || !viewGeometry?.view.width || !viewGeometry.view.height) return;
    const rect = viewGeometry.view;
    const sourceRect = viewGeometry.source;
    windowElement.style.width = `${rect.width}px`;
    windowElement.style.height = `${rect.height}px`;
    if (surfaceRef.current) {
      surfaceRef.current.style.width = `${sourceRect.width}px`;
      surfaceRef.current.style.height = `${sourceRect.height}px`;
      surfaceRef.current.style.left = `${(viewGeometry.rotated.width - sourceRect.width) / 2 - activeTrim.left}px`;
      surfaceRef.current.style.top = `${(viewGeometry.rotated.height - sourceRect.height) / 2 - activeTrim.top}px`;
      surfaceRef.current.style.transform = rotation ? `rotate(${rotation}deg)` : "none";
    }
    imageElement.style.width = `${imageElement.naturalWidth}px`;
    imageElement.style.height = `${imageElement.naturalHeight}px`;
    imageElement.style.left = `${-(displayRect?.x ?? 0)}px`;
    imageElement.style.top = `${-(displayRect?.y ?? 0)}px`;
    windowElement.style.transform = `translate(${offset.current.x}px, ${offset.current.y}px) scale(${zoom.current})`;
    updateDraftOverlay();
    setZoomReadout(Math.round(zoom.current * 100));
  };
  const fit = () => {
    const viewportElement = viewport.current;
    const rect = geometry()?.view;
    if (!viewportElement || !rect?.width || !rect.height) return;
    const scale = Math.min((viewportElement.clientWidth - 64) / rect.width, (viewportElement.clientHeight - 64) / rect.height);
    zoom.current = Math.max(0.15, Math.min(1, scale));
    offset.current = { x: (viewportElement.clientWidth - rect.width * zoom.current) / 2, y: (viewportElement.clientHeight - rect.height * zoom.current) / 2 };
    update();
  };
  const fitRef = useRef(fit);
  fitRef.current = fit;
  const fitWidth = () => {
    const viewportElement = viewport.current;
    const rect = geometry()?.view;
    if (!viewportElement || !rect?.width || !rect.height) return;
    zoom.current = Math.max(0.15, Math.min(6, (viewportElement.clientWidth - 64) / rect.width));
    offset.current.x = (viewportElement.clientWidth - rect.width * zoom.current) / 2;
    update();
  };
  const actualSize = () => {
    const viewportElement = viewport.current;
    const rect = geometry()?.view;
    if (!viewportElement || !rect?.width || !rect.height) return;
    zoom.current = 1;
    offset.current = { x: (viewportElement.clientWidth - rect.width) / 2, y: (viewportElement.clientHeight - rect.height) / 2 };
    update();
  };
  const changeZoom = (factor: number, point?: { x: number; y: number }) => {
    const viewportElement = viewport.current;
    if (!viewportElement) return;
    const next = Math.min(6, Math.max(0.15, zoom.current * factor));
    const px = point?.x ?? viewportElement.clientWidth / 2, py = point?.y ?? viewportElement.clientHeight / 2;
    offset.current = { x: px - (px - offset.current.x) * next / zoom.current, y: py - (py - offset.current.y) * next / zoom.current };
    zoom.current = next;
    update();
  };
  const handleImageLoad = () => { if (region && !editor) update(); else fit(); };
  useEffect(() => {
    onControlsReady({ fit, fitWidth, actualSize, zoomOut: () => changeZoom(0.89), zoomIn: () => changeZoom(1.12) });
    return () => onControlsReady(null);
  }, [project?.id, region?.id, region?.rotation, region?.straighten, region?.trim, straightenDraft, trimDraft, editor?.kind]);
  useEffect(() => {
    const viewportElement = viewport.current, imageElement = image.current;
    if (!viewportElement || !imageElement) return;
    viewportSize.current = null;
    const observer = new ResizeObserver(([entry]) => {
      const next = { width: entry.contentRect.width, height: entry.contentRect.height };
      const previous = viewportSize.current;
      viewportSize.current = next;
      if (previous && (previous.width !== next.width || previous.height !== next.height)) fitRef.current();
    });
    observer.observe(viewportElement);
    return () => observer.disconnect();
  }, [project?.id]);
  useEffect(() => {
    setDraft(editor?.kind === "edit" ? imageRectangle(editor.region.rectangle) ?? null : null);
    update();
  }, [editor?.kind, editor?.kind === "edit" ? editor.region.id : null]);
  useEffect(() => {
    zoom.current = 1;
    offset.current = { x: 0, y: 0 };
    setZoomReadout(100);
    if (image.current?.complete && image.current.naturalWidth) fit();
  }, [project?.id, rootSelection]);
  useEffect(() => {
    zoom.current = 1;
    offset.current = { x: 0, y: 0 };
    setZoomReadout(100);
    fit();
  }, [region?.id, region?.rotation]);
  useEffect(() => { if (straightenDraft !== null) update(); }, [straightenDraft]);
  useEffect(() => { const view = geometry()?.view; onTrimValidity(Boolean(view && view.width >= 4 && view.height >= 4)); update(); }, [trimDraft, region?.id, region?.trim, rotation]);
  useEffect(() => {
    const keyDown = (event: KeyboardEvent) => { if (event.code === "Space") spaceHeld.current = true; };
    const keyUp = (event: KeyboardEvent) => { if (event.code === "Space") spaceHeld.current = false; };
    window.addEventListener("keydown", keyDown);
    window.addEventListener("keyup", keyUp);
    return () => { window.removeEventListener("keydown", keyDown); window.removeEventListener("keyup", keyUp); };
  }, []);
  const imagePoint = (event: PointerEvent) => {
    const box = viewport.current!.getBoundingClientRect();
    return { x: (event.clientX - box.left - offset.current.x) / zoom.current, y: (event.clientY - box.top - offset.current.y) / zoom.current };
  };
  const clampRect = (startPoint: { x: number; y: number }, endPoint: { x: number; y: number }): Rectangle | null => {
    const imageElement = image.current;
    if (!imageElement?.naturalWidth || !imageElement.naturalHeight) return null;
    const clamp = (value: number, max: number) => Math.max(0, Math.min(max, value));
    const x1 = clamp(startPoint.x, imageElement.naturalWidth), y1 = clamp(startPoint.y, imageElement.naturalHeight);
    const x2 = clamp(endPoint.x, imageElement.naturalWidth), y2 = clamp(endPoint.y, imageElement.naturalHeight);
    return { x: Math.min(x1, x2), y: Math.min(y1, y2), width: Math.abs(x2 - x1), height: Math.abs(y2 - y1) };
  };
  const resizeRect = (base: Rectangle, side: "top" | "right" | "bottom" | "left", point: { x: number; y: number }): Rectangle | null => {
    const source = image.current;
    if (!source?.naturalWidth || !source.naturalHeight) return null;
    const minimum = 4;
    const right = base.x + base.width, bottom = base.y + base.height;
    if (side === "left") { const x = Math.max(0, Math.min(point.x, right - minimum)); return { ...base, x, width: right - x }; }
    if (side === "right") { const nextRight = Math.min(source.naturalWidth, Math.max(point.x, base.x + minimum)); return { ...base, width: nextRight - base.x }; }
    if (side === "top") { const y = Math.max(0, Math.min(point.y, bottom - minimum)); return { ...base, y, height: bottom - y }; }
    const nextBottom = Math.min(source.naturalHeight, Math.max(point.y, base.y + minimum));
    return { ...base, height: nextBottom - base.y };
  };
  const startResize = (event: ReactPointerEvent, side: "top" | "right" | "bottom" | "left") => {
    event.preventDefault();
    event.stopPropagation();
    if (event.button === 1) { startPan(event); return; }
    if (!draft) return;
    resizing.current = side;
    resizeBase.current = draft;
    viewport.current?.setPointerCapture(event.pointerId);
  };
  const panGesture = (event: { button: number }) => event.button === 1 || (event.button === 0 && spaceHeld.current);
  const startPan = (event: { clientX: number; clientY: number; pointerId: number }) => {
    dragging.current = true;
    start.current = { x: event.clientX - offset.current.x, y: event.clientY - offset.current.y };
    viewport.current?.setPointerCapture(event.pointerId);
  };
  const overlayPointerDown = (event: ReactPointerEvent) => {
    event.stopPropagation();
    if (event.button === 1) { event.preventDefault(); startPan(event); }
  };
  const startMove = (event: ReactPointerEvent) => {
    event.preventDefault();
    event.stopPropagation();
    if (panGesture(event)) { startPan(event); return; }
    if (!draft) return;
    movingDraft.current = true;
    moveBase.current = draft;
    moveStart.current = imagePoint(event);
    viewport.current?.setPointerCapture(event.pointerId);
  };
  const pointerDown = (event: PointerEvent) => {
    if (editor) {
      if (panGesture(event)) { event.preventDefault(); startPan(event); return; }
      const point = imagePoint(event);
      if (draft && point.x >= draft.x && point.x <= draft.x + draft.width && point.y >= draft.y && point.y <= draft.y + draft.height) {
        movingDraft.current = true;
        moveBase.current = draft;
        moveStart.current = point;
        viewport.current?.setPointerCapture(event.pointerId);
        return;
      }
      drawing.current = true; start.current = imagePoint(event); viewport.current?.setPointerCapture(event.pointerId); return;
    }
    if (event.button === 0 || event.button === 1) { if (event.button === 1) event.preventDefault(); startPan(event); }
  };
  const pointerMove = (event: PointerEvent) => {
    if (resizing.current && resizeBase.current) { setDraft(resizeRect(resizeBase.current, resizing.current, imagePoint(event))); return; }
    if (movingDraft.current && moveBase.current) {
      const source = image.current;
      if (source?.naturalWidth && source.naturalHeight) {
        const base = moveBase.current, point = imagePoint(event);
        const x = Math.max(0, Math.min(source.naturalWidth - base.width, base.x + point.x - moveStart.current.x));
        const y = Math.max(0, Math.min(source.naturalHeight - base.height, base.y + point.y - moveStart.current.y));
        setDraft({ ...base, x, y });
      }
      return;
    }
    if (drawing.current) { setDraft(clampRect(start.current, imagePoint(event))); return; }
    if (dragging.current) { offset.current = { x: event.clientX - start.current.x, y: event.clientY - start.current.y }; update(); }
  };
  const pointerUp = (event: PointerEvent) => { resizing.current = null; resizeBase.current = null; movingDraft.current = false; moveBase.current = null; drawing.current = false; dragging.current = false; viewport.current?.releasePointerCapture(event.pointerId); };
  const wheel = (event: WheelEvent) => { const box = viewport.current!.getBoundingClientRect(); changeZoom(event.deltaY < 0 ? 1.12 : 0.89, { x: event.clientX - box.left, y: event.clientY - box.top }); };
  const overlayStyle = draft && { left: `${offset.current.x + draft.x * zoom.current}px`, top: `${offset.current.y + draft.y * zoom.current}px`, width: `${draft.width * zoom.current}px`, height: `${draft.height * zoom.current}px` };
  const stopViewerPointer = (event: ReactPointerEvent | ReactMouseEvent) => event.stopPropagation();
  const confirmDraft = () => { if (!draft || draft.width < 4 || draft.height < 4) return; const rectangle = normalizedRectangle(draft); if (rectangle) onConfirm(rectangle); };
  return <section className={`viewer${editor ? " drawing" : ""}`} ref={viewport} onWheel={wheel} onPointerDown={pointerDown} onPointerMove={pointerMove} onPointerUp={pointerUp} onAuxClick={(event) => { if (event.button === 1) event.preventDefault(); }}>
    {project?.imageUrl ? <div className={`image-window${displayRect ? " crop-window" : ""}`} ref={windowRef}><div className="image-surface" ref={surfaceRef}><img key={project.id} ref={image} className="document" src={project.imageUrl} alt={project.name} draggable={false} onLoad={handleImageLoad} /></div></div> : <div className="empty-view">Select project to begin</div>}
    {editor && draft && <div ref={draftElement} className="slice-draft" style={overlayStyle} aria-label="Region selection" onPointerDown={startMove}><button className="draft-move-surface" onPointerDown={startMove} onClick={stopViewerPointer} aria-label="Move region rectangle" /><button className="slice-handle handle-top" onPointerDown={(event) => startResize(event, "top")} onClick={stopViewerPointer} aria-label="Resize region top edge" /><button className="slice-handle handle-right" onPointerDown={(event) => startResize(event, "right")} onClick={stopViewerPointer} aria-label="Resize region right edge" /><button className="slice-handle handle-bottom" onPointerDown={(event) => startResize(event, "bottom")} onClick={stopViewerPointer} aria-label="Resize region bottom edge" /><button className="slice-handle handle-left" onPointerDown={(event) => startResize(event, "left")} onClick={stopViewerPointer} aria-label="Resize region left edge" /><span>{Math.round(draft.width)} × {Math.round(draft.height)}</span><div className="slice-actions" onPointerDown={overlayPointerDown} onClick={stopViewerPointer}><button onClick={confirmDraft} disabled={saving || draft.width < 4 || draft.height < 4} aria-label="Confirm region">✓</button><button onClick={onCancel} disabled={saving} aria-label="Cancel region">×</button></div></div>}
    {straightenDraft !== null && region && !editor && <div className="straighten-cross" aria-hidden="true"><i /><b /></div>}
    {editor && <div className="draw-hint">{draft ? "Drag box to move · Space + drag or middle-drag to pan" : "Drag over image to draw region · Space + drag or middle-drag to pan"}</div>}
    <div className="zoom-readout">{zoomReadout}%</div>
  </section>;
}

const treeTheme = createTheme({
  palette: { mode: "dark", primary: { main: "#d3f36b" }, background: { paper: "#18191b" } },
  typography: { fontFamily: "'Space Grotesk', sans-serif" },
});

const treeProjectId = (id: string) => `project:${id}`;
const treeRegionId = (projectId: string, id: number) => `region:${projectId}:${id}`;

function ProjectTree({ projects, selectedProjectId, selectedRegionId, expandedItems, straightenActive, onProject, onExpanded, onRegion, onEdit, onDelete, onRename }: { projects: Project[]; selectedProjectId: string; selectedRegionId: number | null; expandedItems: string[]; straightenActive: boolean; onProject: (id: string) => void; onExpanded: (items: string[]) => void; onRegion: (projectId: string, id: number) => void; onEdit: (region: Region) => void; onDelete: (region: Region) => void; onRename: (region: Region, name: string) => void }) {
  const [renaming, setRenaming] = useState<number | null>(null);
  const [name, setName] = useState("");
  const stopSelection = (event: Event) => event.stopPropagation();
  return <ThemeProvider theme={treeTheme}><SimpleTreeView className="project-tree" aria-label="Projects" expandedItems={expandedItems} selectedItems={selectedRegionId === null ? (selectedProjectId ? treeProjectId(selectedProjectId) : null) : treeRegionId(selectedProjectId, selectedRegionId)} expansionTrigger="iconContainer" onExpandedItemsChange={(_, items) => onExpanded(items)} onSelectedItemsChange={(_, item) => { if (!item) return; if (item.startsWith("project:")) onProject(item.slice(8)); else { const [, projectId, id] = item.split(":"); onRegion(projectId, Number(id)); } }}>
    {projects.map((project) => <TreeItem key={project.id} itemId={treeProjectId(project.id)} label={<span className="tree-project-label"><span className="project-dot" />{project.name}</span>}>
      {(project.regionsLoading || project.regionsError || project.regions.length === 0) && <TreeItem itemId={`${treeProjectId(project.id)}:status`} disabled label={project.regionsLoading ? "Loading…" : project.regionsError ? project.regionsError : "No regions"} />}
      {project.regions.map((region) => <TreeItem key={region.id} itemId={treeRegionId(project.id, region.id)} label={<span className="tree-region-label"><span className="slice-marker" />{renaming === region.id ? <input autoFocus value={name} onInput={(event) => setName((event.target as HTMLInputElement).value)} onKeyDown={(event) => { event.stopPropagation(); if (event.key === "Enter") { onRename(region, name); setRenaming(null); } if (event.key === "Escape") setRenaming(null); }} onBlur={() => setRenaming(null)} onClick={stopSelection} onMouseDown={stopSelection} aria-label="Region name" /> : <span>{region.name}</span>}{!straightenActive && <span className="region-menu" onClick={stopSelection} onMouseDown={stopSelection}><button onClick={() => { setName(region.name); setRenaming(region.id); }} aria-label={`Rename ${region.name}`}>↗</button><button onClick={() => onEdit(region)} aria-label={`Edit ${region.name}`}>□</button><button onClick={() => onDelete(region)} aria-label={`Delete ${region.name}`}>×</button></span>}</span>} />)}
    </TreeItem>)}
  </SimpleTreeView></ThemeProvider>;
}

function App() {
  const [projects, setProjects] = useState<Project[]>([]), [selectedProjectId, setSelectedProjectId] = useState(""), [selectedRegionId, setSelectedRegionId] = useState<number | null>(null), [expandedItems, setExpandedItems] = useState<string[]>([]), [loading, setLoading] = useState(true), [error, setError] = useState(""), [editor, setEditor] = useState<EditorMode | null>(null), [straightenDraft, setStraightenDraft] = useState<number | null>(null), [straightenText, setStraightenText] = useState(""), [trimDraft, setTrimDraft] = useState<Trim | null>(null), [trimText, setTrimText] = useState<Trim>({ top: 0, right: 0, bottom: 0, left: 0 }), [trimValid, setTrimValid] = useState(true), [saving, setSaving] = useState(false), [rootSelection, setRootSelection] = useState(0), [viewerControls, setViewerControls] = useState<ViewerControls | null>(null);
  const project = projects.find((item) => item.id === selectedProjectId);
  const region = project?.regions.find((item) => item.id === selectedRegionId);
  useEffect(() => { request<string[]>(`${API}/projects`).then((ids) => { const items = ids.map(normalizeProject); setProjects(items); setSelectedProjectId(items[0]?.id ?? ""); if (items[0]) setExpandedItems([treeProjectId(items[0].id)]); }).catch((reason) => setError(reason.message)).finally(() => setLoading(false)); }, []);
  useEffect(() => { if (!selectedProjectId) return; setSelectedRegionId(null); setEditor(null); setStraightenDraft(null); setStraightenText(""); setTrimDraft(null); setProjects((items) => items.map((item) => item.id === selectedProjectId ? { ...item, regionsLoading: true, regionsError: "" } : item)); request<Region[]>(`${API}/projects/${encodeURIComponent(selectedProjectId)}/regions`).then((regions) => setProjects((items) => items.map((item) => item.id === selectedProjectId ? { ...item, regions, regionsLoading: false } : item))).catch((reason) => setProjects((items) => items.map((item) => item.id === selectedProjectId ? { ...item, regionsLoading: false, regionsError: reason.message } : item))); }, [selectedProjectId]);
  const selectProject = (id: string) => { setSelectedProjectId(id); setSelectedRegionId(null); setEditor(null); setStraightenDraft(null); setStraightenText(""); setTrimDraft(null); setRootSelection((value) => value + 1); };
  const updateRegion = async (regionId: number, body: { name: string; rectangle: Rectangle; rotation: number; straighten: number; trim: Trim }) => { const updated = await request<Region>(`${API}/projects/${encodeURIComponent(selectedProjectId)}/regions/${regionId}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }); setProjects((items) => items.map((item) => item.id === selectedProjectId ? { ...item, regions: item.regions.map((itemRegion) => itemRegion.id === regionId ? updated : itemRegion) } : item)); };
  const confirmRegion = async (rectangle: Rectangle) => { if (!project) return; setSaving(true); try { if (editor?.kind === "edit") { await updateRegion(editor.region.id, { name: editor.region.name, rectangle, rotation: editor.region.rotation, straighten: editor.region.straighten, trim: trimValue(editor.region) }); } else { const created = await request<Region>(`${API}/projects/${encodeURIComponent(project.id)}/regions`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ rectangle }) }); setProjects((items) => items.map((item) => item.id === project.id ? { ...item, regions: [...item.regions, created] } : item)); setSelectedRegionId(created.id); } setEditor(null); } catch (reason) { setError(reason.message); } finally { setSaving(false); } };
  const renameRegion = async (item: Region, name: string) => { const nextName = name.trim(); if (!nextName || nextName === item.name) return; try { await updateRegion(item.id, { name: nextName, rectangle: item.rectangle, rotation: item.rotation, straighten: item.straighten, trim: trimValue(item) }); } catch (reason) { setError(reason.message); } };
  const rotateRegion = async (item: Region, delta: number) => { setSaving(true); try { await updateRegion(item.id, { name: item.name, rectangle: item.rectangle, rotation: (item.rotation + delta + 360) % 360, straighten: item.straighten, trim: trimValue(item) }); } catch (reason) { setError(reason.message); } finally { setSaving(false); } };
  const commitStraightenText = () => { const parsed = parseStraighten(straightenText); if (parsed === null) { setStraightenText(straightenDraft === null ? "" : formatStraighten(straightenDraft)); return; } setStraightenDraft(parsed); setStraightenText(formatStraighten(parsed)); };
  const adjustStraighten = (delta: number) => { const next = Math.max(-45, Math.min(45, Math.round(((straightenDraft ?? 0) + delta) * 10) / 10)); setStraightenDraft(next); setStraightenText(formatStraighten(next)); };
  const confirmStraighten = async () => { const parsed = parseStraighten(straightenText); if (!region || straightenDraft === null || parsed === null) return; setSaving(true); try { await updateRegion(region.id, { name: region.name, rectangle: region.rectangle, rotation: region.rotation, straighten: parsed, trim: trimValue(region) }); setStraightenDraft(null); setStraightenText(""); setTrimDraft(null); } catch (reason) { setError(reason.message); } finally { setSaving(false); } };
  const beginTrim = () => { if (!region) return; setTrimDraft({ ...trimValue(region) }); setTrimText({ ...trimValue(region) }); };
  const updateTrimSide = (side: keyof Trim, value: number) => { const next = { ...(trimDraft ?? trimText), [side]: Math.max(0, value) }; setTrimDraft(next); setTrimText(next); };
  const commitTrimSide = (side: keyof Trim) => { const parsed = parsePixels(String(trimText[side])); if (parsed === null) setTrimText((value) => ({ ...value, [side]: trimDraft?.[side] ?? 0 })); else updateTrimSide(side, parsed); };
  const confirmTrim = async () => { if (!region || !trimDraft || !trimValid || Object.values(trimText).some((value) => parsePixels(String(value)) === null)) return; setSaving(true); try { await updateRegion(region.id, { name: region.name, rectangle: region.rectangle, rotation: region.rotation, straighten: region.straighten, trim: trimDraft }); setTrimDraft(null); } catch (reason) { setError(reason.message); } finally { setSaving(false); } };
  const downloadRegion = () => { if (!region || editor || straightenDraft !== null || trimDraft !== null || saving) return; const link = document.createElement("a"); link.href = `${API}/projects/${encodeURIComponent(project!.id)}/regions/${region.id}/download`; link.click(); };
  const deleteRegion = async (item: Region) => { if (!confirm(`Delete “${item.name}”?`)) return; try { await request<void>(`${API}/projects/${encodeURIComponent(selectedProjectId)}/regions/${item.id}`, { method: "DELETE" }); setProjects((items) => items.map((entry) => entry.id === selectedProjectId ? { ...entry, regions: entry.regions.filter((regionItem) => regionItem.id !== item.id) } : entry)); if (selectedRegionId === item.id) setSelectedRegionId(null); } catch (reason) { setError(reason.message); } };
  return <main className="app-shell"><aside className="toolbar"><div className="brand"><span className="brand-mark">◩</span><span>Cropper</span></div><div className="toolbar-section"><span className="eyebrow">Projects</span>{loading && <p className="muted">Loading…</p>}{error && <p className="error">{error}</p>}{!loading && !error && projects.length === 0 && <p className="muted">No projects found.</p>}<ProjectTree projects={projects} selectedProjectId={selectedProjectId} selectedRegionId={selectedRegionId} expandedItems={expandedItems} straightenActive={straightenDraft !== null || trimDraft !== null} onProject={selectProject} onExpanded={setExpandedItems} onRegion={(projectId, id) => { setEditor(null); setStraightenDraft(null); setStraightenText(""); setTrimDraft(null); setSelectedProjectId(projectId); setSelectedRegionId(id); }} onEdit={(item) => { setStraightenDraft(null); setStraightenText(""); setTrimDraft(null); setSelectedRegionId(item.id); setEditor({ kind: "edit", region: item }); }} onDelete={deleteRegion} onRename={renameRegion} /></div><div className="toolbar-foot">Drag edge to resize<br /><span>Wheel zoom · drag pan</span></div></aside><div className="workspace"><header className={straightenDraft !== null ? "straighten-active" : trimDraft !== null ? "trim-active" : ""}><div><span className="eyebrow">Workspace</span><h1>{project?.name ?? "Document viewer"}</h1></div><div className="header-tools"><button className="region-tool" onClick={() => { setStraightenDraft(null); setStraightenText(""); setTrimDraft(null); setEditor({ kind: "create" }); }} disabled={!project} aria-pressed={Boolean(editor)}>＋ Region</button>{region && !editor && straightenDraft === null && <div className="rotation-tools"><button onClick={() => rotateRegion(region, -90)} disabled={saving} aria-label="Rotate region left 90 degrees" title="Rotate region left 90 degrees">↶ 90°</button><button onClick={() => rotateRegion(region, 90)} disabled={saving} aria-label="Rotate region right 90 degrees" title="Rotate region right 90 degrees">↷ 90°</button></div>}{region && !editor && straightenDraft === null && <button className="straighten-tool" onClick={() => { setStraightenDraft(region.straighten); setStraightenText(formatStraighten(region.straighten)); }} disabled={saving}>Straighten</button>}{region && !editor && straightenDraft === null && trimDraft === null && <button className="trim-tool" onClick={beginTrim} disabled={saving}>Trim</button>}{region && !editor && straightenDraft !== null && <div className="straighten-tools"><button className="straighten-step" onClick={() => adjustStraighten(-0.1)} disabled={saving} aria-label="Decrease straighten angle by 0.1 degrees">−</button><label className="angle-control"><input className="straighten-number" value={straightenText} onInput={(event) => { const value = (event.target as HTMLInputElement).value; setStraightenText(value); const parsed = parseStraighten(value); if (parsed !== null) setStraightenDraft(parsed); }} onBlur={commitStraightenText} onKeyDown={(event) => { if (event.key === "Enter") commitStraightenText(); }} aria-label="Straighten angle" aria-valuetext={`${straightenText || "invalid"} degrees`} /><span>°</span></label><button className="straighten-step" onClick={() => adjustStraighten(0.1)} disabled={saving} aria-label="Increase straighten angle by 0.1 degrees">+</button><input className="straighten-slider" type="range" min="-45" max="45" step="0.1" value={straightenDraft ?? 0} onChange={(event) => { const value = Number(event.target.value); setStraightenDraft(value); setStraightenText(formatStraighten(value)); }} aria-label="Straighten angle slider" /><button className="straighten-action" onClick={() => { setStraightenDraft(null); setStraightenText(""); setTrimDraft(null); }} disabled={saving}>Cancel</button><button className="straighten-action confirm" onClick={confirmStraighten} disabled={saving || parseStraighten(straightenText) === null}>Confirm</button></div>}{region && !editor && straightenDraft === null && trimDraft !== null && <div className="trim-tools"><label className="trim-control"><span>Top</span><button className="trim-step" onClick={() => updateTrimSide("top", trimText.top - 1)} disabled={saving}>−</button><input value={trimText.top} inputMode="numeric" aria-label="Trim top pixels" onInput={(event) => setTrimText((value) => ({ ...value, top: (event.target as HTMLInputElement).value }))} onBlur={() => commitTrimSide("top")} onKeyDown={(event) => { if (event.key === "Enter") commitTrimSide("top"); }} /><button className="trim-step" onClick={() => updateTrimSide("top", trimText.top + 1)} disabled={saving}>+</button></label><label className="trim-control"><span>Right</span><button className="trim-step" onClick={() => updateTrimSide("right", trimText.right - 1)} disabled={saving}>−</button><input value={trimText.right} inputMode="numeric" aria-label="Trim right pixels" onInput={(event) => setTrimText((value) => ({ ...value, right: (event.target as HTMLInputElement).value }))} onBlur={() => commitTrimSide("right")} onKeyDown={(event) => { if (event.key === "Enter") commitTrimSide("right"); }} /><button className="trim-step" onClick={() => updateTrimSide("right", trimText.right + 1)} disabled={saving}>+</button></label><label className="trim-control"><span>Bottom</span><button className="trim-step" onClick={() => updateTrimSide("bottom", trimText.bottom - 1)} disabled={saving}>−</button><input value={trimText.bottom} inputMode="numeric" aria-label="Trim bottom pixels" onInput={(event) => setTrimText((value) => ({ ...value, bottom: (event.target as HTMLInputElement).value }))} onBlur={() => commitTrimSide("bottom")} onKeyDown={(event) => { if (event.key === "Enter") commitTrimSide("bottom"); }} /><button className="trim-step" onClick={() => updateTrimSide("bottom", trimText.bottom + 1)} disabled={saving}>+</button></label><label className="trim-control"><span>Left</span><button className="trim-step" onClick={() => updateTrimSide("left", trimText.left - 1)} disabled={saving}>−</button><input value={trimText.left} inputMode="numeric" aria-label="Trim left pixels" onInput={(event) => setTrimText((value) => ({ ...value, left: (event.target as HTMLInputElement).value }))} onBlur={() => commitTrimSide("left")} onKeyDown={(event) => { if (event.key === "Enter") commitTrimSide("left"); }} /><button className="trim-step" onClick={() => updateTrimSide("left", trimText.left + 1)} disabled={saving}>+</button></label><button className="trim-action" onClick={() => { setTrimDraft(null); }} disabled={saving}>Cancel</button><button className="trim-action confirm" onClick={confirmTrim} disabled={saving || !trimValid || Object.values(trimText).some((value) => parsePixels(String(value)) === null)}>Confirm</button></div>}{region && !editor && straightenDraft === null && trimDraft === null && <button className="download-tool" onClick={downloadRegion} disabled={saving} aria-label="Download selected region as PNG" title="Download selected region as PNG">Download PNG</button>}<div className="view-presets"><button onClick={() => viewerControls?.fit()} disabled={!viewerControls}>Fit</button><button onClick={() => viewerControls?.fitWidth()} disabled={!viewerControls}>Fit Width</button><button onClick={() => viewerControls?.actualSize()} disabled={!viewerControls}>Actual Size</button></div><div className="zoom-tools"><button onClick={() => viewerControls?.zoomOut()} disabled={!viewerControls} aria-label="Zoom out">−</button><button onClick={() => viewerControls?.zoomIn()} disabled={!viewerControls} aria-label="Zoom in">+</button></div><span className="status"><i />{project ? "Ready" : "Waiting"}</span></div></header><Viewer project={project} region={region} editor={editor} saving={saving} straightenDraft={straightenDraft} trimDraft={trimDraft} rootSelection={rootSelection} onConfirm={confirmRegion} onCancel={() => setEditor(null)} onTrimValidity={setTrimValid} onControlsReady={setViewerControls} /></div></main>;
}

createRoot(document.getElementById("app")!).render(<App />);
