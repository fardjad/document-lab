import { createRoot } from "react-dom/client";
import { useEffect, useMemo, useRef, useState } from "react";
import type { ChangeEvent, PointerEvent as ReactPointerEvent } from "react";
import {
  Alert, Box, Button, Card, CardContent, Checkbox, CircularProgress, Dialog, DialogActions,
  DialogContent, DialogTitle, Divider, FormControl, FormControlLabel, IconButton, InputLabel,
  MenuItem, Select, Slider, Stack, TextField, Tooltip, Typography, createTheme, ThemeProvider,
} from "@mui/material";
import { SimpleTreeView } from "@mui/x-tree-view/SimpleTreeView";
import { TreeItem } from "@mui/x-tree-view/TreeItem";
import Crop169Icon from "@mui/icons-material/Crop169";
import Rotate90DegreesCcwIcon from "@mui/icons-material/Rotate90DegreesCcw";
import StraightenIcon from "@mui/icons-material/Straighten";
import ContentCutIcon from "@mui/icons-material/ContentCut";
import AutoFixHighIcon from "@mui/icons-material/AutoFixHigh";
import AddIcon from "@mui/icons-material/Add";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutlineOutlined";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import SaveIcon from "@mui/icons-material/Save";
import FitScreenIcon from "@mui/icons-material/FitScreen";
import ZoomInIcon from "@mui/icons-material/ZoomIn";
import ZoomOutIcon from "@mui/icons-material/ZoomOut";
import CenterFocusStrongIcon from "@mui/icons-material/CenterFocusStrong";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import CloseIcon from "@mui/icons-material/Close";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";
import ChevronLeftIcon from "@mui/icons-material/ChevronLeft";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import KeyboardArrowUpIcon from "@mui/icons-material/KeyboardArrowUp";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import "./style.css";

type Options = Record<string, unknown>;
type PipelineOp = { kind: string; options: Options };
type Schema = { type?: string; control?: string; label?: string; description?: string; min?: number; max?: number; step?: number; options?: unknown[] };
type Helper = { name: string; display_name: string; description?: string; schema?: Record<string, Schema> };
type Metadata = { kind: string; name: string; description?: string; icon?: string; default_options: Options; schema: Record<string, Schema>; helpers?: Helper[] };
type View = { id: number; name: string; pipeline: PipelineOp[] };
type Project = { id: string; name: string; views: View[]; imageUrl: string };
const API = "/api";
async function request<T>(url: string, init?: RequestInit): Promise<T> { const r = await fetch(url, init); if (!r.ok) throw new Error(`Request failed (${r.status})`); return r.status === 204 ? undefined as T : r.json(); }
const icons: Record<string, React.ElementType> = { Crop169: Crop169Icon, Rotate90DegreesCcw: Rotate90DegreesCcwIcon, Straighten: StraightenIcon, ContentCut: ContentCutIcon, AutoFixHigh: AutoFixHighIcon };
const Icon = ({ name }: { name?: string }) => { const C = icons[name ?? ""] ?? TuneIcon; return <C fontSize="small" />; };
function TuneIcon() { return <AutoFixHighIcon fontSize="small" />; }
function opMeta(metas: Metadata[], kind: string) { return metas.find((m) => m.kind === kind); }
function clonePipeline(p: PipelineOp[]) { return p.map((o) => ({ kind: o.kind, options: { ...o.options } })); }

