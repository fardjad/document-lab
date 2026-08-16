import { useState } from "react";
import { Box, ThemeProvider, Typography, createTheme } from "@mui/material";
import { ProjectSidebar, useProjects } from "../features/projects";
import { useViews, ViewWorkspace } from "../features/views";
import { FoldButton, ResizeHandle } from "../shared/ui";

export function App() {
  const [error, setError] = useState("");
  const [leftWidth, setLeftWidth] = useState(250);
  const [leftFolded, setLeftFolded] = useState(false);
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
        <aside
          className={`left ${leftFolded ? "folded" : ""}`}
          style={{ width: leftFolded ? 30 : leftWidth }}
          sx={{
            display: "flex", flex: "0 0 auto", flexDirection: "column", minWidth: 0, minHeight: 0,
            overflow: "hidden", background: "#191e24", borderRight: "1px solid #303840",
            ...(leftFolded && { width: "30px !important", "& .pane-heading": { justifyContent: "center", p: "8px 0" }, "& .fold-button": { width: 30, height: 36, p: "4px 0" } }),
          }}
        >
          <Box className="pane-heading" sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", minHeight: 56, p: "8px 12px" }}>
            {leftFolded ? (
              <FoldButton
                label="Expand project sidebar"
                direction="right"
                onClick={() => setLeftFolded(false)}
              />
            ) : (
              <>
                <Typography className="brand" sx={{ letterSpacing: "0.12em", fontWeight: 800 }}>
                  DOCUMENT<span style={{ color: "#c6f36b" }}>LAB</span>
                </Typography>
                <FoldButton
                  label="Collapse project sidebar"
                  direction="left"
                  onClick={() => setLeftFolded(true)}
                />
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
        {!leftFolded && (
          <ResizeHandle
            axis="horizontal"
            onResize={(d) =>
              setLeftWidth((w) => Math.max(180, Math.min(420, w + d)))
            }
          />
        )}
        <ViewWorkspace
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
