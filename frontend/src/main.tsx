import { createRoot } from "react-dom/client";
import { useEffect, useRef, useState } from "react";
import { createTheme, ThemeProvider } from "@mui/material/styles";
import { SimpleTreeView } from "@mui/x-tree-view/SimpleTreeView";
import { TreeItem } from "@mui/x-tree-view/TreeItem";
import "./style.css";

type Project = { id: string; name: string; imageUrl: string };
type ViewerControls = { fit: () => void; fitWidth: () => void; actualSize: () => void; zoomOut: () => void; zoomIn: () => void };

const API = "http://localhost:8000/api";
const theme = createTheme({
  palette: { mode: "dark", primary: { main: "#d3f36b" }, background: { paper: "#18191b" } },
  typography: { fontFamily: "'Space Grotesk', sans-serif" },
  components: { MuiTreeItem: { styleOverrides: { content: { borderRadius: 7, padding: "9px 10px", color: "#aeb0b3", "&:hover": { background: "#242629", color: "#fff" }, "&.Mui-selected": { background: "#d3f36b", color: "#151713", fontWeight: 600 }, "&.Mui-focused": { outline: "2px solid #d3f36b", outlineOffset: "-2px" } }, iconContainer: { color: "currentColor" } } } },
});

function normalizeProject(id: string): Project { return { id, name: id, imageUrl: `${API}/projects/${encodeURIComponent(id)}/image` }; }

function Viewer({ project, onControlsReady }: { project?: Project; onControlsReady: (controls: ViewerControls | null) => void }) {
  const zoom = useRef(1), offset = useRef({ x: 0, y: 0 }), viewport = useRef<HTMLDivElement>(null), image = useRef<HTMLImageElement>(null), dragging = useRef(false), start = useRef({ x: 0, y: 0 });
  const [zoomReadout, setZoomReadout] = useState(100);
  const update = () => { image.current?.style.setProperty("transform", `translate(${offset.current.x}px, ${offset.current.y}px) scale(${zoom.current})`); setZoomReadout(Math.round(zoom.current * 100)); };
  const fit = () => { const box = viewport.current, source = image.current; if (!box || !source?.naturalWidth || !source.naturalHeight) return; const scale = Math.min((box.clientWidth - 64) / source.naturalWidth, (box.clientHeight - 64) / source.naturalHeight); zoom.current = Math.max(0.15, Math.min(1, scale)); offset.current = { x: (box.clientWidth - source.naturalWidth * zoom.current) / 2, y: (box.clientHeight - source.naturalHeight * zoom.current) / 2 }; update(); };
  const fitWidth = () => { const box = viewport.current, source = image.current; if (!box || !source?.naturalWidth || !source.naturalHeight) return; zoom.current = Math.max(0.15, Math.min(6, (box.clientWidth - 64) / source.naturalWidth)); offset.current.x = (box.clientWidth - source.naturalWidth * zoom.current) / 2; update(); };
  const actualSize = () => { const box = viewport.current, source = image.current; if (!box || !source?.naturalWidth || !source.naturalHeight) return; zoom.current = 1; offset.current = { x: (box.clientWidth - source.naturalWidth) / 2, y: (box.clientHeight - source.naturalHeight) / 2 }; update(); };
  const changeZoom = (factor: number, point?: { x: number; y: number }) => { const box = viewport.current; if (!box) return; const next = Math.min(6, Math.max(0.15, zoom.current * factor)); const px = point?.x ?? box.clientWidth / 2, py = point?.y ?? box.clientHeight / 2; offset.current = { x: px - (px - offset.current.x) * next / zoom.current, y: py - (py - offset.current.y) * next / zoom.current }; zoom.current = next; update(); };
  useEffect(() => { onControlsReady({ fit, fitWidth, actualSize, zoomOut: () => changeZoom(0.89), zoomIn: () => changeZoom(1.12) }); return () => onControlsReady(null); }, [project?.id]);
  useEffect(() => { zoom.current = 1; offset.current = { x: 0, y: 0 }; setZoomReadout(100); const box = viewport.current, source = image.current; if (!box || !source) return; source.addEventListener("load", fit); const observer = new ResizeObserver(fit); observer.observe(box); if (source.complete) fit(); return () => { source.removeEventListener("load", fit); observer.disconnect(); }; }, [project?.id]);
  const wheel = (event: WheelEvent) => { event.preventDefault(); const box = viewport.current!.getBoundingClientRect(); changeZoom(event.deltaY < 0 ? 1.12 : 0.89, { x: event.clientX - box.left, y: event.clientY - box.top }); };
  return <section className="viewer" ref={viewport} onWheel={wheel} onPointerDown={(event) => { dragging.current = true; start.current = { x: event.clientX - offset.current.x, y: event.clientY - offset.current.y }; viewport.current?.setPointerCapture(event.pointerId); }} onPointerMove={(event) => { if (!dragging.current) return; offset.current = { x: event.clientX - start.current.x, y: event.clientY - start.current.y }; update(); }} onPointerUp={() => { dragging.current = false; }}>
    {project?.imageUrl ? <img key={project.id} ref={image} className="document" src={project.imageUrl} alt={project.name} draggable={false} onLoad={fit} /> : <div className="empty-view">Select project to begin</div>}
    <div className="zoom-readout">{zoomReadout}%</div>
  </section>;
}