function ProjectTree({ projects, selectedProject, selectedView, onProject, onView, onCreate, onRenameView, onDeleteView, onDeleteProject }: { projects: Project[]; selectedProject: string; selectedView: number | null; onProject: (id: string) => void; onView: (p: string, v: number) => void; onCreate: () => void; onRenameView: (p: Project, v: View) => void; onDeleteView: (p: Project, v: View) => void; onDeleteProject: (p: Project) => void }) {
  return <Box className="project-tree"><SimpleTreeView selectedItems={selectedView === null ? `p:${selectedProject}` : `v:${selectedProject}:${selectedView}`}>
    {projects.map((p) => <TreeItem key={p.id} itemId={`p:${p.id}`} label={<Box className="tree-label" onClick={() => onProject(p.id)}><span className="dot" /><span className="tree-name">{p.name}</span><IconButton className="tree-action" size="small" aria-label={`Delete project ${p.name}`} onClick={e => { e.stopPropagation(); onDeleteProject(p); }}><DeleteOutlineIcon fontSize="small" /></IconButton></Box>}>
      {p.views.map((v) => <TreeItem key={v.id} itemId={`v:${p.id}:${v.id}`} label={<Box className="tree-label view" onClick={() => onView(p.id, v.id)} onDoubleClick={() => onRenameView(p, v)}><span className="view-dot" /><span className="tree-name">{v.name}</span><IconButton className="tree-action" size="small" aria-label={`Rename view ${v.name}`} onClick={e => { e.stopPropagation(); onRenameView(p, v); }}><EditOutlinedIcon fontSize="small" /></IconButton><IconButton className="tree-action" size="small" aria-label={`Delete view ${v.name}`} onClick={e => { e.stopPropagation(); onDeleteView(p, v); }}><DeleteOutlineIcon fontSize="small" /></IconButton></Box>} />)}
      {selectedProject === p.id && <Button size="small" startIcon={<AddIcon />} onClick={onCreate} className="create-view">New view</Button>}
    </TreeItem>)}
  </SimpleTreeView></Box>;
}

