import { useEffect, useState } from "react";
import type { Metadata, PipelineOp, View } from "../../entities";
import { clonePipeline, opMeta } from "./PipelineControls";

export function usePipeline(metas: Metadata[], view?: View) {
  const [pipeline, setPipeline] = useState<PipelineOp[]>([]);
  const [selectedOperation, setSelectedOperation] = useState<number | null>(
    null,
  );
  const [activeEditing, setActiveEditing] = useState(false);
  const [pipelineReady, setPipelineReady] = useState(false);
  useEffect(() => {
    if (!view) {
      setPipelineReady(false);
      return;
    }
    setPipeline(clonePipeline(view.pipeline));
    setSelectedOperation(null);
    setActiveEditing(false);
    setPipelineReady(true);
  }, [view?.id]);
  const add = (kind: string) => {
    const meta = opMeta(metas, kind);
    if (!meta) return;
    const next = [
      ...pipeline,
      { kind, options: { ...meta.default_options }, enabled: true },
    ];
    setPipeline(next);
    setSelectedOperation(next.length - 1);
    setActiveEditing(true);
  };
  const remove = (index: number) => {
    setPipeline((current) =>
      current.filter((_, itemIndex) => itemIndex !== index),
    );
    setSelectedOperation((current) =>
      current === index
        ? null
        : current !== null && current > index
          ? current - 1
          : current,
    );
    setActiveEditing(true);
  };
  const move = (index: number, direction: number) => {
    const target = index + direction;
    if (target < 0 || target >= pipeline.length) return;
    const next = [...pipeline];
    [next[index], next[target]] = [next[target], next[index]];
    setPipeline(next);
    setSelectedOperation(target);
    setActiveEditing(true);
  };
  const change = (next: PipelineOp[]) => {
    setPipeline(next);
    setActiveEditing(true);
  };
  return {
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
  };
}
