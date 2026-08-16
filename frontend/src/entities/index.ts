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
  enum?: unknown[];
  minimum?: number;
  maximum?: number;
  title?: string;
  "x-hint-ui-control"?: string;
  "x-hint-ui-step"?: number;
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
