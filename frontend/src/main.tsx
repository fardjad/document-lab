import { createRoot } from "react-dom/client";
import { useEffect, useRef, useState } from "react";
import type { MouseEvent as ReactMouseEvent, PointerEvent as ReactPointerEvent } from "react";
import { createTheme, ThemeProvider } from "@mui/material/styles";
import { SimpleTreeView } from "@mui/x-tree-view/SimpleTreeView";
import { TreeItem } from "@mui/x-tree-view/TreeItem";
import "./style.css";

type Rectangle = { x: number; y: number; width: number; height: number };
type Slice = { id: number; name: string; rectangle: Rectangle; rotation: number };
type Project = { id: string; name: string; imageUrl: string; slices: Slice[]; slicesLoading?: boolean; slicesError?: string };
type EditorMode = { kind: "create" } | { kind: "edit"; slice: Slice };

const API = "http://localhost:8000/api";

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  if (!response.ok) throw new Error(`Request failed (${response.status})`);
  return response.status === 204 ? (undefined as T) : response.json();
}

function normalizeProject(id: string): Project {
  return { id, name: id, imageUrl: `${API}/projects/${encodeURIComponent(id)}/image`, slices: [] };
}

function rotatedBounds(rectangle: Rectangle, rotation: number) {
  return rotation % 180 !== 0 ? { width: rectangle.height, height: rectangle.width } : { width: rectangle.width, height: rectangle.height };
}

type ViewerControls = { fit: () => void; fitWidth: () => void; actualSize: () => void; zoomOut: () => void; zoomIn: () => void };

function Viewer({ project, slice, editor, saving, rootSelection, onConfirm, onCancel, onControlsReady }: { project?: Project; slice?: Slice; editor: EditorMode | null; saving: boolean; rootSelection: number; onConfirm: (rectangle: Rectangle) => void; onCancel: () => void; onControlsReady: (controls: ViewerControls | null) => void }) {
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
  const displayRect = editor ? undefined : slice ? imageRectangle(slice.rectangle) : undefined;
  const rotation = displayRect && slice && !editor ? ((slice.rotation % 360) + 360) % 360 : 0;
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
    return { source, view: displayRect ? { x: 0, y: 0, ...rotatedBounds(source, rotation) } : source };
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
      surfaceRef.current.style.left = `${(rect.width - sourceRect.width) / 2}px`;
      surfaceRef.current.style.top = `${(rect.height - sourceRect.height) / 2}px`;
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
  const handleImageLoad = () => { if (slice && !editor) update(); else fit(); };
  useEffect(() => {
    onControlsReady({ fit, fitWidth, actualSize, zoomOut: () => changeZoom(0.89), zoomIn: () => changeZoom(1.12) });
    return () => onControlsReady(null);
  }, [project?.id, slice?.id, editor?.kind]);
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
    setDraft(editor?.kind === "edit" ? imageRectangle(editor.slice.rectangle) ?? null : null);
    update();
  }, [editor?.kind, editor?.kind === "edit" ? editor.slice.id : null]);
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
  }, [slice?.id, slice?.rotation]);
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
    {editor && draft && <div ref={draftElement} className="slice-draft" style={overlayStyle} aria-label="Slice selection" onPointerDown={startMove}><button className="draft-move-surface" onPointerDown={startMove} onClick={stopViewerPointer} aria-label="Move slice rectangle" /><button className="slice-handle handle-top" onPointerDown={(event) => startResize(event, "top")} onClick={stopViewerPointer} aria-label="Resize slice top edge" /><button className="slice-handle handle-right" onPointerDown={(event) => startResize(event, "right")} onClick={stopViewerPointer} aria-label="Resize slice right edge" /><button className="slice-handle handle-bottom" onPointerDown={(event) => startResize(event, "bottom")} onClick={stopViewerPointer} aria-label="Resize slice bottom edge" /><button className="slice-handle handle-left" onPointerDown={(event) => startResize(event, "left")} onClick={stopViewerPointer} aria-label="Resize slice left edge" /><span>{Math.round(draft.width)} × {Math.round(draft.height)}</span><div className="slice-actions" onPointerDown={overlayPointerDown} onClick={stopViewerPointer}><button onClick={confirmDraft} disabled={saving || draft.width < 4 || draft.height < 4} aria-label="Confirm slice">✓</button><button onClick={onCancel} disabled={saving} aria-label="Cancel slice">×</button></div></div>}
    {editor && <div className="draw-hint">{draft ? "Drag box to move · Space + drag or middle-drag to pan" : "Drag over image to draw slice · Space + drag or middle-drag to pan"}</div>}
    <div className="zoom-readout">{zoomReadout}%</div>
  </section>;
}

const treeTheme = createTheme({
  palette: { mode: "dark", primary: { main: "#d3f36b" }, background: { paper: "#18191b" } },
  typography: { fontFamily: "'Space Grotesk', sans-serif" },
});

