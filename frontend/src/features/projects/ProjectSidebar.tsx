import { useState, type ChangeEvent } from "react";
import {
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  TextField,
  Typography,
} from "@mui/material";
import { SimpleTreeView } from "@mui/x-tree-view/SimpleTreeView";
import { TreeItem } from "@mui/x-tree-view/TreeItem";
import AddIcon from "@mui/icons-material/Add";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutlineOutlined";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import type { Project, View } from "../../entities";

export function ProjectTree({
  projects,
  selectedProject,
  selectedView,
  onProject,
  onView,
  onCreate,
  onRenameProject,
  onRenameView,
  onDeleteView,
  onDeleteProject,
}: {
  projects: Project[];
  selectedProject: string;
  selectedView: number | null;
  onProject: (id: string) => void;
  onView: (p: string, v: number) => void;
  onCreate: () => void;
  onRenameProject: (p: Project) => void;
  onRenameView: (p: Project, v: View) => void;
  onDeleteView: (p: Project, v: View) => void;
  onDeleteProject: (p: Project) => void;
}) {
  return (
    <Box className="project-tree" sx={{ minHeight: 0, overflow: "auto", p: "0 8px 12px" }}>
      <SimpleTreeView
        selectedItems={
          selectedView === null
            ? `p:${selectedProject}`
            : `v:${selectedProject}:${selectedView}`
        }
        expandedItems={selectedProject ? [`p:${selectedProject}`] : []}
      >
        {projects.map((p) => (
          <TreeItem
            key={p.id}
            itemId={`p:${p.id}`}
            label={
              <Box className="tree-label" onClick={() => onProject(p.id)} sx={{ display: "flex", alignItems: "center", minWidth: 0, width: "100%", "&:hover .tree-action": { opacity: 1 } }}>
                <span className="dot" />
                <span className="tree-name" style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", flex: 1 }}>{p.name}</span>
                <IconButton
                  className="tree-action"
                  sx={{ opacity: 0 }}
                  size="small"
                  aria-label={`Rename project ${p.name}`}
                  onClick={(e) => {
                    e.stopPropagation();
                    onRenameProject(p);
                  }}
                >
                  <EditOutlinedIcon fontSize="small" />
                </IconButton>
                <IconButton
                  className="tree-action"
                  sx={{ opacity: 0 }}
                  size="small"
                  aria-label={`Delete project ${p.name}`}
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteProject(p);
                  }}
                >
                  <DeleteOutlineIcon fontSize="small" />
                </IconButton>
              </Box>
            }
          >
            {p.views.map((v) => (
              <TreeItem
                key={v.id}
                itemId={`v:${p.id}:${v.id}`}
                label={
                  <Box
                    className="tree-label view"
                    sx={{ display: "flex", alignItems: "center", minWidth: 0, width: "100%", "&:hover .tree-action": { opacity: 1 } }}
                    onClick={() => onView(p.id, v.id)}
                    onDoubleClick={() => onRenameView(p, v)}
                  >
                    <span className="view-dot" />
                    <span className="tree-name" style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", flex: 1 }}>{v.name}</span>
                    <IconButton
                      className="tree-action"
                      sx={{ opacity: 0 }}
                      size="small"
                      aria-label={`Rename view ${v.name}`}
                      onClick={(e) => {
                        e.stopPropagation();
                        onRenameView(p, v);
                      }}
                    >
                      <EditOutlinedIcon fontSize="small" />
                    </IconButton>
                    <IconButton
                      className="tree-action"
                      sx={{ opacity: 0 }}
                      size="small"
                      aria-label={`Delete view ${v.name}`}
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteView(p, v);
                      }}
                    >
                      <DeleteOutlineIcon fontSize="small" />
                    </IconButton>
                  </Box>
                }
              />
            ))}
            {selectedProject === p.id && (
              <Button
                size="small"
                startIcon={<AddIcon />}
                onClick={onCreate}
                className="create-view"
              >
                New view
              </Button>
            )}
          </TreeItem>
        ))}
      </SimpleTreeView>
    </Box>
  );
}