function App() {
  const [projects, setProjects] = useState<Project[]>([]), [selectedId, setSelectedId] = useState(""), [expandedItems, setExpandedItems] = useState<string[]>([]), [loading, setLoading] = useState(true), [error, setError] = useState(""), [viewerControls, setViewerControls] = useState<ViewerControls | null>(null);
  const selected = projects.find((project) => project.id === selectedId);
  useEffect(() => { fetch(`${API}/projects`).then((response) => { if (!response.ok) throw new Error(`Projects request failed (${response.status})`); return response.json(); }).then((body) => { const items = (Array.isArray(body) ? body : []).map(normalizeProject); setProjects(items); setSelectedId(items[0]?.id ?? ""); if (items[0]) setExpandedItems([items[0].id]); }).catch((reason) => setError(reason instanceof Error ? reason.message : "Could not load projects")).finally(() => setLoading(false)); }, []);
  return <ThemeProvider theme={theme}><main className="app-shell"><aside className="toolbar"><div className="brand"><span className="brand-mark">◩</span><span>Cropper</span></div><div className="toolbar-section"><span className="eyebrow">Projects</span>{loading && <p className="muted">Loading…</p>}{error && <p className="error">{error}</p>}{!loading && !error && projects.length === 0 && <p className="muted">No projects found.</p>}<SimpleTreeView className="project-tree" aria-label="Projects" expandedItems={expandedItems} selectedItems={selectedId || null} onExpandedItemsChange={(_, items) => setExpandedItems(items)} expansionTrigger="iconContainer" onSelectedItemsChange={(_, item) => { if (item) setSelectedId(item); }}>{projects.map((project) => <TreeItem key={project.id} itemId={project.id} label={<span className="tree-project-label"><span className="project-dot" />{project.name}</span>} />)}</SimpleTreeView></div><div className="toolbar-foot">Drag edge to resize<br /><span>Wheel zoom · drag pan</span></div></aside><div className="workspace"><header><div><span className="eyebrow">Workspace</span><h1>{selected?.name ?? "Document viewer"}</h1></div><div className="header-tools"><div className="view-presets"><button onClick={() => viewerControls?.fit()} disabled={!viewerControls}>Fit</button><button onClick={() => viewerControls?.fitWidth()} disabled={!viewerControls}>Fit Width</button><button onClick={() => viewerControls?.actualSize()} disabled={!viewerControls}>Actual Size</button></div><div className="zoom-tools"><button onClick={() => viewerControls?.zoomOut()} disabled={!viewerControls} aria-label="Zoom out">−</button><button onClick={() => viewerControls?.zoomIn()} disabled={!viewerControls} aria-label="Zoom in">+</button></div><span className="status"><i />{selected ? "Ready" : "Waiting"}</span></div></header><Viewer project={selected} onControlsReady={setViewerControls} /></div></main></ThemeProvider>;
}

createRoot(document.getElementById("app")!).render(<App />);
