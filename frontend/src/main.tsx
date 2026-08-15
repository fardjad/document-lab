import { createRoot } from "react-dom/client";
import { useEffect, useRef, useState } from "react";
import type { MouseEvent as ReactMouseEvent, PointerEvent as ReactPointerEvent, ReactNode } from "react";
import { createTheme, ThemeProvider } from "@mui/material/styles";
import { SimpleTreeView } from "@mui/x-tree-view/SimpleTreeView";
import { TreeItem } from "@mui/x-tree-view/TreeItem";
import AddPhotoAlternateOutlinedIcon from "@mui/icons-material/AddPhotoAlternateOutlined";
import AutoFixHighOutlinedIcon from "@mui/icons-material/AutoFixHighOutlined";
import CheckOutlinedIcon from "@mui/icons-material/CheckOutlined";
import CloseOutlinedIcon from "@mui/icons-material/CloseOutlined";
import DeleteOutlineOutlinedIcon from "@mui/icons-material/DeleteOutlineOutlined";
import DownloadOutlinedIcon from "@mui/icons-material/DownloadOutlined";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";
import FitScreenOutlinedIcon from "@mui/icons-material/FitScreenOutlined";
import HeightOutlinedIcon from "@mui/icons-material/HeightOutlined";
import HideImageOutlinedIcon from "@mui/icons-material/HideImageOutlined";
import RemoveOutlinedIcon from "@mui/icons-material/RemoveOutlined";
import RestartAltOutlinedIcon from "@mui/icons-material/RestartAltOutlined";
import Rotate90DegreesCcwOutlinedIcon from "@mui/icons-material/Rotate90DegreesCcwOutlined";
import Rotate90DegreesCwOutlinedIcon from "@mui/icons-material/Rotate90DegreesCwOutlined";
import StraightenOutlinedIcon from "@mui/icons-material/StraightenOutlined";
import TuneOutlinedIcon from "@mui/icons-material/TuneOutlined";
import ZoomInOutlinedIcon from "@mui/icons-material/ZoomInOutlined";
import ZoomOutOutlinedIcon from "@mui/icons-material/ZoomOutOutlined";
import MenuOutlinedIcon from "@mui/icons-material/MenuOutlined";
import MenuOpenOutlinedIcon from "@mui/icons-material/MenuOpenOutlined";
import SearchOutlinedIcon from "@mui/icons-material/SearchOutlined";
import { IconButton, Tooltip } from "@mui/material";
import "./style.css";

type Rectangle = { x: number; y: number; width: number; height: number };
type Trim = { top: number; right: number; bottom: number; left: number };
type BackgroundRemoval = { model: string; alpha_matting: boolean; alpha_matting_foreground_threshold: number; alpha_matting_background_threshold: number; alpha_matting_erode_size: number; post_process_mask: boolean };
const BACKGROUND_REMOVAL_MODELS = ["birefnet-general", "isnet-general-use", "u2net", "u2netp", "silueta"];
const defaultBackgroundRemoval = (): BackgroundRemoval => ({ model: "birefnet-general", alpha_matting: false, alpha_matting_foreground_threshold: 240, alpha_matting_background_threshold: 10, alpha_matting_erode_size: 10, post_process_mask: false });
type Operation = { kind: string; options: Record<string, unknown> };
type Pipeline = Operation[];
type View = { id: number; name: string; pipeline: Pipeline };
const emptyTrim = (): Trim => ({ top: 0, right: 0, bottom: 0, left: 0 });
const findOp = (pipeline: Pipeline, kind: string): Operation | undefined => pipeline.find((op) => op.kind === kind);
const getRotateDegrees = (pipeline: Pipeline): number => (findOp(pipeline, "rotate")?.options.degrees as number) ?? 0;
const getStraightenAngle = (pipeline: Pipeline): number => (findOp(pipeline, "straighten")?.options.angle as number) ?? 0;
const getCrop = (pipeline: Pipeline): Rectangle | null => { const op = findOp(pipeline, "crop"); return op ? (op.options as Rectangle) : null; };
const getTrim = (pipeline: Pipeline): Trim => (findOp(pipeline, "trim")?.options as Trim) ?? { top: 0, right: 0, bottom: 0, left: 0 };
const getRemoveBackground = (pipeline: Pipeline): BackgroundRemoval | null => { const op = findOp(pipeline, "remove_background"); return op ? (op.options as BackgroundRemoval) : null; };
const asOperation = (kind: string, options: Record<string, unknown>): Operation => ({ kind, options });
const setOp = (pipeline: Pipeline, kind: string, options: Record<string, unknown>): Pipeline => { const next = pipeline.filter((op) => op.kind !== kind); const operation = asOperation(kind, options); if (kind === "crop") return [operation, ...next]; next.push(operation); return next; };
const removeOps = (pipeline: Pipeline, ...kinds: string[]): Pipeline => pipeline.filter((op) => !kinds.includes(op.kind));
type Project = { id: string; name: string; imageUrl: string; views: View[]; viewsLoading?: boolean; viewsError?: string };
type EditorMode = { kind: "create" } | { kind: "edit"; view: View };

const API = "/api";

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  if (!response.ok) throw new Error(`Request failed (${response.status})`);
  return response.status === 204 ? (undefined as T) : response.json();
}

