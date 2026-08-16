import { useEffect, useState, type ChangeEvent } from "react";
import { API, projectImageUrl, request } from "../../shared/api";
import type { Project, View } from "../../entities";

export function useProjects(setError: (message: string) => void) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState("");

  useEffect(() => {
    request<{ id: string; name: string }[]>(`${API}/projects/details`)
      .then((ids) => {
        const loaded = ids.map(({ id, name }) => ({
          id,
          name,
          views: [],
          imageUrl: projectImageUrl(id),
        }));
        setProjects(loaded);
        if (loaded[0]) {
          setProjectId(loaded[0].id);
        }
      })
      .catch((error) => setError(error.message));
  }, [setError]);

  const selectProject = (id: string) => {
    setProjectId(id);
  };

  const upload = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }

    const form = new FormData();
    form.append("image", file);

    try {
      const created = await request<{
        id: string;
        name?: string;
        views?: View[];
      }>(`${API}/projects`, { method: "POST", body: form });
      const project: Project = {
        id: created.id,
        name: created.name ?? created.id,
        views: Array.isArray(created.views) ? created.views : [],
        imageUrl: projectImageUrl(created.id),
      };
      setProjects((current) => [...current, project]);
      setProjectId(project.id);
    } catch (error) {
      setError(error instanceof Error ? error.message : String(error));
    }
  };

  const renameProject = async (project: Project, name: string) => {
    const updated = await request<{ id: string; name: string }>(
      `${API}/projects/${encodeURIComponent(project.id)}/name`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: name.trim() }),
      },
    );
    setProjects((current) =>
      current.map((item) =>
        item.id === project.id ? { ...item, name: updated.name } : item,
      ),
    );
  };

  const deleteProject = async (project: Project) => {
    await request<void>(`${API}/projects/${encodeURIComponent(project.id)}`, {
      method: "DELETE",
    });
    setProjects((current) => current.filter((item) => item.id !== project.id));
    if (projectId === project.id) {
      setProjectId("");
    }
  };

  return {
    projects,
    setProjects,
    projectId,
    project: projects.find((item) => item.id === projectId),
    selectProject,
    upload,
    renameProject,
    deleteProject,
  };
}

export type { Project, View };
export { ProjectSidebar, ProjectTree } from "./ProjectSidebar";
