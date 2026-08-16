import { useCallback, useEffect, useMemo, useState } from "react";
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
  const [helper, setHelper] = useState<{ index: number; value: Helper } | null>(
    null,
  );
  const [helperOptions, setHelperOptions] = useState<Options>({});
  const [loading, setLoading] = useState(false);
  const [rightWidth, setRightWidth] = useState(340);
  const [splitRatio, setSplitRatio] = useState(0.68);
  const [rightFolded, setRightFolded] = useState(false);
  const [parametersFolded, setParametersFolded] = useState(false);
  const [parameterDraft, setParameterDraft] = useState<Options>();
  const {
    pipeline,
    setPipeline,
    selectedOperation,
    setSelectedOperation,
    activeEditing,
    setActiveEditing,
    pipelineReady,
    add,
    remove,
    move,
    change,
  } = usePipeline(metas, view);
  const selectedMeta =
    selectedOperation === null
      ? undefined
      : opMeta(metas, pipeline[selectedOperation]?.kind);
  const previewPipeline = useMemo(
    () =>
      selectedOperation === null || !parameterDraft
        ? pipeline
        : pipeline.map((operation, index) =>
            index === selectedOperation
              ? { ...operation, options: parameterDraft }
              : operation,
          ),
    [pipeline, selectedOperation, parameterDraft],
  );
  const updateParameterDraft = useCallback((options?: Options) => {
    setParameterDraft(options);
  }, []);
  const persistedPipeline = useMemo(
    () =>
      pipeline.map(({ kind, options, enabled }) =>
        enabled === false ? { kind, options, enabled } : { kind, options },
      ),
    [pipeline],
  );
  const storedPipeline = useMemo(
    () =>
      (view?.pipeline ?? []).map(({ kind, options, enabled }) =>
        enabled === false ? { kind, options, enabled } : { kind, options },
      ),
    [view?.pipeline],
  );
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
      .then((operations) =>
        setMetas(
          operations.map((operation) => ({
            ...operation,
            schema: Object.fromEntries(
              Object.entries(operation.schema).map(([name, schema]) => [
                name,
                {
                  ...schema,
                  label: schema.label ?? schema.title,
                  control: schema.control ?? schema["x-hint-ui-control"],
                  min: schema.min ?? schema.minimum,
                  max: schema.max ?? schema.maximum,
                  step: schema.step ?? schema["x-hint-ui-step"],
                },
              ]),
            ),
          })),
        ),
      )
      .catch((e) => setError(e.message));
  }, [setError]);
  useEffect(() => {
    if (!project || !view || !pipelineReady) return;
    if (JSON.stringify(persistedPipeline) === JSON.stringify(storedPipeline)) return;

    setActiveEditing(true);
    const timer = window.setTimeout(() => {
      request<View>(
        `${API}/projects/${encodeURIComponent(project.id)}/views/${view.id}`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name: view.name, pipeline: persistedPipeline }),
        },
      )
        .then((updated) => updateView(project, view, updated))
        .then(() => setActiveEditing(false))
        .catch((e) => setError(e.message));
    }, 300);
    return () => window.clearTimeout(timer);
  }, [
    project?.id,
    view?.id,
    view?.name,
    persistedPipeline,
    storedPipeline,
    updateView,
    setActiveEditing,
    setError,
    pipelineReady,
  ]);
  const helperRun = async (
    selectedHelper = helper,
    options = helperOptions,
  ) => {
    if (!project || !view || !selectedHelper) return;
    setLoading(true);
    try {
      const r = await request<{ options?: Options; suggestion?: Options }>(
        `${API}/projects/${encodeURIComponent(project.id)}/views/${view.id}/pipeline/${selectedHelper.index}/helpers/${selectedHelper.value.name}`,
        {
          method: "POST",
          headers: Object.keys(options).length
            ? { "Content-Type": "application/json" }
            : undefined,
          body: Object.keys(options).length
            ? JSON.stringify(options)
            : undefined,
        },
      );
      const updatedOptions = r.options ?? r.suggestion;
      setHelper(null);
      return updatedOptions;
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
              pipeline={previewPipeline}
              activeEditing={activeEditing || Boolean(parameterDraft)}
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
                  onHelper={async (selectedHelper) => {
                    if (selectedOperation === null || !selectedMeta) return;
                    if (Object.keys(selectedHelper.schema ?? {}).length) {
                      setHelper({ index: selectedOperation, value: selectedHelper });
                      setHelperOptions({});
                      return;
                    } else {
                      return helperRun(
                        { index: selectedOperation, value: selectedHelper },
                        {},
                      );
                    }
                  }}
                  onDraftChange={updateParameterDraft}
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
            <Pipeline
              pipeline={pipeline}
              metas={metas}
              selected={selectedOperation}
              onSelect={setSelectedOperation}
              onChange={change}
              onAdd={add}
              onRemove={remove}
              onMove={move}
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
            onClick={() => void helperRun()}
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