function normalizeProject(id: string): Project {
  return { id, name: id, imageUrl: `${API}/projects/${encodeURIComponent(id)}/image`, views: [] };
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
type AutoState = { loading: boolean; message: string; error: string };

type ViewerControls = { fit: () => void; fitWidth: () => void; actualSize: () => void; zoomOut: () => void; zoomIn: () => void };

function Viewer({ project, view, editor, saving, straightenDraft, trimDraft, renderedUrl, previewUrl, rootSelection, onTrimValidity, onConfirm, onCancel, onControlsReady, children }: { project?: Project; view?: View; editor: EditorMode | null; saving: boolean; straightenDraft: number | null; trimDraft: Trim | null; renderedUrl?: string; previewUrl?: string; rootSelection: number; onTrimValidity: (valid: boolean) => void; onConfirm: (rectangle: Rectangle) => void; onCancel: () => void; onControlsReady: (controls: ViewerControls | null) => void; children?: ReactNode }) {
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
  const sourceUrl = previewUrl ?? renderedUrl ?? project?.imageUrl;
  const renderedView = Boolean(previewUrl ?? renderedUrl);
  const displayRect = editor || renderedView ? undefined : view ? imageRectangle(getCrop(view.pipeline) ?? { x: 0, y: 0, width: 1, height: 1 }) : undefined;
  const rotation = displayRect && view && !editor ? ((getRotateDegrees(view.pipeline) + (straightenDraft ?? getStraightenAngle(view.pipeline))) % 360 + 360) % 360 : 0;
  const activeTrim = displayRect && view && !editor ? (trimDraft ?? getTrim(view.pipeline)) : emptyTrim();
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
  const renderedMode = useRef(false);
  const handleImageLoad = () => { const nowRendered = Boolean(previewUrl ?? renderedUrl); if (view && !editor && !nowRendered) update(); else if (renderedMode.current && nowRendered) update(); else fit(); renderedMode.current = nowRendered; };
  useEffect(() => {
    onControlsReady({ fit, fitWidth, actualSize, zoomOut: () => changeZoom(0.89), zoomIn: () => changeZoom(1.12) });
    return () => onControlsReady(null);
  }, [project?.id, view?.id, view?.pipeline, straightenDraft, trimDraft, editor?.kind]);
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
    setDraft(editor?.kind === "edit" ? imageRectangle(getCrop(editor.view.pipeline) ?? { x: 0, y: 0, width: 1, height: 1 }) ?? null : null);
    update();
  }, [editor?.kind, editor?.kind === "edit" ? editor.view.id : null]);
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
  }, [view?.id, view?.pipeline, renderedUrl, Boolean(previewUrl)]);
  useEffect(() => { if (straightenDraft !== null) update(); }, [straightenDraft]);
  useEffect(() => { const view = geometry()?.view; onTrimValidity(Boolean(view && view.width >= 4 && view.height >= 4)); update(); }, [trimDraft, view?.id, view?.pipeline, rotation]);
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
    {sourceUrl ? <div className={`image-window${displayRect ? " crop-window" : ""}${renderedView ? " rendered-view" : ""}`} ref={windowRef}><div className="image-surface" ref={surfaceRef}><img key={previewUrl ?? renderedUrl ?? project!.id} ref={image} className="document" src={sourceUrl} alt={project?.name ?? "View"} draggable={false} onLoad={handleImageLoad} /></div></div> : <div className="empty-view">Select project to begin</div>}
    {editor && draft && <div ref={draftElement} className="slice-draft" style={overlayStyle} aria-label="View selection" onPointerDown={startMove}><button className="draft-move-surface" onPointerDown={startMove} onClick={stopViewerPointer} aria-label="Move view rectangle" /><button className="slice-handle handle-top" onPointerDown={(event) => startResize(event, "top")} onClick={stopViewerPointer} aria-label="Resize view top edge" /><button className="slice-handle handle-right" onPointerDown={(event) => startResize(event, "right")} onClick={stopViewerPointer} aria-label="Resize view right edge" /><button className="slice-handle handle-bottom" onPointerDown={(event) => startResize(event, "bottom")} onClick={stopViewerPointer} aria-label="Resize view bottom edge" /><button className="slice-handle handle-left" onPointerDown={(event) => startResize(event, "left")} onClick={stopViewerPointer} aria-label="Resize view left edge" /><span>{Math.round(draft.width)} × {Math.round(draft.height)}</span><div className="slice-actions" onPointerDown={overlayPointerDown} onClick={stopViewerPointer}><button onClick={confirmDraft} disabled={saving || draft.width < 4 || draft.height < 4} aria-label="Confirm view">✓</button><button onClick={onCancel} disabled={saving} aria-label="Cancel view">×</button></div></div>}
    {straightenDraft !== null && view && !editor && <div className="straighten-cross" aria-hidden="true"><i /><b /></div>}
    {children}
    <nav className="viewer-toolbar" aria-label="Viewer zoom controls" onPointerDown={stopViewerPointer}><button onClick={fit} aria-label="Fit" title="Fit"><FitScreenOutlinedIcon /></button><button onClick={fitWidth} aria-label="Fit Width" title="Fit Width"><HeightOutlinedIcon /></button><button onClick={actualSize} aria-label="Actual Size" title="Actual Size"><RestartAltOutlinedIcon /></button><span className="zoom-readout" aria-live="polite">{zoomReadout}%</span><button onClick={() => changeZoom(0.89)} aria-label="Zoom Out" title="Zoom Out"><ZoomOutOutlinedIcon /></button><button onClick={() => changeZoom(1.12)} aria-label="Zoom In" title="Zoom In"><ZoomInOutlinedIcon /></button></nav>
  </section>;
}