function CropOverlay({ imageRef, options, onChange }: { imageRef: React.RefObject<HTMLImageElement | null>; options: Options; onChange: (o: Options) => void }) {
  const box = { x: Number(options.x ?? 0), y: Number(options.y ?? 0), width: Number(options.width ?? 1), height: Number(options.height ?? 1) };
  const start = useRef<{ x: number; y: number } | null>(null);
  const down = (e: ReactPointerEvent) => { e.stopPropagation(); const img = imageRef.current; if (!img) return; const r = img.getBoundingClientRect(); start.current = { x: Math.max(0, Math.min(1, (e.clientX - r.left) / r.width)), y: Math.max(0, Math.min(1, (e.clientY - r.top) / r.height)) }; (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId); };
  const move = (e: ReactPointerEvent) => { if (!start.current || !imageRef.current) return; const r = imageRef.current.getBoundingClientRect(); const x = Math.max(0, Math.min(1, (e.clientX - r.left) / r.width)), y = Math.max(0, Math.min(1, (e.clientY - r.top) / r.height)); onChange({ ...options, x: Math.min(start.current.x, x), y: Math.min(start.current.y, y), width: Math.abs(x - start.current.x), height: Math.abs(y - start.current.y) }); };
  return <Box className="crop-layer" onPointerDown={down} onPointerMove={move} onPointerUp={e => { e.stopPropagation(); start.current = null; }}><Box className="crop-box" style={{ left: `${box.x * 100}%`, top: `${box.y * 100}%`, width: `${box.width * 100}%`, height: `${box.height * 100}%` }} /></Box>;
}
function Preview({ project, view, pipeline, selected, onCrop, activeEditing, onImageDimensions }: { project?: Project; view?: View; pipeline: PipelineOp[]; selected?: Metadata; onCrop: (o: Options) => void; activeEditing: boolean; onImageDimensions: (width: number, height: number) => void }) {
  const img = useRef<HTMLImageElement>(null); const [zoom, setZoom] = useState(1); const [pan, setPan] = useState({ x: 0, y: 0 }); const [preview, setPreview] = useState("");
  const dragging = useRef<{ x: number; y: number; panX: number; panY: number } | null>(null);
  const crop = pipeline.find((o) => o.kind === "crop");
  useEffect(() => { if (!project || !view || !activeEditing) return; const timer = setTimeout(() => { fetch(`${API}/projects/${encodeURIComponent(project.id)}/views/${view.id}/preview`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ pipeline }) }).then(r => r.ok ? r.blob() : Promise.reject(new Error("Preview failed"))).then(b => { const u = URL.createObjectURL(b); setPreview(old => { if (old) URL.revokeObjectURL(old); return u; }); }).catch(() => setPreview("")); }, 350); return () => clearTimeout(timer); }, [project?.id, view?.id, JSON.stringify(pipeline), activeEditing]);
  useEffect(() => { if (!activeEditing) setPreview(""); }, [activeEditing, view?.id]);
  useEffect(() => { setZoom(1); setPan({ x: 0, y: 0 }); }, [project?.id, view?.id]);
  const src = preview || project?.imageUrl;
  const reset = (nextZoom = 1) => { setZoom(nextZoom); setPan({ x: 0, y: 0 }); };
  const down = (e: ReactPointerEvent<HTMLDivElement>) => {
    if (e.button !== 0) return;
    dragging.current = { x: e.clientX, y: e.clientY, panX: pan.x, panY: pan.y };
    e.currentTarget.setPointerCapture(e.pointerId);
  };
  const move = (e: ReactPointerEvent<HTMLDivElement>) => {
    if (!dragging.current) return;
    const d = dragging.current;
    setPan({ x: d.panX + e.clientX - d.x, y: d.panY + e.clientY - d.y });
  };
  const up = (e: ReactPointerEvent<HTMLDivElement>) => {
    if (e.currentTarget.hasPointerCapture(e.pointerId)) e.currentTarget.releasePointerCapture(e.pointerId);
    dragging.current = null;
  };
  const wheel = (e: React.WheelEvent<HTMLDivElement>) => {
    e.preventDefault();
    setZoom(z => Math.max(.25, Math.min(4, z + (e.deltaY < 0 ? .1 : -.1))));
  };
  return <Box className="preview"><Box className="preview-toolbar"><Tooltip title="Fit and center"><IconButton onClick={() => reset()}><FitScreenIcon /></IconButton></Tooltip><Tooltip title="Actual size and center"><IconButton onClick={() => reset(1.5)}><CenterFocusStrongIcon /></IconButton></Tooltip><IconButton aria-label="Zoom out" onClick={() => setZoom(z => Math.max(.25, z - .25))}><ZoomOutIcon /></IconButton><Typography>{Math.round(zoom * 100)}%</Typography><IconButton aria-label="Zoom in" onClick={() => setZoom(z => Math.min(4, z + .25))}><ZoomInIcon /></IconButton></Box>{src ? <Box className="image-stage" onPointerDown={down} onPointerMove={move} onPointerUp={up} onPointerCancel={up} onWheel={wheel} style={{ transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})` }}><img ref={img} src={src} alt={project?.name ?? "Document"} draggable={false} onLoad={e => { const image = e.currentTarget; onImageDimensions(image.naturalWidth, image.naturalHeight); }} />{selected?.kind === "crop" && crop && activeEditing && <CropOverlay imageRef={img} options={crop.options} onChange={onCrop} />}</Box> : <Typography color="text.secondary">Select a view to begin editing</Typography>}</Box>;
}
function Parameters({ meta, op, naturalWidth, naturalHeight, onChange }: { meta?: Metadata; op?: PipelineOp; naturalWidth: number; naturalHeight: number; onChange: (o: Options) => void }) {
  if (!meta || !op) return <Box className="parameters"><Typography variant="h6">Operation parameters</Typography><Typography color="text.secondary">Select an operation in the pipeline.</Typography></Box>;
  return <Box className="parameters"><Typography variant="h6">{meta.name} parameters</Typography><Typography className="description">{meta.description}</Typography><Stack spacing={2}>{Object.entries(meta.schema ?? {}).map(([key, schema]) => { const value = op.options[key] ?? meta.default_options[key] ?? ""; const label = schema.label ?? key; const step = op.kind === "crop" && naturalWidth > 0 && naturalHeight > 0 ? (key === "x" || key === "width" ? 1 / naturalWidth : key === "y" || key === "height" ? 1 / naturalHeight : schema.step) : schema.step; if (schema.control === "checkbox") return <FormControlLabel key={key} control={<Checkbox checked={Boolean(value)} onChange={e => onChange({ ...op.options, [key]: e.target.checked })} />} label={label} />; if (schema.control === "dropdown") return <FormControl fullWidth size="small" key={key}><InputLabel>{label}</InputLabel><Select value={String(value)} label={label} onChange={e => onChange({ ...op.options, [key]: e.target.value })}>{(schema.options ?? []).map(x => <MenuItem key={String(x)} value={String(x)}>{String(x)}</MenuItem>)}</Select></FormControl>; if (schema.control === "slider") return <Box key={key}><Typography variant="body2">{label}: {String(value)}</Typography><Slider value={Number(value)} min={schema.min} max={schema.max} step={step} onChange={(_, v) => onChange({ ...op.options, [key]: v })} /><TextField size="small" type="number" value={value} onChange={e => onChange({ ...op.options, [key]: Number(e.target.value) })} inputProps={{ min: schema.min, max: schema.max, step }} /></Box>; return <TextField key={key} fullWidth size="small" type="number" label={label} value={value} onChange={e => onChange({ ...op.options, [key]: Number(e.target.value) })} inputProps={{ min: schema.min, max: schema.max, step }} helperText={schema.description} />; })}</Stack></Box>;
}
function Pipeline({ pipeline, metas, selected, onSelect, onChange, onAdd, onRemove, onMove, onHelper }: { pipeline: PipelineOp[]; metas: Metadata[]; selected: number; onSelect: (i: number) => void; onChange: (p: PipelineOp[]) => void; onAdd: (kind: string) => void; onRemove: (i: number) => void; onMove: (i: number, d: number) => void; onHelper: (i: number, h: Helper) => void }) {
  const [adding, setAdding] = useState(false);
  return <Box className="pipeline"><Box className="panel-heading"><Typography variant="h6">Pipeline</Typography><Typography variant="caption">{pipeline.length} operations</Typography></Box><Stack spacing={1}>{pipeline.map((op, i) => { const m = opMeta(metas, op.kind); return <Card key={`${op.kind}-${i}`} className={`operation ${selected === i ? "selected" : ""}`} onClick={() => onSelect(i)}><CardContent><Box className="operation-top"><Icon name={m?.icon} /><Box flex={1}><Typography fontWeight={600}>{m?.name ?? op.kind}</Typography><Typography variant="caption" color="text.secondary">{m?.description}</Typography></Box><IconButton size="small" onClick={e => { e.stopPropagation(); onMove(i, -1); }} disabled={i === 0}><ExpandLessIcon /></IconButton><IconButton size="small" onClick={e => { e.stopPropagation(); onMove(i, 1); }} disabled={i === pipeline.length - 1}><ExpandMoreIcon /></IconButton><IconButton size="small" onClick={e => { e.stopPropagation(); onRemove(i); }}><DeleteOutlineIcon /></IconButton></Box>{m?.helpers?.length ? <Box className="helpers">{m.helpers.map(h => <Button key={h.name} size="small" startIcon={<AutoFixHighIcon />} onClick={e => { e.stopPropagation(); onHelper(i, h); }}>{h.display_name}</Button>)}</Box> : null}</CardContent></Card> })}</Stack><Button fullWidth variant="outlined" startIcon={<AddIcon />} onClick={() => setAdding(v => !v)} className="add-operation">Add operation</Button>{adding && <Card className="operation-menu"><CardContent>{metas.map(m => <Button key={m.kind} fullWidth startIcon={<Icon name={m.icon} />} onClick={() => { onAdd(m.kind); setAdding(false); }}>{m.name}</Button>)}</CardContent></Card>}</Box>;
}
function ResizeHandle({ axis, onResize }: { axis: "horizontal" | "vertical"; onResize: (delta: number) => void }) {
  const start = useRef(0);
  const down = (e: ReactPointerEvent<HTMLDivElement>) => { start.current = axis === "horizontal" ? e.clientX : e.clientY; e.currentTarget.setPointerCapture(e.pointerId); };
  const move = (e: ReactPointerEvent<HTMLDivElement>) => { if (!e.currentTarget.hasPointerCapture(e.pointerId)) return; const current = axis === "horizontal" ? e.clientX : e.clientY; onResize(current - start.current); start.current = current; };
  return <Box className={`resize-handle ${axis}`} onPointerDown={down} onPointerMove={move} onPointerUp={e => e.currentTarget.releasePointerCapture(e.pointerId)} />;
}
function FoldButton({ label, direction, onClick }: { label: string; direction: "left" | "right" | "up" | "down"; onClick: () => void }) {
  const C = direction === "left" ? ChevronLeftIcon : direction === "right" ? ChevronRightIcon : direction === "up" ? KeyboardArrowUpIcon : KeyboardArrowDownIcon;
  return <IconButton className="fold-button" size="small" aria-label={label} onClick={onClick}><C /></IconButton>;
}
function App() {
  const [metas, setMetas] = useState<Metadata[]>([]), [projects, setProjects] = useState<Project[]>([]), [projectId, setProjectId] = useState(""), [viewId, setViewId] = useState<number | null>(null), [pipeline, setPipeline] = useState<PipelineOp[]>([]), [selected, setSelected] = useState(0), [saving, setSaving] = useState(false), [error, setError] = useState(""), [helper, setHelper] = useState<{ index: number; value: Helper } | null>(null), [helperOptions, setHelperOptions] = useState<Options>({}), [loading, setLoading] = useState(false), [renameTarget, setRenameTarget] = useState<{ project: Project; view: View } | null>(null), [renameName, setRenameName] = useState(""), [deleteTarget, setDeleteTarget] = useState<{ project: Project; view?: View } | null>(null);
  const [leftWidth, setLeftWidth] = useState(250), [rightWidth, setRightWidth] = useState(340), [splitRatio, setSplitRatio] = useState(.68);
  const [leftFolded, setLeftFolded] = useState(false), [rightFolded, setRightFolded] = useState(false), [parametersFolded, setParametersFolded] = useState(false), [activeEditing, setActiveEditing] = useState(false), [naturalDimensions, setNaturalDimensions] = useState({ width: 0, height: 0 });
  const project = projects.find(p => p.id === projectId), view = project?.views.find(v => v.id === viewId), selectedMeta = opMeta(metas, pipeline[selected]?.kind);
  useEffect(() => { Promise.all([request<Metadata[]>(`${API}/operations`), request<string[]>(`${API}/projects`)]).then(([m, ids]) => { setMetas(m); const ps = ids.map(id => ({ id, name: id, views: [], imageUrl: `${API}/projects/${encodeURIComponent(id)}/image` })); setProjects(ps); if (ps[0]) setProjectId(ps[0].id); }).catch(e => setError(e.message)); }, []);
  useEffect(() => { if (!projectId) return; request<View[]>(`${API}/projects/${encodeURIComponent(projectId)}/views`).then(vs => setProjects(ps => ps.map(p => p.id === projectId ? { ...p, views: vs } : p))).catch(e => setError(e.message)); }, [projectId]);
  useEffect(() => { if (view) { setPipeline(clonePipeline(view.pipeline)); setSelected(0); setActiveEditing(false); } }, [view?.id]);
  const selectView = (p: string, v: number) => { setProjectId(p); setViewId(v); setActiveEditing(false); };
  const add = (kind: string) => { const m = opMeta(metas, kind); if (!m) return; const next = [...pipeline, { kind, options: { ...m.default_options } }]; if (kind === "crop") next.unshift(next.pop()!); setPipeline(next); setSelected(kind === "crop" ? 0 : next.length - 1); setActiveEditing(true); };
  const remove = (i: number) => { setPipeline(p => p.filter((_, n) => n !== i)); setActiveEditing(true); };
  const move = (i: number, d: number) => { const j = i + d; if (j < 0 || j >= pipeline.length || (pipeline[i].kind === "crop" && j !== 0) || (pipeline[j].kind === "crop" && i !== 0)) return; const n = [...pipeline]; [n[i], n[j]] = [n[j], n[i]]; setPipeline(n); setSelected(j); setActiveEditing(true); };
  const save = async () => { if (!project || !view) return; setSaving(true); try { const updated = await request<View>(`${API}/projects/${encodeURIComponent(project.id)}/views/${view.id}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: view.name, pipeline }) }); setProjects(ps => ps.map(p => p.id === project.id ? { ...p, views: p.views.map(v => v.id === view.id ? updated : v) } : p)); } catch (e) { setError((e as Error).message); } finally { setSaving(false); } };
  const helperRun = async () => { if (!project || !view || !helper) return; setLoading(true); try { const r = await request<{ options?: Options; suggestion?: Options }>(`${API}/projects/${encodeURIComponent(project.id)}/views/${view.id}/auto/${helper.value.name}`, { method: "POST", headers: Object.keys(helperOptions).length ? { "Content-Type": "application/json" } : undefined, body: Object.keys(helperOptions).length ? JSON.stringify(helperOptions) : undefined }); const options = r.options ?? r.suggestion; if (options) setPipeline(p => p.map((o, i) => i === helper.index ? { ...o, options: { ...o.options, ...options } } : o)); setHelper(null); } catch (e) { setError((e as Error).message); } finally { setLoading(false); } };
  const createView = async () => { if (!project) return; try { const v = await request<View>(`${API}/projects/${encodeURIComponent(project.id)}/views`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: `View ${project.views.length + 1}`, pipeline: [] }) }); setProjects(ps => ps.map(p => p.id === project.id ? { ...p, views: [...p.views, v] } : p)); setViewId(v.id); } catch (e) { setError((e as Error).message); } };
  const beginRename = (p: Project, v: View) => { setRenameTarget({ project: p, view: v }); setRenameName(v.name); };
  const renameView = async () => { if (!renameTarget || !renameName.trim()) return; const { project: p, view: v } = renameTarget; try { const updated = await request<View>(`${API}/projects/${encodeURIComponent(p.id)}/views/${v.id}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: renameName.trim(), pipeline: v.pipeline }) }); setProjects(ps => ps.map(x => x.id === p.id ? { ...x, views: x.views.map(y => y.id === v.id ? updated : y) } : x)); setRenameTarget(null); } catch (e) { setError((e as Error).message); } };
  const deleteConfirmed = async () => { if (!deleteTarget) return; const { project: p, view: v } = deleteTarget; try { await request<void>(v ? `${API}/projects/${encodeURIComponent(p.id)}/views/${v.id}` : `${API}/projects/${encodeURIComponent(p.id)}`, { method: "DELETE" }); if (v) { setProjects(ps => ps.map(x => x.id === p.id ? { ...x, views: x.views.filter(y => y.id !== v.id) } : x)); if (viewId === v.id) setViewId(null); } else { setProjects(ps => ps.filter(x => x.id !== p.id)); if (projectId === p.id) { setProjectId(""); setViewId(null); } } setDeleteTarget(null); } catch (e) { setError((e as Error).message); } };
  const upload = async (e: ChangeEvent<HTMLInputElement>) => { const file = e.target.files?.[0]; if (!file) return; const fd = new FormData(); fd.append("image", file); try { const p = await request<Project>(`${API}/projects`, { method: "POST", body: fd }); setProjects(ps => [...ps, p]); setProjectId(p.id); } catch (x) { setError((x as Error).message); } };
    return <ThemeProvider theme={theme}><Box className="app">
    <aside className={`left ${leftFolded ? "folded" : ""}`} style={{ width: leftFolded ? 30 : leftWidth }}>
      <Box className="pane-heading"><Typography className="brand">DOCUMENT<span>LAB</span></Typography><FoldButton label={leftFolded ? "Expand project sidebar" : "Collapse project sidebar"} direction={leftFolded ? "right" : "left"} onClick={() => setLeftFolded(v => !v)} /></Box>
      <Stack direction="row" justifyContent="space-between" alignItems="center"><Typography className="section-title">Projects</Typography><Button component="label" size="small" startIcon={<UploadFileIcon />}>Import<input hidden type="file" accept="image/*" onChange={upload} /></Button></Stack>
      <ProjectTree projects={projects} selectedProject={projectId} selectedView={viewId} onProject={p => { setProjectId(p); setViewId(null); }} onView={selectView} onCreate={createView} onRenameView={beginRename} onDeleteView={(p, v) => setDeleteTarget({ project: p, view: v })} onDeleteProject={p => setDeleteTarget({ project: p })} />
    </aside>
    {!leftFolded && <ResizeHandle axis="horizontal" onResize={d => setLeftWidth(w => Math.max(180, Math.min(420, w + d)))} />}
    <main className="main">
      {error && <Alert severity="error" onClose={() => setError("")}>{error}</Alert>}
      <Box className="center" style={{ gridTemplateRows: parametersFolded ? "minmax(0, 1fr) 0px 0px" : `${splitRatio * 100}% auto ${ (1 - splitRatio) * 100}%` }}>
        <Box className="center-pane"><Preview project={project} view={view} pipeline={pipeline} selected={selectedMeta} activeEditing={activeEditing} onImageDimensions={(width, height) => setNaturalDimensions({ width, height })} onCrop={o => { setPipeline(p => p.map((x, i) => i === selected ? { ...x, options: o } : x)); setActiveEditing(true); }} /></Box>
        {!parametersFolded && <ResizeHandle axis="vertical" onResize={d => setSplitRatio(r => Math.max(.2, Math.min(.8, r + d / Math.max(1, document.querySelector(".center")?.clientHeight ?? 1))))} />}
        <Box className={`center-pane ${parametersFolded ? "folded-pane" : ""}`}>{parametersFolded ? <FoldButton label="Expand parameters" direction="up" onClick={() => setParametersFolded(false)} /> : <><Box className="pane-corner"><FoldButton label="Collapse parameters" direction="down" onClick={() => setParametersFolded(true)} /></Box><Parameters meta={selectedMeta} op={pipeline[selected]} naturalWidth={naturalDimensions.width} naturalHeight={naturalDimensions.height} onChange={o => { setPipeline(p => p.map((x, i) => i === selected ? { ...x, options: o } : x)); setActiveEditing(true); }} /></>}</Box>
      </Box>
    </main>
    {!rightFolded && <ResizeHandle axis="horizontal" onResize={d => setRightWidth(w => Math.max(240, Math.min(500, w - d)))} />}
    <aside className={`right ${rightFolded ? "folded" : ""}`} style={{ width: rightFolded ? 30 : rightWidth }}>
      <Box className="pane-heading"><Typography className="section-title">Pipeline</Typography><FoldButton label={rightFolded ? "Expand pipeline sidebar" : "Collapse pipeline sidebar"} direction={rightFolded ? "left" : "right"} onClick={() => setRightFolded(v => !v)} /></Box>
      {!rightFolded && <><Button fullWidth variant="contained" startIcon={<SaveIcon />} disabled={!view || saving} onClick={save} className="save-pipeline">{saving ? "Saving…" : "Save pipeline"}</Button><Pipeline pipeline={pipeline} metas={metas} selected={selected} onSelect={setSelected} onChange={setPipeline} onAdd={add} onRemove={remove} onMove={move} onHelper={(i, h) => { if (Object.keys(h.schema ?? {}).length) { setHelper({ index: i, value: h }); setHelperOptions({}); } else { setHelper({ index: i, value: h }); setHelperOptions({}); setTimeout(helperRun, 0); } }} /></>}
    </aside>
    <Dialog open={Boolean(renameTarget)} onClose={() => setRenameTarget(null)}><DialogTitle>Rename view</DialogTitle><DialogContent><TextField autoFocus fullWidth label="View name" value={renameName} onChange={e => setRenameName(e.target.value)} onKeyDown={e => { if (e.key === "Enter") renameView(); }} /></DialogContent><DialogActions><Button onClick={() => setRenameTarget(null)}>Cancel</Button><Button variant="contained" onClick={renameView} disabled={!renameName.trim()}>Rename</Button></DialogActions></Dialog><Dialog open={Boolean(deleteTarget)} onClose={() => setDeleteTarget(null)}><DialogTitle>Delete {deleteTarget?.view ? "view" : "project"}?</DialogTitle><DialogContent><Typography>This action cannot be undone.</Typography></DialogContent><DialogActions><Button onClick={() => setDeleteTarget(null)}>Cancel</Button><Button color="error" variant="contained" onClick={deleteConfirmed}>Delete</Button></DialogActions></Dialog><Dialog open={Boolean(helper?.value.schema && Object.keys(helper.value.schema).length)} onClose={() => setHelper(null)}><DialogTitle>{helper?.value.display_name}</DialogTitle><DialogContent><Stack spacing={2} sx={{ pt: 1 }}>{helper?.value.schema && Object.entries(helper.value.schema).map(([k, s]) => <TextField key={k} label={s.label ?? k} type="number" value={helperOptions[k] ?? ""} onChange={e => setHelperOptions(o => ({ ...o, [k]: Number(e.target.value) }))} />)}</Stack></DialogContent><DialogActions><Button onClick={() => setHelper(null)} startIcon={<CloseIcon />}>Cancel</Button><Button onClick={helperRun} variant="contained" startIcon={loading ? <CircularProgress size={16} /> : <PlayArrowIcon />} disabled={loading}>Run</Button></DialogActions></Dialog>
  </Box></ThemeProvider>;
}
const theme = createTheme({ palette: { mode: "dark", primary: { main: "#c6f36b" }, background: { default: "#101317", paper: "#191e24" } }, typography: { fontFamily: "Inter, system-ui, sans-serif" }, shape: { borderRadius: 10 } });
createRoot(document.getElementById("app")!).render(<App />);
