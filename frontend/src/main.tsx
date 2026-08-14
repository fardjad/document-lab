import { render } from "preact";
import { useEffect, useRef, useState } from "preact/hooks";
import { signal, computed } from "@preact/signals";
import "./style.css";

type Project = Record<string, unknown> & { id: string; name: string; imageUrl: string };

const projects = signal<Project[]>([]);
const selectedId = signal("");
const loading = signal(true);
const error = signal("");
const selected = computed(() => projects.value.find((project) => project.id === selectedId.value));

function normalizeProject(id: string): Project {
  return {
    id,
    name: id,
    imageUrl: `http://localhost:8000/api/projects/${encodeURIComponent(id)}/image`,
  };
}

async function loadProjects() {
  try {
    const response = await fetch("http://localhost:8000/api/projects");
    if (!response.ok) throw new Error(`Projects request failed (${response.status})`);
    const body = await response.json();
    const list: string[] = Array.isArray(body) ? body : [];
    projects.value = list.map(normalizeProject);
    selectedId.value = projects.value[0]?.id ?? "";
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : "Could not load projects";
  } finally {
    loading.value = false;
  }
}

type ViewerControls = {
  fit: () => void;
  fitWidth: () => void;
  actualSize: () => void;
  zoomOut: () => void;
  zoomIn: () => void;
};

function Viewer({ project, onControlsReady }: { project?: Project; onControlsReady: (controls: ViewerControls | null) => void }) {
  const zoom = useRef(1);
  const offset = useRef({ x: 0, y: 0 });
  const viewport = useRef<HTMLDivElement>(null);
  const image = useRef<HTMLImageElement>(null);
  const dragging = useRef(false);
  const start = useRef({ x: 0, y: 0 });
  const [zoomReadout, setZoomReadout] = useState(100);

  const update = () => {
    image.current?.style.setProperty("transform", `translate(${offset.current.x}px, ${offset.current.y}px) scale(${zoom.current})`);
    setZoomReadout(Math.round(zoom.current * 100));
  };
  const fit = () => {
    const viewportElement = viewport.current;
    const imageElement = image.current;
    if (!viewportElement || !imageElement?.naturalWidth || !imageElement.naturalHeight) return;
    const padding = 32;
    const scale = Math.min((viewportElement.clientWidth - padding * 2) / imageElement.naturalWidth, (viewportElement.clientHeight - padding * 2) / imageElement.naturalHeight);
    zoom.current = Math.max(0.15, Math.min(1, scale));
    offset.current = { x: (viewportElement.clientWidth - imageElement.naturalWidth * zoom.current) / 2, y: (viewportElement.clientHeight - imageElement.naturalHeight * zoom.current) / 2 };
    update();
  };
  const fitWidth = () => {
    const viewportElement = viewport.current;
    const imageElement = image.current;
    if (!viewportElement || !imageElement?.naturalWidth || !imageElement.naturalHeight) return;
    zoom.current = Math.max(0.15, Math.min(6, (viewportElement.clientWidth - 64) / imageElement.naturalWidth));
    offset.current.x = (viewportElement.clientWidth - imageElement.naturalWidth * zoom.current) / 2;
    update();
  };
  const actualSize = () => {
    const viewportElement = viewport.current;
    const imageElement = image.current;
    if (!viewportElement || !imageElement?.naturalWidth || !imageElement.naturalHeight) return;
    zoom.current = 1;
    offset.current = { x: (viewportElement.clientWidth - imageElement.naturalWidth) / 2, y: (viewportElement.clientHeight - imageElement.naturalHeight) / 2 };
    update();
  };
  const changeZoom = (factor: number) => {
    const viewportElement = viewport.current;
    if (!viewportElement) return;
    const next = Math.min(6, Math.max(0.15, zoom.current * factor));
    const px = viewportElement.clientWidth / 2, py = viewportElement.clientHeight / 2;
    offset.current = { x: px - (px - offset.current.x) * next / zoom.current, y: py - (py - offset.current.y) * next / zoom.current };
    zoom.current = next;
    update();
  };
  useEffect(() => {
    onControlsReady({ fit, fitWidth, actualSize, zoomOut: () => changeZoom(0.89), zoomIn: () => changeZoom(1.12) });
    return () => onControlsReady(null);
  }, [project?.id]);
  useEffect(() => {
    zoom.current = 1;
    offset.current = { x: 0, y: 0 };
    setZoomReadout(100);

    const viewportElement = viewport.current;
    const imageElement = image.current;
    if (!viewportElement || !imageElement) return;

    imageElement.addEventListener("load", fit);
    const observer = new ResizeObserver(fit);
    observer.observe(viewportElement);
    if (imageElement.complete) fit();
    return () => {
      imageElement.removeEventListener("load", fit);
      observer.disconnect();
    };
  }, [project?.id]);
  const wheel = (event: WheelEvent) => {
    event.preventDefault();
    const box = viewport.current!.getBoundingClientRect();
    const next = Math.min(6, Math.max(0.15, zoom.current * (event.deltaY < 0 ? 1.12 : 0.89)));
    const px = event.clientX - box.left, py = event.clientY - box.top;
    offset.current = { x: px - (px - offset.current.x) * next / zoom.current, y: py - (py - offset.current.y) * next / zoom.current };
    zoom.current = next; update();
  };
  return <section class="viewer" ref={viewport} onWheel={wheel} onPointerDown={(event) => { dragging.current = true; start.current = { x: event.clientX - offset.current.x, y: event.clientY - offset.current.y }; viewport.current?.setPointerCapture(event.pointerId); }} onPointerMove={(event) => { if (!dragging.current) return; offset.current = { x: event.clientX - start.current.x, y: event.clientY - start.current.y }; update(); }} onPointerUp={() => { dragging.current = false; }}>
    {project?.imageUrl ? <img ref={image} class="document" src={project.imageUrl} alt={project.name} draggable={false} /> : <div class="empty-view">{project ? "No image endpoint for this project" : "Select project to begin"}</div>}
    <div class="zoom-readout">{zoomReadout}%</div>
  </section>;
}

