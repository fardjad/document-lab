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
import { Parameters, Pipeline, opMeta } from "../pipeline/PipelineControls";
import { usePipeline } from "../pipeline/usePipeline";
import { Preview } from "../pipeline/Preview";
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
              ? "minmax(0, 1fr) 0px 32px"
              : `${splitRatio * 100}% auto ${(1 - splitRatio) * 100}%`,
          }}
        >
          <Box className="center-pane" sx={{ minWidth: 0, minHeight: 0, overflow: "hidden", position: "relative" }}>
            <Preview
              project={project}
              view={view}
              pipeline={pipeline}
              activeEditing={activeEditing}
            />
          </Box>
          {!parametersFolded && (
            <ResizeHandle
              axis="vertical"
              onResize={(d) =>
                setSplitRatio((r) =>
                  Math.max(
                    0.2,
                    Math.min(
                      0.8,
                      r +
                        d /
                          Math.max(
                            1,
                            document.querySelector(".center")?.clientHeight ??
                              1,
                          ),
                    ),
                  ),
                )
              }
            />
          )}
          <Box
            className={`center-pane ${parametersFolded ? "folded-pane" : ""}`}
            sx={{
              minWidth: 0,
              minHeight: 0,
              overflow: parametersFolded ? "visible" : "hidden",
              position: "relative",
              ...(parametersFolded && {
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }),
            }}
          >
            {parametersFolded ? (
              <FoldButton
                label="Expand parameters"
                direction="up"
                onClick={() => setParametersFolded(false)}
              />
            ) : (
              <>
                <Box className="pane-corner" sx={{ position: "absolute", top: 4, right: 4, zIndex: 2 }}>
                  <FoldButton
                    label="Collapse parameters"
                    direction="down"
                    onClick={() => setParametersFolded(true)}
                  />
                </Box>
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
      {!rightFolded && (
        <ResizeHandle
          axis="horizontal"
          onResize={(d) =>
            setRightWidth((w) => Math.max(240, Math.min(500, w - d)))
          }
        />
      )}
      <aside
        className={`right ${rightFolded ? "folded" : ""}`}
        style={{ width: rightFolded ? 30 : rightWidth }}
        sx={{
          display: "flex", flex: "0 0 auto", flexDirection: "column", minWidth: 0, minHeight: 0,
          overflow: "hidden", background: "#191e24", borderLeft: "1px solid #303840",
          ...(rightFolded && { width: "30px !important", "& .pane-heading": { justifyContent: "center", p: "8px 0" }, "& .fold-button": { width: 30, height: 36, p: "4px 0" } }),
        }}
      >
        <Box className="pane-heading" sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", minHeight: 56, p: "8px 12px" }}>
          {rightFolded ? (
            <FoldButton
              label="Expand pipeline sidebar"
              direction="left"
              onClick={() => setRightFolded(false)}
            />
          ) : (
            <>
              <Typography className="section-title" sx={{ fontWeight: 700 }}>Pipeline</Typography>
              <FoldButton
                label="Collapse pipeline sidebar"
                direction="right"
                onClick={() => setRightFolded(true)}
              />
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
              sx={{ m: "0 12px 12px", width: "calc(100% - 24px)" }}
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
