import {
  useEffect,
  useRef,
  useState,
  type PointerEvent as ReactPointerEvent,
} from "react";
import { Box, IconButton, Tooltip, Typography } from "@mui/material";
import FitScreenIcon from "@mui/icons-material/FitScreen";
import ZoomInIcon from "@mui/icons-material/ZoomIn";
import ZoomOutIcon from "@mui/icons-material/ZoomOut";
import CenterFocusStrongIcon from "@mui/icons-material/CenterFocusStrong";
import DownloadOutlinedIcon from "@mui/icons-material/DownloadOutlined";
import { API, trackedFetch } from "../../shared/api";
import type { PipelineOp, Project, View } from "../../entities";

export function Preview({
  project,
  view,
  pipeline,
  activeEditing,
}: {
  project?: Project;
  view?: View;
  pipeline: PipelineOp[];
  activeEditing: boolean;
}) {
  const img = useRef<HTMLImageElement>(null);
  const imageViewer = useRef<HTMLDivElement>(null);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [preview, setPreview] = useState("");
  const needsFit = useRef(false);
  const dragging = useRef<{
    x: number;
    y: number;
    panX: number;
    panY: number;
  } | null>(null);
  useEffect(() => {
    if (!project || !view || !activeEditing) return;
    const timer = setTimeout(() => {
      const enabledPipeline = pipeline
        .filter((o) => o.enabled !== false)
        .map(({ kind, options }) => ({ kind, options }));
      const crop = enabledPipeline.find((operation) => operation.kind === "crop");
      if (
        crop &&
        (!isNormalizedRectangle(crop.options.x) ||
          !isNormalizedRectangle(crop.options.y) ||
          !isNormalizedRectangle(crop.options.width) ||
          !isNormalizedRectangle(crop.options.height) ||
          Number(crop.options.x) + Number(crop.options.width) > 1 ||
          Number(crop.options.y) + Number(crop.options.height) > 1)
      ) {
        setPreview("");
        return;
      }
      trackedFetch(
        `${API}/projects/${encodeURIComponent(project.id)}/views/${view.id}/render`,
        {
          method: "POST",
          cache: "no-store",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ pipeline: enabledPipeline }),
        },
      )
        .then((r) =>
          r.ok ? r.blob() : Promise.reject(new Error("Preview failed")),
        )
        .then((b) => {
          const u = URL.createObjectURL(b);
          setPreview((old) => {
            if (old) URL.revokeObjectURL(old);
            return u;
          });
        })
        .catch(() => setPreview(""));
    }, 350);
    return () => clearTimeout(timer);
  }, [project?.id, view?.id, JSON.stringify(pipeline), activeEditing]);
  useEffect(() => {
    if (!activeEditing) {
      setPreview((current) => {
        if (current) URL.revokeObjectURL(current);
        return "";
      });
    }
  }, [activeEditing, view?.id]);
  useEffect(() => {
    needsFit.current = true;
  }, [project?.id, view?.id]);
  useEffect(() => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  }, [project?.id, view?.id]);
  const savedRenderUrl =
    project && view
      ? `${API}/projects/${encodeURIComponent(project.id)}/views/${view.id}/render?pipeline=${encodeURIComponent(JSON.stringify(view.pipeline))}`
      : undefined;
  const src = activeEditing
    ? preview || project?.imageUrl
    : project && view
      ? savedRenderUrl
      : undefined;
  const reset = (nextZoom?: number) => {
    const viewer = imageViewer.current;
    const image = img.current;
    if (!viewer || !image || !image.naturalWidth || !image.naturalHeight) {
      setZoom(nextZoom ?? 1);
      setPan({ x: 0, y: 0 });
      return;
    }
    const containerWidth = viewer.clientWidth;
    const containerHeight = viewer.clientHeight;
    const padding = 24;
    const availableWidth = containerWidth - padding * 2;
    const availableHeight = containerHeight - padding * 2;
    const targetZoom =
      nextZoom ??
      Math.min(
        availableWidth / image.naturalWidth,
        availableHeight / image.naturalHeight,
      );
    setZoom(targetZoom);
    setPan({
      x: (containerWidth - image.naturalWidth * targetZoom) / 2,
      y: (containerHeight - image.naturalHeight * targetZoom) / 2,
    });
  };
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
    if (e.currentTarget.hasPointerCapture(e.pointerId))
      e.currentTarget.releasePointerCapture(e.pointerId);
    dragging.current = null;
  };
  const wheel = (e: React.WheelEvent<HTMLDivElement>) => {
    e.preventDefault();
    setZoom((z) => Math.max(0.25, Math.min(8, z * (e.deltaY < 0 ? 1.1 : 0.9))));
  };
  const download = async () => {
    if (!project || !view) return;
    const response = await trackedFetch(
      `${API}/projects/${encodeURIComponent(project.id)}/views/${view.id}/render`,
    );
    if (!response.ok) throw new Error(`Download failed (${response.status})`);
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${view.name}.png`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  };
  return (
    <Box
      className="preview"
      sx={{
        display: "flex",
        flexDirection: "column",
        width: "100%",
        height: "100%",
        minHeight: 0,
        overflow: "hidden",
        position: "relative",
      }}
    >
      <Box
        className="preview-toolbar"
        sx={{
          display: "flex",
          flex: "0 0 56px",
          minHeight: 56,
          alignItems: "center",
          justifyContent: "flex-end",
          gap: 0.5,
          width: "100%",
          p: "4px 8px",
          background: "#20272f",
          borderBottom: "1px solid #3b4651",
        }}
      >
        <Tooltip title="Fit and center">
          <IconButton onClick={() => reset()}>
            <FitScreenIcon />
          </IconButton>
        </Tooltip>
        <Tooltip title="Actual size and center">
          <IconButton onClick={() => reset(1)}>
            <CenterFocusStrongIcon />
          </IconButton>
        </Tooltip>
        <IconButton
          aria-label="Zoom out"
          onClick={() => setZoom((z) => Math.max(0.25, z / 1.25))}
        >
          <ZoomOutIcon />
        </IconButton>
        <Typography>{Math.round(zoom * 100)}%</Typography>
        <IconButton
          aria-label="Zoom in"
          onClick={() => setZoom((z) => Math.min(8, z * 1.25))}
        >
          <ZoomInIcon />
        </IconButton>
        <Tooltip title="Download rendered PNG">
          <span style={{ display: "inline-flex" }}>
            <IconButton
              aria-label="Download rendered PNG"
              disabled={!view}
              onClick={() => {
                void download();
              }}
            >
              <DownloadOutlinedIcon />
            </IconButton>
          </span>
        </Tooltip>
      </Box>
      <Box
        className="image-viewer"
        ref={imageViewer}
        sx={{
          position: "relative",
          display: "flex",
          flex: "1 1 auto",
          alignItems: "center",
          justifyContent: "center",
          width: "100%",
          minHeight: 0,
          overflow: "hidden",
          backgroundColor: "#252a30",
          backgroundImage:
            "linear-gradient(45deg, #2d3339 25%, transparent 25%), linear-gradient(-45deg, #2d3339 25%, transparent 25%), linear-gradient(45deg, transparent 75%, #2d3339 75%), linear-gradient(-45deg, transparent 75%, #2d3339 75%)",
          backgroundPosition: "0 0, 0 8px, 8px -8px, -8px 0",
          backgroundSize: "16px 16px",
        }}
      >
        {src ? (
          <Box
            className="image-stage"
            sx={{
              position: "absolute",
              top: 0,
              left: 0,
              transformOrigin: "top left",
              cursor: "grab",
              touchAction: "none",
              "&:active": { cursor: "grabbing" },
              "& img": { display: "block", userSelect: "none" },
            }}
            style={{
              transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
            }}
            onPointerDown={down}
            onPointerMove={move}
            onPointerUp={up}
            onPointerCancel={up}
            onWheel={wheel}
          >
            <img
              key={`${project?.id ?? ""}-${view?.id ?? ""}`}
              ref={img}
              src={src}
              alt={project?.name ?? "Document"}
              draggable={false}
              onLoad={() => {
                if (needsFit.current) {
                  needsFit.current = false;
                  reset();
                }
              }}
            />
          </Box>
        ) : (
          <Typography color="text.secondary">
            Select a view to begin editing
          </Typography>
        )}
      </Box>
    </Box>
  );
}

function isNormalizedRectangle(value: unknown) {
  return typeof value === "number" && value >= 0 && value <= 1;
}