function App() {
  const [viewerControls, setViewerControls] = useState<ViewerControls | null>(null);
  useEffect(() => { loadProjects(); }, []);
  return <main class="app-shell">
    <aside class="toolbar">
      <div class="brand"><span class="brand-mark">◩</span><span>Cropper</span></div>
      <div class="toolbar-section"><span class="eyebrow">Projects</span>{loading.value && <p class="muted">Loading…</p>}{error.value && <p class="error">{error.value}</p>}{!loading.value && !error.value && projects.value.length === 0 && <p class="muted">No projects found.</p>}
        <nav class="project-list">{projects.value.map((project) => <button class={{ project: true, active: project.id === selectedId.value }} onClick={() => { selectedId.value = project.id; }}><span class="project-dot" />{project.name}</button>)}</nav>
      </div>
      <div class="toolbar-foot">Drag edge to resize<br /><span>Wheel zoom · drag pan</span></div>
    </aside>
    <div class="workspace"><header><div><span class="eyebrow">Workspace</span><h1>{selected.value?.name ?? "Document viewer"}</h1></div><div class="header-tools"><div class="view-presets"><button onClick={() => viewerControls?.fit()} disabled={!viewerControls}>Fit</button><button onClick={() => viewerControls?.fitWidth()} disabled={!viewerControls}>Fit Width</button><button onClick={() => viewerControls?.actualSize()} disabled={!viewerControls}>Actual Size</button></div><div class="zoom-tools"><button onClick={() => viewerControls?.zoomOut()} disabled={!viewerControls} aria-label="Zoom out" title="Zoom out">−</button><button onClick={() => viewerControls?.zoomIn()} disabled={!viewerControls} aria-label="Zoom in" title="Zoom in">+</button></div><span class="status"><i />{selected.value ? "Ready" : "Waiting"}</span></div></header><Viewer project={selected.value} onControlsReady={setViewerControls} /></div>
  </main>;
}

render(<App />, document.getElementById("app")!);
