import { useRef, type PointerEvent as ReactPointerEvent } from "react";
import { Box, IconButton } from "@mui/material";
import ChevronLeftIcon from "@mui/icons-material/ChevronLeft";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import KeyboardArrowUpIcon from "@mui/icons-material/KeyboardArrowUp";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";

export function ResizeHandle({
  axis,
  onResize,
}: {
  axis: "horizontal" | "vertical";
  onResize: (delta: number) => void;
}) {
  const start = useRef(0);
  const down = (event: ReactPointerEvent<HTMLDivElement>) => {
    start.current = axis === "horizontal" ? event.clientX : event.clientY;
    event.currentTarget.setPointerCapture(event.pointerId);
  };
  const move = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (!event.currentTarget.hasPointerCapture(event.pointerId)) return;
    const current = axis === "horizontal" ? event.clientX : event.clientY;
    onResize(current - start.current);
    start.current = current;
  };
  return (
    <Box
      className={`resize-handle ${axis}`}
      sx={{
        flex: "0 0 auto", zIndex: 2, background: "transparent",
        ...(axis === "horizontal" ? { width: 5, cursor: "col-resize" } : { height: 5, cursor: "row-resize" }),
        "&:hover, &:active": { background: "#c6f36b" },
      }}
      onPointerDown={down}
      onPointerMove={move}
      onPointerUp={(event) =>
        event.currentTarget.releasePointerCapture(event.pointerId)
      }
    />
  );
}

export function FoldButton({
  label,
  direction,
  onClick,
}: {
  label: string;
  direction: "left" | "right" | "up" | "down";
  onClick: () => void;
}) {
  const Icon =
    direction === "left"
      ? ChevronLeftIcon
      : direction === "right"
        ? ChevronRightIcon
        : direction === "up"
          ? KeyboardArrowUpIcon
          : KeyboardArrowDownIcon;
  return (
    <IconButton
      className="fold-button"
      sx={{ flex: "0 0 auto" }}
      size="small"
      aria-label={label}
      onClick={onClick}
    >
      <Icon />
    </IconButton>
  );
}
