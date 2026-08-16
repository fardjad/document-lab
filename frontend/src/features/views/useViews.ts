import { useEffect, useState } from "react";
import type { Dispatch, SetStateAction } from "react";
import { API, request } from "../../shared/api";
import type { Project, View } from "../../entities";

type SetProjects = Dispatch<SetStateAction<Project[]>>;

export function useViews(
  projects: Project[],
  setProjects: SetProjects,
  projectId: string,
  setError: (message: string) => void,
) {
  const [viewId, setViewId] = useState<number | null>(null);

  useEffect(() => {
    setViewId(null);
    if (!projectId) {
      return;
    }

    request<View[]>(`${API}/projects/${encodeURIComponent(projectId)}/views`)
      .then((views) => {
        setProjects((current) =>
          current.map((project) =>
            project.id === projectId ? { ...project, views } : project,
          ),
        );
      })
      .catch((error) => setError(error.message));
  }, [projectId, setError, setProjects]);

  const selectView = (id: string, idToSelect: number) => {
    setViewId(idToSelect);
  };

  const createView = async () => {
    const project = projects.find((item) => item.id === projectId);
    if (!project) {
      return;
    }

    try {
      const view = await request<View>(
        `${API}/projects/${encodeURIComponent(project.id)}/views`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name: `View ${project.views.length + 1}`,
            pipeline: [],
          }),
        },
      );
      setProjects((current) =>
        current.map((item) =>
          item.id === project.id
            ? { ...item, views: [...item.views, view] }
            : item,
        ),
      );
      setViewId(view.id);
    } catch (error) {
      setError(error instanceof Error ? error.message : String(error));
    }
  };

  const renameView = async (project: Project, view: View, name: string) => {
    const updated = await request<View>(
      `${API}/projects/${encodeURIComponent(project.id)}/views/${view.id}`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: name.trim(), pipeline: view.pipeline }),
      },
    );
    setProjects((current) =>
      current.map((item) =>
        item.id === project.id
          ? {
              ...item,
              views: item.views.map((entry) =>
                entry.id === view.id ? updated : entry,
              ),
            }
          : item,
      ),
    );
  };

  const updateView = async (project: Project, view: View, updated: View) => {
    setProjects((current) =>
      current.map((item) =>
        item.id === project.id
          ? {
              ...item,
              views: item.views.map((entry) =>
                entry.id === view.id ? updated : entry,
              ),
            }
          : item,
      ),
    );
  };

  const deleteView = async (project: Project, view: View) => {
    await request<void>(
      `${API}/projects/${encodeURIComponent(project.id)}/views/${view.id}`,
      { method: "DELETE" },
    );
    setProjects((current) =>
      current.map((item) =>
        item.id === project.id
          ? {
              ...item,
              views: item.views.filter((entry) => entry.id !== view.id),
            }
          : item,
      ),
    );
    if (viewId === view.id) {
      setViewId(null);
    }
  };

  const project = projects.find((item) => item.id === projectId);
  return {
    viewId,
    view: project?.views.find((item) => item.id === viewId),
    selectView,
    createView,
    renameView,
    updateView,
    deleteView,
  };
}
