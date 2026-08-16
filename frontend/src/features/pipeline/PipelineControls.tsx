import { useEffect, useState } from "react";
import {
  Box,
  Button,
  Card,
  CardContent,
  Checkbox,
  FormControl,
  FormControlLabel,
  InputLabel,
  MenuItem,
  Select,
  Slider,
  Stack,
  TextField,
  Tooltip,
  Typography,
  IconButton,
} from "@mui/material";
import Rotate90DegreesCcwIcon from "@mui/icons-material/Rotate90DegreesCcw";
import StraightenIcon from "@mui/icons-material/Straighten";
import ContentCutIcon from "@mui/icons-material/ContentCut";
import AutoFixHighIcon from "@mui/icons-material/AutoFixHigh";
import AddIcon from "@mui/icons-material/Add";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutlineOutlined";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import FitScreenIcon from "@mui/icons-material/FitScreen";
import ZoomInIcon from "@mui/icons-material/ZoomIn";
import ZoomOutIcon from "@mui/icons-material/ZoomOut";
import CenterFocusStrongIcon from "@mui/icons-material/CenterFocusStrong";
import DownloadOutlinedIcon from "@mui/icons-material/DownloadOutlined";
import CheckIcon from "@mui/icons-material/Check";
import CloseIcon from "@mui/icons-material/Close";

import type { Helper, Metadata, Options, PipelineOp } from "../../entities";