export function ProjectSidebar({
  projects,
  selectedProject,
  selectedView,
  onProject,
  onView,
  onCreate,
  onRenameProject,
  onRenameView,
  onDeleteView,
  onDeleteProject,
  onUpload,
}: {
  projects: Project[];
  selectedProject: string;
  selectedView: number | null;
  onProject: (id: string) => void;
  onView: (p: string, v: number) => void;
  onCreate: () => void;
  onRenameProject: (p: Project, name: string) => Promise<void>;
  onRenameView: (p: Project, v: View, name: string) => Promise<void>;
  onDeleteView: (p: Project, v: View) => Promise<void>;
  onDeleteProject: (p: Project) => Promise<void>;
  onUpload: (event: ChangeEvent<HTMLInputElement>) => Promise<void>;
}) {
  const [renameTarget, setRenameTarget] = useState<{
    project: Project;
    view?: View;
  }>();
  const [renameName, setRenameName] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<{
    project: Project;
    view?: View;
  }>();
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const matchingProjects = projects.filter((project) =>
    project.name.toLocaleLowerCase().includes(search.trim().toLocaleLowerCase()),
  );
  const run = async (action: () => Promise<void>) => {
    try {
      await action();
    } catch (e) {
      setError((e as Error).message);
    }
  };
  const rename = () => {
    if (!renameTarget || !renameName.trim()) return;
    void run(async () => {
      if (renameTarget.view)
        await onRenameView(renameTarget.project, renameTarget.view, renameName);
      else await onRenameProject(renameTarget.project, renameName);
      setRenameTarget(undefined);
    });
  };
  const remove = () => {
    if (!deleteTarget) return;
    void run(async () => {
      if (deleteTarget.view)
        await onDeleteView(deleteTarget.project, deleteTarget.view);
      else await onDeleteProject(deleteTarget.project);
      setDeleteTarget(undefined);
    });
  };
  return (
    <>
      {error && (
        <Typography color="error" role="alert">
          {error}
        </Typography>
      )}
      <Box className="section-actions" sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", p: "4px 12px 8px" }}>
        <Typography className="section-title" sx={{ fontWeight: 700 }}>Projects</Typography>
        <Button component="label" size="small" startIcon={<UploadFileIcon />}>
          Import
          <input
            hidden
            type="file"
            accept="image/*"
            onChange={(e) => {
              void onUpload(e);
            }}
          />
        </Button>
      </Box>
      <TextField
        size="small"
        fullWidth
        value={search}
        onChange={(event) => setSearch(event.target.value)}
        placeholder="Search projects"
        slotProps={{ htmlInput: { "aria-label": "Search projects" } }}
        sx={{ px: 1, pb: 1 }}
      />
      <ProjectTree
        projects={matchingProjects}
        selectedProject={selectedProject}
        selectedView={selectedView}
        onProject={onProject}
        onView={onView}
        onCreate={onCreate}
        onRenameProject={(p) => {
          setRenameTarget({ project: p });
          setRenameName(p.name);
        }}
        onRenameView={(p, v) => {
          setRenameTarget({ project: p, view: v });
          setRenameName(v.name);
        }}
        onDeleteView={(p, v) => setDeleteTarget({ project: p, view: v })}
        onDeleteProject={(p) => setDeleteTarget({ project: p })}
      />
      <Dialog
        open={Boolean(renameTarget)}
        onClose={() => setRenameTarget(undefined)}
      >
        <DialogTitle>
          Rename {renameTarget?.view ? "view" : "project"}
        </DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            fullWidth
            label={renameTarget?.view ? "View name" : "Project name"}
            value={renameName}
            onChange={(e) => setRenameName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") rename();
            }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRenameTarget(undefined)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={rename}
            disabled={!renameName.trim()}
          >
            Rename
          </Button>
        </DialogActions>
      </Dialog>
      <Dialog
        open={Boolean(deleteTarget)}
        onClose={() => setDeleteTarget(undefined)}
      >
        <DialogTitle>
          Delete {deleteTarget?.view ? "view" : "project"}?
        </DialogTitle>
        <DialogContent>
          <Typography>This action cannot be undone.</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteTarget(undefined)}>Cancel</Button>
          <Button color="error" variant="contained" onClick={remove}>
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
