import { useState } from "react";
import { Backdrop, Box, CircularProgress, ThemeProvider, Typography, createTheme } from "@mui/material";
import { ProjectSidebar, useProjects } from "../features/projects";
import { useViews } from "../features/views";
import { ViewWorkspace } from "../features/pipeline/ViewWorkspace";
import { FoldButton, ResizeHandle } from "../shared/ui";
import { useRequestsInFlight } from "../shared/api";

export function App() {
  const requestsInFlight = useRequestsInFlight();
  const [error, setError] = useState("");
  const [leftWidth, setLeftWidth] = useState(250);
  const [leftFolded, setLeftFolded] = useState(false);
  const resizeLeft = (delta: number) => {
    if (leftFolded && delta <= 0) return;
    setLeftWidth((width) => {
      const next = Math.max(0, Math.min(420, width + delta));
      setLeftFolded(next === 0);
      return next;
    });
  };
  const toggleLeftFold = () => {
    if (leftFolded) {
      if (leftWidth === 0) setLeftWidth(250);
      setLeftFolded(false);
      return;
    }
    setLeftFolded(true);
  };
  const {
    projects,
    setProjects,
    projectId,
    project,
    selectProject,
    upload,
    renameProject: updateProjectName,
    deleteProject,
  } = useProjects(setError);
  const {
    viewId,
    view,
    selectView,
    createView,
    renameView: updateViewName,
    updateView,
    deleteView,
  } = useViews(projects, setProjects, projectId, setError);
  return (
    <ThemeProvider theme={theme}>
      <Box className="app" sx={{ display: "flex", flexDirection: "row", width: "100%", height: "100%", minWidth: 0 }}>
        <Backdrop open={requestsInFlight > 0} sx={{ color: "primary.main", zIndex: (theme) => theme.zIndex.modal + 1 }}>
          <CircularProgress color="inherit" aria-label="Loading" />
        </Backdrop>
        <aside
          className={`left ${leftFolded ? "folded" : ""}`}
          style={{ width: leftFolded ? 0 : leftWidth, backgroundColor: "#20272f" }}
          sx={{
            display: "flex", flex: "0 0 auto", flexDirection: "column", minWidth: 0, minHeight: 0,
            overflow: "hidden", background: "#20272f", borderRight: "1px solid #46515c",
            boxShadow: "1px 0 0 rgba(255, 255, 255, 0.04)",
            ...(leftFolded && {
              width: "0 !important",
              border: 0,
              boxShadow: "none",
            }),
          }}
        >
          <Box className="pane-heading" sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", minHeight: 56, p: "8px 12px", background: "#252d36", borderBottom: "1px solid #3b4651" }}>
            {leftFolded ? null : (
              <>
                <Typography className="brand" sx={{ letterSpacing: "0.12em", fontWeight: 800 }}>
                  DOCUMENT<span style={{ color: "#c6f36b" }}>LAB</span>
                </Typography>
              </>
            )}
          </Box>
          {!leftFolded && (
            <ProjectSidebar
              projects={projects}
              selectedProject={projectId}
              selectedView={viewId}
              onProject={selectProject}
              onView={(id, view) => {
                selectProject(id);
                selectView(id, view);
              }}
              onCreate={createView}
              onRenameProject={updateProjectName}
              onRenameView={updateViewName}
              onDeleteView={deleteView}
              onDeleteProject={deleteProject}
              onUpload={upload}
            />
          )}
        </aside>
        <ResizeHandle
            axis="horizontal"
            onResize={resizeLeft}
          >
            <Box sx={{ position: "absolute", inset: "0 -6px", "&:hover .side-splitter-button": { opacity: 1 } }}>
              <FoldButton
                label={leftFolded ? "Expand project sidebar" : "Collapse project sidebar"}
                direction={leftFolded ? "right" : "left"}
                splitter
                onClick={toggleLeftFold}
              />
            </Box>
        </ResizeHandle>
        <ViewWorkspace
          key={`${project?.id ?? ""}:${view?.id ?? ""}`}
          project={project}
          view={view}
          error={error}
          setError={setError}
          updateView={updateView}
        />
      </Box>
    </ThemeProvider>
  );
}
export const theme = createTheme({
  palette: {
    mode: "dark",
    primary: { main: "#c6f36b" },
    background: { default: "#101317", paper: "#191e24" },
  },
  typography: { fontFamily: "Inter, system-ui, sans-serif" },
  shape: { borderRadius: 10 },
});