const treeProjectId = (id: string) => `project:${id}`;
const treeSliceId = (projectId: string, id: number) => `slice:${projectId}:${id}`;

function ProjectTree({ projects, selectedProjectId, selectedSliceId, expandedItems, onProject, onExpanded, onSlice, onEdit, onDelete, onRename }: { projects: Project[]; selectedProjectId: string; selectedSliceId: number | null; expandedItems: string[]; onProject: (id: string) => void; onExpanded: (items: string[]) => void; onSlice: (projectId: string, id: number) => void; onEdit: (slice: Slice) => void; onDelete: (slice: Slice) => void; onRename: (slice: Slice, name: string) => void }) {
  const [renaming, setRenaming] = useState<number | null>(null);
  const [name, setName] = useState("");
  const stopSelection = (event: Event) => event.stopPropagation();
  return <ThemeProvider theme={treeTheme}><SimpleTreeView className="project-tree" aria-label="Projects" expandedItems={expandedItems} selectedItems={selectedSliceId === null ? (selectedProjectId ? treeProjectId(selectedProjectId) : null) : treeSliceId(selectedProjectId, selectedSliceId)} expansionTrigger="iconContainer" onExpandedItemsChange={(_, items) => onExpanded(items)} onSelectedItemsChange={(_, item) => { if (!item) return; if (item.startsWith("project:")) onProject(item.slice(8)); else { const [, projectId, id] = item.split(":"); onSlice(projectId, Number(id)); } }}>
    {projects.map((project) => <TreeItem key={project.id} itemId={treeProjectId(project.id)} label={<span className="tree-project-label"><span className="project-dot" />{project.name}</span>}>
      {(project.slicesLoading || project.slicesError || project.slices.length === 0) && <TreeItem itemId={`${treeProjectId(project.id)}:status`} disabled label={project.slicesLoading ? "Loading…" : project.slicesError ? project.slicesError : "No slices"} />}
      {project.slices.map((slice) => <TreeItem key={slice.id} itemId={treeSliceId(project.id, slice.id)} label={<span className="tree-slice-label"><span className="slice-marker" />{renaming === slice.id ? <input autoFocus value={name} onInput={(event) => setName((event.target as HTMLInputElement).value)} onKeyDown={(event) => { if (event.key === "Enter") { onRename(slice, name); setRenaming(null); } if (event.key === "Escape") setRenaming(null); }} onBlur={() => setRenaming(null)} onClick={stopSelection} onMouseDown={stopSelection} aria-label="Slice name" /> : <span>{slice.name}</span>}<span className="slice-menu" onClick={stopSelection} onMouseDown={stopSelection}><button onClick={() => { setName(slice.name); setRenaming(slice.id); }} aria-label={`Rename ${slice.name}`}>↗</button><button onClick={() => onEdit(slice)} aria-label={`Edit ${slice.name}`}>□</button><button onClick={() => onDelete(slice)} aria-label={`Delete ${slice.name}`}>×</button></span></span>} />)}
    </TreeItem>)}
  </SimpleTreeView></ThemeProvider>;
}