const treeTheme = createTheme({
  palette: { mode: "dark", primary: { main: "#d3f36b" }, background: { paper: "#18191b" } },
  typography: { fontFamily: "'Space Grotesk', sans-serif" },
});

const treeProjectId = (id: string) => `project:${id}`;
const treeViewId = (projectId: string, id: number) => `view:${projectId}:${id}`;

function ProjectTree({ projects, selectedProjectId, selectedViewId, expandedItems, straightenActive, filter, onProject, onExpanded, onView, onEdit, onDelete, onRename }: { projects: Project[]; selectedProjectId: string; selectedViewId: number | null; expandedItems: string[]; straightenActive: boolean; filter: string; onProject: (id: string) => void; onExpanded: (items: string[]) => void; onView: (projectId: string, id: number) => void; onEdit: (view: View) => void; onDelete: (view: View) => void; onRename: (view: View, name: string) => void }) {
  const [renaming, setRenaming] = useState<number | null>(null);
  const [name, setName] = useState("");
  const query = filter.trim().toLocaleLowerCase();
  const visibleProjects = projects.map((project) => { const projectMatch = !query || project.name.toLocaleLowerCase().includes(query); const views = projectMatch ? project.views : project.views.filter((view) => view.name.toLocaleLowerCase().includes(query)); return { project, views }; }).filter(({ project, views }) => !query || project.name.toLocaleLowerCase().includes(query) || views.length > 0);
  const stopSelection = (event: Event) => event.stopPropagation();
  return <ThemeProvider theme={treeTheme}><SimpleTreeView className="project-tree" aria-label="Projects" expandedItems={expandedItems} selectedItems={selectedViewId === null ? (selectedProjectId ? treeProjectId(selectedProjectId) : null) : treeViewId(selectedProjectId, selectedViewId)} expansionTrigger="iconContainer" onExpandedItemsChange={(_, items) => onExpanded(items)} onSelectedItemsChange={(_, item) => { if (!item) return; if (item.startsWith("project:")) onProject(item.slice(8)); else { const [, projectId, id] = item.split(":"); onView(projectId, Number(id)); } }}>
    {visibleProjects.map(({ project, views }) => <TreeItem key={project.id} itemId={treeProjectId(project.id)} label={<span className="tree-project-label"><span className="project-dot" />{project.name}</span>}>
      {(project.viewsLoading || project.viewsError || project.views.length === 0) && <TreeItem itemId={`${treeProjectId(project.id)}:status`} disabled label={project.viewsLoading ? "Loading…" : project.viewsError ? project.viewsError : "No views"} />}
      {views.map((view) => <TreeItem key={view.id} itemId={treeViewId(project.id, view.id)} label={<span className="tree-view-label"><span className="slice-marker" />{renaming === view.id ? <input autoFocus value={name} onInput={(event) => setName((event.target as HTMLInputElement).value)} onKeyDown={(event) => { event.stopPropagation(); if (event.key === "Enter") { onRename(view, name); setRenaming(null); } if (event.key === "Escape") setRenaming(null); }} onBlur={() => setRenaming(null)} onClick={stopSelection} onMouseDown={stopSelection} aria-label="View name" /> : <span>{view.name}</span>}{!straightenActive && <span className="view-menu" onClick={stopSelection} onMouseDown={stopSelection}><button onClick={() => { setName(view.name); setRenaming(view.id); }} aria-label={`Rename ${view.name}`}>↗</button><button onClick={() => onEdit(view)} aria-label={`Edit ${view.name}`}>□</button><button onClick={() => onDelete(view)} aria-label={`Delete ${view.name}`}>×</button></span>}</span>} />)}
    </TreeItem>)}
  </SimpleTreeView></ThemeProvider>;
}

