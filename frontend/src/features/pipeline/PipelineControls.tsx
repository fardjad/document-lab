import { useState } from "react";
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

import type { Metadata, Options, PipelineOp, Helper } from "../../entities";

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
}: {
  meta?: Metadata;
  op?: PipelineOp;
  onChange: (o: Options) => void;
}) {
  if (!meta || !op)
    return (
      <Box sx={{ height: "100%", overflow: "auto", p: 2 }}>
        <Typography variant="h6">Operation parameters</Typography>
        <Typography color="text.secondary">
          Select an operation in the pipeline to edit its parameters.
        </Typography>
      </Box>
    );
  return (
    <Box sx={{ height: "100%", overflow: "auto", p: 2 }}>
      <Typography variant="h6">{meta.name} parameters</Typography>
      <Typography sx={{ display: "block", mb: 2 }}>{meta.description}</Typography>
      <Stack spacing={2}>
        {Object.entries(meta.schema ?? {}).map(([key, schema]) => {
          const value = op.options[key] ?? meta.default_options[key] ?? "";
          const label = schema.label ?? key;
          const step = schema.step;
          if (schema.control === "checkbox")
            return (
              <FormControlLabel
                key={key}
                control={
                  <Checkbox
                    checked={Boolean(value)}
                    onChange={(e) =>
                      onChange({ ...op.options, [key]: e.target.checked })
                    }
                  />
                }
                label={label}
              />
            );
          if (schema.control === "dropdown")
            return (
              <FormControl fullWidth size="small" key={key}>
                <InputLabel>{label}</InputLabel>
                <Select
                  value={String(value)}
                  label={label}
                  onChange={(e) =>
                    onChange({ ...op.options, [key]: e.target.value })
                  }
                >
                  {(schema.options ?? []).map((x) => (
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
                  onChange={(_, v) => onChange({ ...op.options, [key]: v })}
                />
                <TextField
                  size="small"
                  type="number"
                  value={value}
                  onChange={(e) =>
                    onChange({ ...op.options, [key]: Number(e.target.value) })
                  }
                  inputProps={{ min: schema.min, max: schema.max, step }}
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
              onChange={(e) =>
                onChange({ ...op.options, [key]: Number(e.target.value) })
              }
              inputProps={{ min: schema.min, max: schema.max, step }}
              helperText={schema.description}
            />
          );
        })}
      </Stack>
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
  onHelper,
}: {
  pipeline: PipelineOp[];
  metas: Metadata[];
  selected: number | null;
  onSelect: (i: number) => void;
  onChange: (p: PipelineOp[]) => void;
  onAdd: (kind: string) => void;
  onRemove: (i: number) => void;
  onMove: (i: number, d: number) => void;
  onHelper: (i: number, h: Helper) => void;
}) {
  const [adding, setAdding] = useState(false);
  return (
    <Box sx={{ minHeight: 0, overflow: "auto", p: "0 8px 12px", flex: "1 1 auto" }}>
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 1.5 }}>
        <Typography variant="h6">Pipeline</Typography>
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
                {m?.helpers?.length ? (
                  <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5, mt: 1 }}>
                    {m.helpers.map((h) => (
                      <Button
                        key={h.name}
                        size="small"
                        startIcon={<AutoFixHighIcon />}
                        onClick={(e) => {
                          e.stopPropagation();
                          onHelper(i, h);
                        }}
                      >
                        {h.display_name}
                      </Button>
                    ))}
                  </Box>
                ) : null}
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