const icons: Record<string, React.ElementType> = {
  Rotate90DegreesCcw: Rotate90DegreesCcwIcon,
  Straighten: StraightenIcon,
  ContentCut: ContentCutIcon,
  AutoFixHigh: AutoFixHighIcon,
};
const Icon = ({ name }: { name?: string }) => {
  const C = icons[name ?? ""] ?? AutoFixHighIcon;
  return <C fontSize="small" />;
};
export function opMeta(metas: Metadata[], kind: string) {
  return metas.find((m) => m.kind === kind);
}
export function clonePipeline(p: PipelineOp[]) {
  return p.map((o) => ({
    kind: o.kind,
    options: { ...o.options },
    enabled: o.enabled !== false,
  }));
}
export function Parameters({
  meta,
  op,
  onChange,
  onHelper,
  onDraftChange,
}: {
  meta?: Metadata;
  op?: PipelineOp;
  onChange: (o: Options) => void;
  onHelper: (helper: Helper) => Promise<Options | undefined>;
  onDraftChange: (options?: Options) => void;
}) {
  const [draft, setDraft] = useState<Options>({});
  useEffect(() => {
    setDraft(op?.options ?? {});
    onDraftChange(undefined);
  }, [op, onDraftChange]);
  const hasChanges = JSON.stringify(draft) !== JSON.stringify(op?.options ?? {});
  if (!meta || !op)
    return (
      <Box sx={{ height: "100%", overflow: "auto", p: 2 }}>
        <Typography variant="h6">Operation options</Typography>
        <Typography color="text.secondary">
          Select an operation in the pipeline to edit its options.
        </Typography>
      </Box>
    );
  return (
    <Box sx={{ height: "100%", overflow: "auto", p: 2 }}>
      <Box sx={{ display: "flex", alignItems: "center", mb: 2 }}>
        <Typography variant="h6" sx={{ flex: 1 }}>{meta.name} options</Typography>
        <Tooltip title="Save options">
          <span>
            <IconButton
              size="small"
              color="primary"
              disabled={!hasChanges}
              onClick={() => {
                onChange(draft);
                onDraftChange(undefined);
              }}
            >
              <CheckIcon />
            </IconButton>
          </span>
        </Tooltip>
        <Tooltip title="Cancel changes">
          <span>
            <IconButton
              size="small"
              disabled={!hasChanges}
              onClick={() => {
                setDraft(op.options);
                onDraftChange(undefined);
              }}
            >
              <CloseIcon />
            </IconButton>
          </span>
        </Tooltip>
      </Box>
      <Typography sx={{ display: "block", mb: 2 }}>{meta.description}</Typography>
      <Stack spacing={2}>
        {Object.entries(meta.schema ?? {}).map(([key, schema]) => {
          const value = draft[key] ?? meta.default_options[key] ?? "";
          const label = schema.label ?? key;
          const step = schema.step;
          if (schema.control === "checkbox")
            return (
              <FormControlLabel
                key={key}
                control={
                  <Checkbox
                    checked={Boolean(value)}
                    onChange={(e) => {
                      setDraft({ ...draft, [key]: e.target.checked });
                      onDraftChange({ ...draft, [key]: e.target.checked });
                    }}
                  />
                }
                label={label}
              />
            );
          if (schema.control === "dropdown" || schema.enum)
            return (
              <FormControl fullWidth size="small" key={key}>
                <InputLabel>{label}</InputLabel>
                <Select
                  value={String(value)}
                  label={label}
                  onChange={(e) => {
                    setDraft({ ...draft, [key]: e.target.value });
                    onDraftChange({ ...draft, [key]: e.target.value });
                  }}
                >
                  {(schema.options ?? schema.enum ?? []).map((x) => (
                    <MenuItem key={String(x)} value={String(x)}>
                      {String(x)}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            );
          if (schema.control === "slider")
            return (
              <Box key={key}>
                <Typography variant="body2">
                  {label}: {String(value)}
                </Typography>
                <Slider
                  value={Number(value)}
                  min={schema.min}
                  max={schema.max}
                  step={step}
                  onChange={(_, v) => {
                    setDraft({ ...draft, [key]: v });
                    onDraftChange({ ...draft, [key]: v });
                  }}
                />
                <TextField
                  size="small"
                  type="number"
                  value={value}
                  onChange={(e) => {
                    setDraft({ ...draft, [key]: Number(e.target.value) });
                    onDraftChange({ ...draft, [key]: Number(e.target.value) });
                  }}
                  slotProps={{ htmlInput: { min: schema.min, max: schema.max, step } }}
                />
              </Box>
            );
          return (
            <TextField
              key={key}
              fullWidth
              size="small"
              type="number"
              label={label}
              value={value}
              onChange={(e) => {
                setDraft({ ...draft, [key]: Number(e.target.value) });
                onDraftChange({ ...draft, [key]: Number(e.target.value) });
              }}
              slotProps={{ htmlInput: { min: schema.min, max: schema.max, step } }}
              helperText={schema.description}
            />
          );
        })}
      </Stack>
      {meta.helpers?.length ? (
        <Stack spacing={1} sx={{ mt: 3 }}>
          <Typography variant="subtitle2">Helpers</Typography>
          {meta.helpers.map((helper) => (
            <Button
              key={helper.name}
              fullWidth
              variant="outlined"
              startIcon={<AutoFixHighIcon />}
              onClick={() => {
                void onHelper(helper).then((options) => {
                  if (options) setDraft((current) => {
                    const next = { ...current, ...options };
                    onDraftChange(next);
                    return next;
                  });
                });
              }}
            >
              {helper.display_name}
            </Button>
          ))}
        </Stack>
      ) : null}
    </Box>
  );
}
export function Pipeline({
  pipeline,
  metas,
  selected,
  onSelect,
  onChange,
  onAdd,
  onRemove,
  onMove,
}: {
  pipeline: PipelineOp[];
  metas: Metadata[];
  selected: number | null;
  onSelect: (i: number) => void;
  onChange: (p: PipelineOp[]) => void;
  onAdd: (kind: string) => void;
  onRemove: (i: number) => void;
  onMove: (i: number, d: number) => void;
}) {
  const [adding, setAdding] = useState(false);
  return (
    <Box sx={{ minHeight: 0, overflow: "auto", p: "0 8px 12px", flex: "1 1 auto" }}>
      <Box sx={{ display: "flex", justifyContent: "flex-end", mb: 1.5 }}>
        <Typography variant="caption">{pipeline.length} operations</Typography>
      </Box>
      <Stack spacing={1}>
        {pipeline.map((op, i) => {
          const m = opMeta(metas, op.kind);
          const enabled = op.enabled !== false;
          return (
            <Card
              className="operation"
              key={`${op.kind}-${i}`}
              sx={{
                ...(selected === i && {
                  borderColor: "primary.main",
                  background: "rgba(198, 243, 107, 0.1)",
                  boxShadow: "0 0 0 1px rgba(198, 243, 107, 0.35)",
                }),
                ...(!enabled && {
                  opacity: 0.48,
                  "& .MuiTypography-root": { textDecoration: "line-through" },
                }),
              }}
              onClick={() => onSelect(i)}
            >
              <CardContent>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                  <Checkbox
                    size="small"
                    checked={enabled}
                    aria-label={`${enabled ? "Disable" : "Enable"} ${m?.name ?? op.kind}`}
                    onClick={(e) => e.stopPropagation()}
                    onChange={(e) => {
                      e.stopPropagation();
                      onChange(
                        pipeline.map((x, n) =>
                          n === i ? { ...x, enabled: e.target.checked } : x,
                        ),
                      );
                    }}
                  />
                  <Icon name={m?.icon} />
                  <Box flex={1} sx={{ minWidth: 0 }}>
                    <Typography fontWeight={600}>
                      {m?.name ?? op.kind}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {m?.description}
                    </Typography>
                  </Box>
                  <IconButton
                    size="small"
                    sx={{ ml: "auto" }}
                    onClick={(e) => {
                      e.stopPropagation();
                      onMove(i, -1);
                    }}
                    disabled={i === 0}
                  >
                    <ExpandLessIcon />
                  </IconButton>
                  <IconButton
                    size="small"
                    onClick={(e) => {
                      e.stopPropagation();
                      onMove(i, 1);
                    }}
                    disabled={i === pipeline.length - 1}
                  >
                    <ExpandMoreIcon />
                  </IconButton>
                  <IconButton
                    size="small"
                    onClick={(e) => {
                      e.stopPropagation();
                      onRemove(i);
                    }}
                  >
                    <DeleteOutlineIcon />
                  </IconButton>
                </Box>
              </CardContent>
            </Card>
          );
        })}
      </Stack>
      <Button
        fullWidth
        variant="outlined"
        startIcon={<AddIcon />}
        onClick={() => setAdding((v) => !v)}
        sx={{ mt: 1.5 }}
      >
        Add operation
      </Button>
      {adding && (
        <Card>
          <CardContent>
            {metas.map((m) => (
              <Button
                key={m.kind}
                fullWidth
                startIcon={<Icon name={m.icon} />}
                onClick={() => {
                  onAdd(m.kind);
                  setAdding(false);
                }}
              >
                {m.name}
              </Button>
            ))}
          </CardContent>
        </Card>
      )}
    </Box>
  );
}