function App() {
  const [projects, setProjects] = useState<Project[]>([]), [selectedProjectId, setSelectedProjectId] = useState(""), [selectedSliceId, setSelectedSliceId] = useState<number | null>(null), [expandedItems, setExpandedItems] = useState<string[]>([]), [loading, setLoading] = useState(true), [error, setError] = useState(""), [editor, setEditor] = useState<EditorMode | null>(null), [saving, setSaving] = useState(false), [rootSelection, setRootSelection] = useState(0), [viewerControls, setViewerControls] = useState<ViewerControls | null>(null);
  const project = projects.find((item) => item.id === selectedProjectId);
  const slice = project?.slices.find((item) => item.id === selectedSliceId);
  useEffect(() => { request<string[]>(`${API}/projects`).then((ids) => { const items = ids.map(normalizeProject); setProjects(items); setSelectedProjectId(items[0]?.id ?? ""); if (items[0]) setExpandedItems([treeProjectId(items[0].id)]); }).catch((reason) => setError(reason.message)).finally(() => setLoading(false)); }, []);
  useEffect(() => { if (!selectedProjectId) return; setSelectedSliceId(null); setEditor(null); setProjects((items) => items.map((item) => item.id === selectedProjectId ? { ...item, slicesLoading: true, slicesError: "" } : item)); request<Slice[]>(`${API}/projects/${encodeURIComponent(selectedProjectId)}/slices`).then((slices) => setProjects((items) => items.map((item) => item.id === selectedProjectId ? { ...item, slices, slicesLoading: false } : item))).catch((reason) => setProjects((items) => items.map((item) => item.id === selectedProjectId ? { ...item, slicesLoading: false, slicesError: reason.message } : item))); }, [selectedProjectId]);
  const selectProject = (id: string) => { setSelectedProjectId(id); setSelectedSliceId(null); setEditor(null); setRootSelection((value) => value + 1); };
  const updateSlice = async (sliceId: number, body: { name: string; rectangle: Rectangle; rotation: number }) => { const updated = await request<Slice>(`${API}/projects/${encodeURIComponent(selectedProjectId)}/slices/${sliceId}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }); setProjects((items) => items.map((item) => item.id === selectedProjectId ? { ...item, slices: item.slices.map((itemSlice) => itemSlice.id === sliceId ? updated : itemSlice) } : item)); };
  const confirmSlice = async (rectangle: Rectangle) => { if (!project) return; setSaving(true); try { if (editor?.kind === "edit") { await updateSlice(editor.slice.id, { name: editor.slice.name, rectangle, rotation: editor.slice.rotation }); } else { const created = await request<Slice>(`${API}/projects/${encodeURIComponent(project.id)}/slices`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ rectangle }) }); setProjects((items) => items.map((item) => item.id === project.id ? { ...item, slices: [...item.slices, created] } : item)); setSelectedSliceId(created.id); } setEditor(null); } catch (reason) { setError(reason.message); } finally { setSaving(false); } };
  const renameSlice = async (item: Slice, name: string) => { const nextName = name.trim(); if (!nextName || nextName === item.name) return; try { await updateSlice(item.id, { name: nextName, rectangle: item.rectangle, rotation: item.rotation }); } catch (reason) { setError(reason.message); } };
  const rotateSlice = async (item: Slice, delta: number) => { setSaving(true); try { await updateSlice(item.id, { name: item.name, rectangle: item.rectangle, rotation: (item.rotation + delta + 360) % 360 }); } catch (reason) { setError(reason.message); } finally { setSaving(false); } };
  const deleteSlice = async (item: Slice) => { if (!confirm(`Delete “${item.name}”?`)) return; try { await request<void>(`${API}/projects/${encodeURIComponent(selectedProjectId)}/slices/${item.id}`, { method: "DELETE" }); setProjects((items) => items.map((entry) => entry.id === selectedProjectId ? { ...entry, slices: entry.slices.filter((sliceItem) => sliceItem.id !== item.id) } : entry)); if (selectedSliceId === item.id) setSelectedSliceId(null); } catch (reason) { setError(reason.message); } };
  return <main className="app-shell"><aside className="toolbar"><div className="brand"><span className="brand-mark">◩</span><span>Cropper</span></div><div className="toolbar-section"><span className="eyebrow">Projects</span>{loading && <p className="muted">Loading…</p>}{error && <p className="error">{error}</p>}{!loading && !error && projects.length === 0 && <p className="muted">No projects found.</p>}<ProjectTree projects={projects} selectedProjectId={selectedProjectId} selectedSliceId={selectedSliceId} expandedItems={expandedItems} onProject={selectProject} onExpanded={setExpandedItems} onSlice={(projectId, id) => { setEditor(null); setSelectedProjectId(projectId); setSelectedSliceId(id); }} onEdit={(item) => { setSelectedSliceId(item.id); setEditor({ kind: "edit", slice: item }); }} onDelete={deleteSlice} onRename={renameSlice} /></div><div className="toolbar-foot">Drag edge to resize<br /><span>Wheel zoom · drag pan</span></div></aside><div className="workspace"><header><div><span className="eyebrow">Workspace</span><h1>{project?.name ?? "Document viewer"}</h1></div><div className="header-tools"><button className="slice-tool" onClick={() => setEditor({ kind: "create" })} disabled={!project} aria-pressed={Boolean(editor)}>＋ Slice</button>{slice && !editor && <div className="rotation-tools"><button onClick={() => rotateSlice(slice, -90)} disabled={saving} aria-label="Rotate slice left 90 degrees" title="Rotate slice left 90 degrees">↶ 90°</button><button onClick={() => rotateSlice(slice, 90)} disabled={saving} aria-label="Rotate slice right 90 degrees" title="Rotate slice right 90 degrees">↷ 90°</button></div>}<div className="view-presets"><button onClick={() => viewerControls?.fit()} disabled={!viewerControls}>Fit</button><button onClick={() => viewerControls?.fitWidth()} disabled={!viewerControls}>Fit Width</button><button onClick={() => viewerControls?.actualSize()} disabled={!viewerControls}>Actual Size</button></div><div className="zoom-tools"><button onClick={() => viewerControls?.zoomOut()} disabled={!viewerControls} aria-label="Zoom out">−</button><button onClick={() => viewerControls?.zoomIn()} disabled={!viewerControls} aria-label="Zoom in">+</button></div><span className="status"><i />{project ? "Ready" : "Waiting"}</span></div></header><Viewer project={project} slice={slice} editor={editor} saving={saving} rootSelection={rootSelection} onConfirm={confirmSlice} onCancel={() => setEditor(null)} onControlsReady={setViewerControls} /></div></main>;
}

createRoot(document.getElementById("app")!).render(<App />);
