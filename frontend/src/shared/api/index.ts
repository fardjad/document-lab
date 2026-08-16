export type Options = Record<string, unknown>;
export type PipelineOp = { kind: string; options: Options; enabled?: boolean };
export type Schema = {
  type?: string;
  control?: string;
  label?: string;
  description?: string;
  min?: number;
  max?: number;
  step?: number;
  options?: unknown[];
};
export type Helper = {
  name: string;
  display_name: string;
  description?: string;
  schema?: Record<string, Schema>;
};
export type Metadata = {
  kind: string;
  name: string;
  description?: string;
  icon?: string;
  default_options: Options;
  schema: Record<string, Schema>;
  helpers?: Helper[];
};
export type View = { id: number; name: string; pipeline: PipelineOp[] };
export type Project = {
  id: string;
  name: string;
  views: View[];
  imageUrl: string;
};

export const API = "/api";

export async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  if (!response.ok) throw new Error(`Request failed (${response.status})`);
  return response.status === 204 ? (undefined as T) : response.json();
}

export function projectImageUrl(id: string): string {
  return `${API}/projects/${encodeURIComponent(id)}/image`;
}

export async function renderView(
  projectId: string,
  viewId: number,
  pipeline?: PipelineOp[],
): Promise<Blob> {
  const response = await fetch(
    `${API}/projects/${encodeURIComponent(projectId)}/views/${viewId}/render`,
    pipeline
      ? {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ pipeline }),
        }
      : undefined,
  );
  if (!response.ok) throw new Error(`Render failed (${response.status})`);
  return response.blob();
}

export async function downloadView(
  projectId: string,
  viewId: number,
): Promise<Blob> {
  return renderView(projectId, viewId);
}