function App() {
  const [projects, setProjects] = useState<Project[]>([]), [selectedProjectId, setSelectedProjectId] = useState(""), [selectedViewId, setSelectedViewId] = useState<number | null>(null), [expandedItems, setExpandedItems] = useState<string[]>([]), [loading, setLoading] = useState(true), [error, setError] = useState(""), [editor, setEditor] = useState<EditorMode | null>(null), [straightenDraft, setStraightenDraft] = useState<number | null>(null), [straightenText, setStraightenText] = useState(""), [trimDraft, setTrimDraft] = useState<Trim | null>(null), [trimText, setTrimText] = useState<Trim>({ top: 0, right: 0, bottom: 0, left: 0 }), [trimValid, setTrimValid] = useState(true), [autoState, setAutoState] = useState<AutoState>({ loading: false, message: "", error: "" }), [saving, setSaving] = useState(false), [rootSelection, setRootSelection] = useState(0), [viewerControls, setViewerControls] = useState<ViewerControls | null>(null), [filter, setFilter] = useState(""), [sidebarHidden, setSidebarHidden] = useState(false), [backgroundDraft, setBackgroundDraft] = useState<BackgroundRemoval | "none" | null>(null), [backgroundPreview, setBackgroundPreview] = useState<{ url: string; loading: boolean; error: string }>({ url: "", loading: false, error: "" }), [renderToken, setRenderToken] = useState(0);
  const project = projects.find((item) => item.id === selectedProjectId);
  const view = project?.views.find((item) => item.id === selectedViewId);
  const autoMode = editor ? "none" : straightenDraft !== null ? "straighten" : trimDraft !== null ? "trim" : backgroundDraft !== null ? "background" : "none";
  const autoContext = `${view?.id ?? ""}:${autoMode}`;
  const autoRequest = useRef(0);
  const backgroundRequest = useRef(0);
  const renderedUrl = view && !editor && getRemoveBackground(view.pipeline) && trimDraft === null && straightenDraft === null && backgroundDraft === null ? `${API}/projects/${encodeURIComponent(selectedProjectId)}/views/${view.id}/render?render=${renderToken}-${getRotateDegrees(view.pipeline)}-${getStraightenAngle(view.pipeline)}-${encodeURIComponent(JSON.stringify(getTrim(view.pipeline)))}` : undefined;
  const autoContextRef = useRef(autoContext);
  autoContextRef.current = autoContext;
  useEffect(() => { request<string[]>(`${API}/projects`).then((ids) => { const items = ids.map(normalizeProject); setProjects(items); setSelectedProjectId(items[0]?.id ?? ""); if (items[0]) setExpandedItems([treeProjectId(items[0].id)]); }).catch((reason) => setError(reason.message)).finally(() => setLoading(false)); }, []);
  useEffect(() => { if (!selectedProjectId) return; setSelectedViewId(null); setEditor(null); setStraightenDraft(null); setStraightenText(""); setTrimDraft(null); setBackgroundDraft(null); setProjects((items) => items.map((item) => item.id === selectedProjectId ? { ...item, viewsLoading: true, viewsError: "" } : item)); request<View[]>(`${API}/projects/${encodeURIComponent(selectedProjectId)}/views`).then((views) => setProjects((items) => items.map((item) => item.id === selectedProjectId ? { ...item, views, viewsLoading: false } : item))).catch((reason) => setProjects((items) => items.map((item) => item.id === selectedProjectId ? { ...item, viewsLoading: false, viewsError: reason.message } : item))); }, [selectedProjectId]);
  useEffect(() => { autoRequest.current += 1; setAutoState({ loading: false, message: "", error: "" }); }, [autoContext]);
  useEffect(() => {
    const settings = backgroundDraft;
    if (!project || !view || !settings || settings === "none") {
      setBackgroundPreview((value) => { if (value.url) URL.revokeObjectURL(value.url); return { url: "", loading: false, error: "" }; });
      return;
    }
    const requestId = ++backgroundRequest.current;
    const timer = setTimeout(() => {
      setBackgroundPreview((value) => ({ url: value.url, loading: true, error: "" }));
      fetch(`${API}/projects/${encodeURIComponent(project.id)}/views/${view.id}/preview`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ pipeline: setOp(view.pipeline, "remove_background", settings) }) }).then((response) => { if (!response.ok) throw new Error(`Preview failed (${response.status})`); return response.blob(); }).then((blob) => {
        if (requestId !== backgroundRequest.current) return;
        const url = URL.createObjectURL(blob);
        setBackgroundPreview((value) => { if (value.url) URL.revokeObjectURL(value.url); return { url, loading: false, error: "" }; });
      }).catch((reason) => { if (requestId === backgroundRequest.current) setBackgroundPreview((value) => ({ url: value.url, loading: false, error: reason instanceof Error ? reason.message : "Preview failed" })); });
    }, 250);
    return () => clearTimeout(timer);
  }, [backgroundDraft, view?.id, project?.id]);
  const selectProject = (id: string) => { setSelectedProjectId(id); setSelectedViewId(null); setEditor(null); setStraightenDraft(null); setStraightenText(""); setTrimDraft(null); setBackgroundDraft(null); setRootSelection((value) => value + 1); };
  const updateView = async (viewId: number, body: { name: string; pipeline: Pipeline }) => { const updated = await request<View>(`${API}/projects/${encodeURIComponent(selectedProjectId)}/views/${viewId}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }); setProjects((items) => items.map((item) => item.id === selectedProjectId ? { ...item, views: item.views.map((itemView) => itemView.id === viewId ? updated : itemView) } : item)); };
  const confirmView = async (rectangle: Rectangle) => { if (!project) return; setSaving(true); try { const pipeline = setOp(editor?.kind === "edit" ? editor.view.pipeline : [], "crop", rectangle); if (editor?.kind === "edit") { await updateView(editor.view.id, { name: editor.view.name, pipeline }); } else { const name = `View ${project.views.length + 1}`; const created = await request<View>(`${API}/projects/${encodeURIComponent(project.id)}/views`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name, pipeline }) }); setProjects((items) => items.map((item) => item.id === project.id ? { ...item, views: [...item.views, created] } : item)); setSelectedViewId(created.id); } setEditor(null); } catch (reason) { setError(reason.message); } finally { setSaving(false); } };
  const renameView = async (item: View, name: string) => { const nextName = name.trim(); if (!nextName || nextName === item.name) return; try { await updateView(item.id, { name: nextName, pipeline: item.pipeline }); } catch (reason) { setError(reason.message); } };
  const rotateView = async (item: View, delta: number) => { setSaving(true); try { await updateView(item.id, { name: item.name, pipeline: setOp(item.pipeline, "rotate", { degrees: (getRotateDegrees(item.pipeline) + delta + 360) % 360 }) }); } catch (reason) { setError(reason.message); } finally { setSaving(false); } };
  const commitStraightenText = () => { const parsed = parseStraighten(straightenText); if (parsed === null) { setStraightenText(straightenDraft === null ? "" : formatStraighten(straightenDraft)); return; } setStraightenDraft(parsed); setStraightenText(formatStraighten(parsed)); };
  const adjustStraighten = (delta: number) => { const next = Math.max(-45, Math.min(45, Math.round(((straightenDraft ?? 0) + delta) * 10) / 10)); setStraightenDraft(next); setStraightenText(formatStraighten(next)); };
  const confirmStraighten = async () => { const parsed = parseStraighten(straightenText); if (!view || straightenDraft === null || parsed === null) return; setSaving(true); try { await updateView(view.id, { name: view.name, pipeline: setOp(view.pipeline, "straighten", { angle: parsed }) }); setStraightenDraft(null); setStraightenText(""); setTrimDraft(null); } catch (reason) { setError(reason.message); } finally { setSaving(false); } };
  const beginTrim = () => { if (!view) return; const trim = getTrim(view.pipeline); setTrimDraft({ ...trim }); setTrimText({ ...trim }); };
  const updateTrimSide = (side: keyof Trim, value: number) => { const next = { ...(trimDraft ?? trimText), [side]: Math.max(0, value) }; setTrimDraft(next); setTrimText(next); };
  const commitTrimSide = (side: keyof Trim) => { const parsed = parsePixels(String(trimText[side])); if (parsed === null) setTrimText((value) => ({ ...value, [side]: trimDraft?.[side] ?? 0 })); else updateTrimSide(side, parsed); };
  const confirmTrim = async () => { if (!view || !trimDraft || !trimValid || Object.values(trimText).some((value) => parsePixels(String(value)) === null)) return; setSaving(true); try { await updateView(view.id, { name: view.name, pipeline: setOp(view.pipeline, "trim", trimDraft) }); setTrimDraft(null); } catch (reason) { setError(reason.message); } finally { setSaving(false); } };
  const beginBackground = () => { if (!view) return; setStraightenDraft(null); setStraightenText(""); setTrimDraft(null); setBackgroundDraft(getRemoveBackground(view.pipeline) ?? defaultBackgroundRemoval()); };
  const updateBackground = (changes: Partial<BackgroundRemoval>) => setBackgroundDraft((value) => value === null || value === "none" ? value : { ...value, ...changes });
  const parseNumberField = (value: string, min: number, max: number) => /^\d+$/.test(value) ? Math.max(min, Math.min(max, Number(value))) : null;
  const confirmBackground = async () => { if (!view || !backgroundDraft) return; setSaving(true); try { const pipeline = backgroundDraft === "none" ? removeOps(view.pipeline, "remove_background") : setOp(view.pipeline, "remove_background", backgroundDraft); await updateView(view.id, { name: view.name, pipeline }); setBackgroundDraft(null); setRenderToken((value) => value + 1); } catch (reason) { setError(reason.message); } finally { setSaving(false); } };
  const cancelBackground = () => setBackgroundDraft(null);
  const removeBackground = async () => { if (!view || getRemoveBackground(view.pipeline) === null) return; setSaving(true); try { await updateView(view.id, { name: view.name, pipeline: removeOps(view.pipeline, "remove_background") }); setBackgroundDraft(null); setRenderToken((value) => value + 1); } catch (reason) { setError(reason.message); } finally { setSaving(false); } };
  const autoAnalyze = async (operation: "straighten" | "trim") => { if (!view) return; const requestId = ++autoRequest.current; const context = `${view.id}:${operation}`; setAutoState({ loading: true, message: "Calculating…", error: "" }); try { const response = await fetch(`${API}/projects/${encodeURIComponent(project!.id)}/views/${view.id}/auto/${operation}`, { method: "POST" }); if (!response.ok) throw new Error(`Analysis failed (${response.status})`); const result = await response.json() as { suggestion: number | Operation | null; confidence?: number; reason?: string }; if (requestId !== autoRequest.current || autoContextRef.current !== context) return; if (result.suggestion === null) { setAutoState({ loading: false, message: result.reason ?? "No suggestion available", error: "" }); return; } if (operation === "straighten") { if (typeof result.suggestion !== "number" || !Number.isFinite(result.suggestion) || Math.abs(result.suggestion) > 45) throw new Error("Invalid straighten suggestion"); const value = Math.round(result.suggestion * 10) / 10; setStraightenDraft(value); setStraightenText(formatStraighten(value)); } else { const op = result.suggestion; if (!op || typeof op !== "object" || op.kind !== "trim" || typeof op.options !== "object") throw new Error("Invalid trim suggestion"); const value = op.options as Trim; if ([value.top, value.right, value.bottom, value.left].some((item: unknown) => !Number.isInteger(item) || (item as number) < 0)) throw new Error("Invalid trim suggestion"); setTrimDraft(value); setTrimText(value); } const confidence = typeof result.confidence === "number" ? ` · ${Math.round(result.confidence * 100)}% confidence` : ""; setAutoState({ loading: false, message: `Suggestion ready${confidence}`, error: "" }); } catch (reason) { if (requestId === autoRequest.current && autoContextRef.current === context) setAutoState({ loading: false, message: "", error: reason instanceof Error ? reason.message : "Auto analysis failed" }); } };
  const downloadView = () => { if (!view || editor || straightenDraft !== null || trimDraft !== null || backgroundDraft !== null || saving) return; const link = document.createElement("a"); link.href = `${API}/projects/${encodeURIComponent(project!.id)}/views/${view.id}/render`; link.click(); };
  const deleteView = async (item: View) => { if (!confirm(`Delete “${item.name}”?`)) return; try { await request<void>(`${API}/projects/${encodeURIComponent(selectedProjectId)}/views/${item.id}`, { method: "DELETE" }); setProjects((items) => items.map((entry) => entry.id === selectedProjectId ? { ...entry, views: entry.views.filter((viewItem) => viewItem.id !== item.id) } : entry)); if (selectedViewId === item.id) setSelectedViewId(null); } catch (reason) { setError(reason.message); } };
  return <main className="app-shell"><aside className={`toolbar${sidebarHidden ? " sidebar-hidden" : ""}`}><div className="toolbar-head"><div className="brand"><span className="brand-mark">◩</span><span>Cropper</span></div><Tooltip title={sidebarHidden ? "Show sidebar" : "Hide sidebar"}><IconButton className="sidebar-toggle" onClick={() => setSidebarHidden((value) => !value)} aria-label={sidebarHidden ? "Show sidebar" : "Hide sidebar"}>{sidebarHidden ? <MenuOpenOutlinedIcon /> : <MenuOutlinedIcon />}</IconButton></Tooltip></div><div className="toolbar-section"><div className="filter-input"><SearchOutlinedIcon /><input value={filter} onInput={(event) => setFilter((event.target as HTMLInputElement).value)} placeholder="Filter projects" aria-label="Filter projects and views" /></div><span className="eyebrow">Projects</span>{loading && <p className="muted">Loading…</p>}{error && <p className="error">{error}</p>}{!loading && !error && projects.length === 0 && <p className="muted">No projects found.</p>}<ProjectTree projects={projects} selectedProjectId={selectedProjectId} selectedViewId={selectedViewId} expandedItems={expandedItems} straightenActive={straightenDraft !== null || trimDraft !== null || backgroundDraft !== null} filter={filter} onProject={selectProject} onExpanded={setExpandedItems} onView={(projectId, id) => { setEditor(null); setStraightenDraft(null); setStraightenText(""); setTrimDraft(null); setBackgroundDraft(null); setSelectedProjectId(projectId); setSelectedViewId(id); }} onEdit={(item) => { setStraightenDraft(null); setStraightenText(""); setTrimDraft(null); setBackgroundDraft(null); setSelectedViewId(item.id); setEditor({ kind: "edit", view: item }); }} onDelete={deleteView} onRename={renameView} /></div></aside><div className="workspace"><header className={straightenDraft !== null ? "straighten-active" : trimDraft !== null ? "trim-active" : backgroundDraft !== null ? "background-active" : ""}><div className="header-tools">{project && !view && <Tooltip title="Create view"><button className="view-tool" onClick={() => { setStraightenDraft(null); setStraightenText(""); setTrimDraft(null); setEditor({ kind: "create" }); }} disabled={!project} aria-pressed={Boolean(editor)} aria-label="Create view"><AddPhotoAlternateOutlinedIcon /></button></Tooltip>}{view && !editor && straightenDraft === null && backgroundDraft === null && <div className="rotation-tools"><Tooltip title="Rotate view left 90 degrees"><button onClick={() => rotateView(view, -90)} disabled={saving} aria-label="Rotate view left 90 degrees"><Rotate90DegreesCcwOutlinedIcon /></button></Tooltip><Tooltip title="Rotate view right 90 degrees"><button onClick={() => rotateView(view, 90)} disabled={saving} aria-label="Rotate view right 90 degrees"><Rotate90DegreesCwOutlinedIcon /></button></Tooltip></div>}{view && !editor && straightenDraft === null && backgroundDraft === null && <Tooltip title="Straighten view"><button className="straighten-tool" onClick={() => { setStraightenDraft(getStraightenAngle(view.pipeline)); setStraightenText(formatStraighten(getStraightenAngle(view.pipeline))); }} disabled={saving} aria-label="Straighten view"><StraightenOutlinedIcon /></button></Tooltip>}{view && !editor && straightenDraft === null && trimDraft === null && backgroundDraft === null && <Tooltip title="Trim view"><button className="trim-tool" onClick={beginTrim} disabled={saving} aria-label="Trim view"><TuneOutlinedIcon /></button></Tooltip>}{view && !editor && straightenDraft !== null && <div className="straighten-tools"><Tooltip title="Automatically detect straighten angle"><button className="auto-tool" onClick={() => autoAnalyze("straighten")} disabled={autoState.loading || saving} aria-label="Automatically detect straighten angle"><AutoFixHighOutlinedIcon /></button></Tooltip>{autoState.loading && <span className="auto-status">Calculating…</span>}{autoState.error && <span className="auto-error">{autoState.error}</span>}{!autoState.loading && autoState.message && <span className="auto-status">{autoState.message}</span>}<button className="straighten-step" onClick={() => adjustStraighten(-0.1)} disabled={saving} aria-label="Decrease straighten angle by 0.1 degrees">−</button><label className="angle-control"><input className="straighten-number" value={straightenText} onInput={(event) => { const value = (event.target as HTMLInputElement).value; setStraightenText(value); const parsed = parseStraighten(value); if (parsed !== null) setStraightenDraft(parsed); }} onBlur={commitStraightenText} onKeyDown={(event) => { if (event.key === "Enter") commitStraightenText(); }} aria-label="Straighten angle" aria-valuetext={`${straightenText || "invalid"} degrees`} /><span>°</span></label><button className="straighten-step" onClick={() => adjustStraighten(0.1)} disabled={saving} aria-label="Increase straighten angle by 0.1 degrees">+</button><input className="straighten-slider" type="range" min="-45" max="45" step="0.1" value={straightenDraft ?? 0} onChange={(event) => { const value = Number(event.target.value); setStraightenDraft(value); setStraightenText(formatStraighten(value)); }} aria-label="Straighten angle slider" /><Tooltip title="Cancel straighten"><button className="straighten-action" onClick={() => { setStraightenDraft(null); setStraightenText(""); setTrimDraft(null); }} disabled={saving} aria-label="Cancel straighten"><CloseOutlinedIcon /></button></Tooltip><Tooltip title="Confirm straighten"><button className="straighten-action confirm" onClick={confirmStraighten} disabled={saving || autoState.loading || parseStraighten(straightenText) === null} aria-label="Confirm straighten"><CheckOutlinedIcon /></button></Tooltip></div>}{view && !editor && straightenDraft === null && trimDraft !== null && <div className="trim-tools"><Tooltip title="Automatically detect trim"><button className="auto-tool" onClick={() => autoAnalyze("trim")} disabled={autoState.loading || saving} aria-label="Automatically detect trim"><AutoFixHighOutlinedIcon /></button></Tooltip><div className="trim-status">{autoState.loading && <span className="auto-status">Calculating…</span>}{autoState.error && <span className="auto-error">{autoState.error}</span>}{!autoState.loading && autoState.message && <span className="auto-status">{autoState.message}</span>}</div><Tooltip title="Cancel trim"><button className="trim-action" onClick={() => { setTrimDraft(null); }} disabled={saving} aria-label="Cancel trim"><CloseOutlinedIcon /></button></Tooltip><Tooltip title="Confirm trim"><button className="trim-action confirm" onClick={confirmTrim} disabled={saving || autoState.loading || !trimValid || Object.values(trimText).some((value) => parsePixels(String(value)) === null)} aria-label="Confirm trim"><CheckOutlinedIcon /></button></Tooltip></div>}{view && !editor && backgroundDraft === null && <Tooltip title="Remove background"><button className="background-tool" onClick={beginBackground} disabled={saving} aria-label="Remove background"><HideImageOutlinedIcon /></button></Tooltip>}{view && !editor && backgroundDraft !== null && <div className="background-tools">{backgroundPreview.loading && <span className="auto-status">Rendering…</span>}{backgroundPreview.error && <span className="auto-error">{backgroundPreview.error}</span>}<select className="background-model" value={backgroundDraft === "none" ? "none" : backgroundDraft.model} onChange={(event) => { const value = (event.target as HTMLSelectElement).value; if (value === "none") { setBackgroundDraft("none"); } else { setBackgroundDraft((current) => current === null ? current : current === "none" ? { ...defaultBackgroundRemoval(), model: value } : { ...current, model: value }); } }} disabled={saving} aria-label="Background removal model"><option value="none">none</option>{BACKGROUND_REMOVAL_MODELS.map((model) => <option key={model} value={model}>{model}</option>)}</select><label className="background-toggle"><input type="checkbox" checked={backgroundDraft !== "none" && backgroundDraft.alpha_matting} disabled={saving || backgroundDraft === "none"} onChange={(event) => updateBackground({ alpha_matting: (event.target as HTMLInputElement).checked })} aria-label="Alpha matting" /><span>Matting</span></label>{backgroundDraft !== "none" && backgroundDraft.alpha_matting && <label className="background-number"><span>Fg</span><input type="number" min={0} max={255} value={backgroundDraft.alpha_matting_foreground_threshold} onChange={(event) => { const parsed = parseNumberField((event.target as HTMLInputElement).value, 0, 255); if (parsed !== null) updateBackground({ alpha_matting_foreground_threshold: parsed }); }} disabled={saving} aria-label="Alpha matting foreground threshold" /></label>}{backgroundDraft !== "none" && backgroundDraft.alpha_matting && <label className="background-number"><span>Bg</span><input type="number" min={0} max={255} value={backgroundDraft.alpha_matting_background_threshold} onChange={(event) => { const parsed = parseNumberField((event.target as HTMLInputElement).value, 0, 255); if (parsed !== null) updateBackground({ alpha_matting_background_threshold: parsed }); }} disabled={saving} aria-label="Alpha matting background threshold" /></label>}{backgroundDraft !== "none" && backgroundDraft.alpha_matting && <label className="background-number"><span>Erode</span><input type="number" min={1} max={100} value={backgroundDraft.alpha_matting_erode_size} onChange={(event) => { const parsed = parseNumberField((event.target as HTMLInputElement).value, 1, 100); if (parsed !== null) updateBackground({ alpha_matting_erode_size: parsed }); }} disabled={saving} aria-label="Alpha matting erode size" /></label>}<label className="background-toggle"><input type="checkbox" checked={backgroundDraft !== "none" && backgroundDraft.post_process_mask} disabled={saving || backgroundDraft === "none"} onChange={(event) => updateBackground({ post_process_mask: (event.target as HTMLInputElement).checked })} aria-label="Post-process mask" /><span>Clean mask</span></label>{getRemoveBackground(view.pipeline) && <Tooltip title="Remove saved background removal"><button className="background-action" onClick={removeBackground} disabled={saving} aria-label="Remove saved background removal"><DeleteOutlineOutlinedIcon /></button></Tooltip>}<Tooltip title="Cancel background removal"><button className="background-action" onClick={cancelBackground} disabled={saving} aria-label="Cancel background removal"><CloseOutlinedIcon /></button></Tooltip><Tooltip title="Confirm background removal"><button className="background-action confirm" onClick={confirmBackground} disabled={saving || backgroundPreview.loading || (backgroundDraft === "none" && !getRemoveBackground(view.pipeline))} aria-label="Confirm background removal"><CheckOutlinedIcon /></button></Tooltip></div>}{view && !editor && straightenDraft === null && trimDraft === null && backgroundDraft === null && <Tooltip title="Download selected view as PNG"><button className="download-tool" onClick={downloadView} disabled={saving} aria-label="Download selected view as PNG"><DownloadOutlinedIcon /></button></Tooltip>}<div className="view-presets"><button onClick={() => viewerControls?.fit()} disabled={!viewerControls}>Fit</button><button onClick={() => viewerControls?.fitWidth()} disabled={!viewerControls}>Fit Width</button><button onClick={() => viewerControls?.actualSize()} disabled={!viewerControls}>Actual Size</button></div><div className="zoom-tools"><button onClick={() => viewerControls?.zoomOut()} disabled={!viewerControls} aria-label="Zoom out">−</button><button onClick={() => viewerControls?.zoomIn()} disabled={!viewerControls} aria-label="Zoom in">+</button></div></div></header><Viewer project={project} view={view} editor={editor} saving={saving} straightenDraft={straightenDraft} trimDraft={trimDraft} renderedUrl={renderedUrl} previewUrl={backgroundDraft !== null && backgroundDraft !== "none" && backgroundPreview.url ? backgroundPreview.url : undefined} rootSelection={rootSelection} onConfirm={confirmView} onCancel={() => setEditor(null)} onTrimValidity={setTrimValid} onControlsReady={setViewerControls}>{view && !editor && straightenDraft === null && trimDraft !== null && <div className="trim-overlay" onPointerDown={(event) => event.stopPropagation()}><label className="trim-control trim-top"><span>Top</span><span className="trim-stepper"><button className="trim-step" onClick={() => updateTrimSide("top", trimText.top - 1)} disabled={saving}>−</button><input value={trimText.top} inputMode="numeric" aria-label="Trim top pixels" onInput={(event) => setTrimText((value) => ({ ...value, top: (event.target as HTMLInputElement).value }))} onBlur={() => commitTrimSide("top")} onKeyDown={(event) => { if (event.key === "Enter") commitTrimSide("top"); }} /><button className="trim-step" onClick={() => updateTrimSide("top", trimText.top + 1)} disabled={saving}>+</button></span></label><label className="trim-control trim-left"><span>Left</span><span className="trim-stepper"><button className="trim-step" onClick={() => updateTrimSide("left", trimText.left - 1)} disabled={saving}>−</button><input value={trimText.left} inputMode="numeric" aria-label="Trim left pixels" onInput={(event) => setTrimText((value) => ({ ...value, left: (event.target as HTMLInputElement).value }))} onBlur={() => commitTrimSide("left")} onKeyDown={(event) => { if (event.key === "Enter") commitTrimSide("left"); }} /><button className="trim-step" onClick={() => updateTrimSide("left", trimText.left + 1)} disabled={saving}>+</button></span></label><label className="trim-control trim-right"><span>Right</span><span className="trim-stepper"><button className="trim-step" onClick={() => updateTrimSide("right", trimText.right - 1)} disabled={saving}>−</button><input value={trimText.right} inputMode="numeric" aria-label="Trim right pixels" onInput={(event) => setTrimText((value) => ({ ...value, right: (event.target as HTMLInputElement).value }))} onBlur={() => commitTrimSide("right")} onKeyDown={(event) => { if (event.key === "Enter") commitTrimSide("right"); }} /><button className="trim-step" onClick={() => updateTrimSide("right", trimText.right + 1)} disabled={saving}>+</button></span></label><label className="trim-control trim-bottom"><span>Bottom</span><span className="trim-stepper"><button className="trim-step" onClick={() => updateTrimSide("bottom", trimText.bottom - 1)} disabled={saving}>−</button><input value={trimText.bottom} inputMode="numeric" aria-label="Trim bottom pixels" onInput={(event) => setTrimText((value) => ({ ...value, bottom: (event.target as HTMLInputElement).value }))} onBlur={() => commitTrimSide("bottom")} onKeyDown={(event) => { if (event.key === "Enter") commitTrimSide("bottom"); }} /><button className="trim-step" onClick={() => updateTrimSide("bottom", trimText.bottom + 1)} disabled={saving}>+</button></span></label></div>}</Viewer></div></main>;
}

createRoot(document.getElementById("app")!).render(<App />);
