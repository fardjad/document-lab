import { useEffect, useState } from "react";
import {
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Stack,
  TextField,
  Alert,
  Typography,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import SaveIcon from "@mui/icons-material/Save";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import { API, request } from "../../shared/api";
import type {
  Metadata,
  Options,
  View,
  Helper,
  PipelineOp,
  Project,
} from "../../entities";
import { Parameters, Pipeline, opMeta } from "./PipelineControls";
import { usePipeline } from "./usePipeline";
import { Preview } from "./Preview";
import { FoldButton, ResizeHandle } from "../../shared/ui";

export function ViewWorkspace({
  project,
  view,
  error,
  setError,
  updateView,
}: {
  project?: Project;
  view?: View;
  error: string;
  setError: (message: string) => void;
  updateView: (project: Project, view: View, updated: View) => Promise<void>;
}) {
  const [metas, setMetas] = useState<Metadata[]>([]);
  const [saving, setSaving] = useState(false);
  const [helper, setHelper] = useState<{ index: number; value: Helper } | null>(
    null,
  );
  const [helperOptions, setHelperOptions] = useState<Options>({});
  const [loading, setLoading] = useState(false);
  const [rightWidth, setRightWidth] = useState(340);
  const [splitRatio, setSplitRatio] = useState(0.68);
  const [rightFolded, setRightFolded] = useState(false);
  const [parametersFolded, setParametersFolded] = useState(false);
  const {
    pipeline,
    setPipeline,
    selectedOperation,
    setSelectedOperation,
    activeEditing,
    setActiveEditing,
    add,
    remove,
    move,
    change,
  } = usePipeline(metas, view);
  const selectedMeta =
    selectedOperation === null
      ? undefined
      : opMeta(metas, pipeline[selectedOperation]?.kind);
  const resizeParameters = (delta: number) => {
    if (parametersFolded && delta >= 0) return;
    const height = Math.max(1, document.querySelector(".center")?.clientHeight ?? 1);
    setSplitRatio((ratio) => {
      const next = Math.max(0, Math.min(1, ratio + delta / height));
      setParametersFolded(next === 1);
      return next;
    });
  };
  const resizeRight = (delta: number) => {
    if (rightFolded && delta >= 0) return;
    setRightWidth((width) => {
      const next = Math.max(0, Math.min(500, width - delta));
      setRightFolded(next === 0);
      return next;
    });
  };
  const toggleParametersFold = () => {
    if (parametersFolded) {
      if (splitRatio === 1) setSplitRatio(0.68);
      setParametersFolded(false);
      return;
    }
    setParametersFolded(true);
  };
  const toggleRightFold = () => {
    if (rightFolded) {
      if (rightWidth === 0) setRightWidth(340);
      setRightFolded(false);
      return;
    }
    setRightFolded(true);
  };

  useEffect(() => {
    request<Metadata[]>(`${API}/operations`)
      .then(setMetas)
      .catch((e) => setError(e.message));
  }, [setError]);
  const save = async () => {
    if (!project || !view) return;
    setSaving(true);
    try {
      const updated = await request<View>(
        `${API}/projects/${encodeURIComponent(project.id)}/views/${view.id}`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name: view.name, pipeline }),
        },
      );
      await updateView(project, view, updated);
      setActiveEditing(false);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };
  const helperRun = async () => {
    if (!project || !view || !helper) return;
    setLoading(true);
    try {
      const r = await request<{ options?: Options; suggestion?: Options }>(
        `${API}/projects/${encodeURIComponent(project.id)}/views/${view.id}/helpers/${helper.value.name}`,
        {
          method: "POST",
          headers: Object.keys(helperOptions).length
            ? { "Content-Type": "application/json" }
            : undefined,
          body: Object.keys(helperOptions).length
            ? JSON.stringify(helperOptions)
            : undefined,
        },
      );
      const options = r.options ?? r.suggestion;
      if (options) {
        setPipeline((p) =>
          p.map((o, i) =>
            i === helper.index
              ? { ...o, options: { ...o.options, ...options } }
              : o,
          ),
        );
        setActiveEditing(true);
      }
      setHelper(null);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };
  return (
    <>
      <Box component="main" className="main" sx={{ display: "flex", flex: "1 1 auto", flexDirection: "column", minWidth: 0, minHeight: 0, overflow: "hidden" }}>
        {error && (
          <Alert severity="error" onClose={() => setError("")}>
            {error}
          </Alert>
        )}
        <Box
          className="center"
          sx={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr)", flex: "1 1 auto", minWidth: 0, minHeight: 0, overflow: "hidden" }}
          style={{
            gridTemplateRows: parametersFolded
              ? "minmax(0, 1fr) 4px 0px"
              : `${splitRatio * 100}% 4px ${(1 - splitRatio) * 100}%`,
          }}
        >
          <Box className="center-pane" sx={{ minWidth: 0, minHeight: 0, overflow: "hidden", position: "relative", background: "#151a1f" }}>
            <Preview
              project={project}
              view={view}
              pipeline={pipeline}
              activeEditing={activeEditing}
            />
          </Box>
          <ResizeHandle
            axis="vertical"
            onResize={resizeParameters}
          >
            <Box
              sx={{
                position: "absolute",
                inset: "-6px 0",
                "&:hover .parameter-splitter-button": { opacity: 1 },
              }}
            >
              <FoldButton
                label={parametersFolded ? "Expand parameters" : "Collapse parameters"}
                direction={parametersFolded ? "up" : "down"}
                splitter
                onClick={toggleParametersFold}
              />
            </Box>
          </ResizeHandle>
          <Box
            className={`center-pane ${parametersFolded ? "folded-pane" : ""}`}
            sx={{
              minWidth: 0,
              minHeight: 0,
              overflow: parametersFolded ? "visible" : "hidden",
              position: "relative",
              background: "#20272f",
              boxShadow: "inset 0 1px #3b4651",
              ...(parametersFolded && {
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }),
            }}
          >
            {parametersFolded ? null : (
              <>
                <Parameters
                  meta={selectedMeta}
                  op={
                    selectedOperation === null
                      ? undefined
                      : pipeline[selectedOperation]
                  }
                  onChange={(o) => {
                    if (selectedOperation === null) return;
                    setPipeline((p) =>
                      p.map((x, i) =>
                        i === selectedOperation ? { ...x, options: o } : x,
                      ),
                    );
                    setActiveEditing(true);
                  }}
                />
              </>
            )}
          </Box>
        </Box>
      </Box>
      <ResizeHandle
          axis="horizontal"
          onResize={resizeRight}
        >
          <Box sx={{ position: "absolute", inset: "0 -6px", "&:hover .side-splitter-button": { opacity: 1 } }}>
            <FoldButton
              label={rightFolded ? "Expand pipeline sidebar" : "Collapse pipeline sidebar"}
              direction={rightFolded ? "left" : "right"}
              splitter
              onClick={toggleRightFold}
            />
          </Box>
        </ResizeHandle>
      <aside
        className={`right ${rightFolded ? "folded" : ""}`}
        style={{ width: rightFolded ? 0 : rightWidth, backgroundColor: "#20272f" }}
        sx={{
          display: "flex", flex: "0 0 auto", flexDirection: "column", minWidth: 0, minHeight: 0,
          overflow: "hidden", background: "#20272f", borderLeft: "1px solid #46515c",
          boxShadow: "-1px 0 0 rgba(255, 255, 255, 0.04)",
          ...(rightFolded && {
            width: "0 !important",
            border: 0,
            boxShadow: "none",
          }),
        }}
      >
        <Box className="pane-heading" sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", minHeight: 56, p: "8px 12px", background: "#252d36", borderBottom: "1px solid #3b4651" }}>
          {rightFolded ? null : (
            <>
              <Typography className="section-title" sx={{ fontWeight: 700 }}>Pipeline</Typography>
            </>
          )}
        </Box>
        {!rightFolded && (
          <>
            <Button
              fullWidth
              variant="contained"
              startIcon={<SaveIcon />}
              disabled={!view || saving}
              onClick={save}
              className="save-pipeline"
              sx={{ m: "12px 12px 12px", width: "calc(100% - 24px)" }}
            >
              {saving ? "Saving…" : "Save pipeline"}
            </Button>
            <Pipeline
              pipeline={pipeline}
              metas={metas}
              selected={selectedOperation}
              onSelect={setSelectedOperation}
              onChange={change}
              onAdd={add}
              onRemove={remove}
              onMove={move}
              onHelper={(i, h) => {
                if (Object.keys(h.schema ?? {}).length) {
                  setHelper({ index: i, value: h });
                  setHelperOptions({});
                } else {
                  setHelper({ index: i, value: h });
                  setHelperOptions({});
                  setTimeout(helperRun, 0);
                }
              }}
            />
          </>
        )}
      </aside>
      <Dialog
        open={Boolean(
          helper?.value.schema && Object.keys(helper.value.schema).length,
        )}
        onClose={() => setHelper(null)}
      >
        <DialogTitle>{helper?.value.display_name}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1 }}>
            {helper?.value.schema &&
              Object.entries(helper.value.schema).map(([k, s]) => (
                <TextField
                  key={k}
                  label={s.label ?? k}
                  type="number"
                  value={helperOptions[k] ?? ""}
                  onChange={(e) =>
                    setHelperOptions((o) => ({
                      ...o,
                      [k]: Number(e.target.value),
                    }))
                  }
                />
              ))}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setHelper(null)} startIcon={<CloseIcon />}>
            Cancel
          </Button>
          <Button
            onClick={helperRun}
            variant="contained"
            startIcon={
              loading ? <CircularProgress size={16} /> : <PlayArrowIcon />
            }
            disabled={loading}
          >
            Run
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
