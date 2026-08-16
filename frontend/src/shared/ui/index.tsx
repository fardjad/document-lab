import { useRef, type PointerEvent as ReactPointerEvent, type ReactNode } from "react";
import { Box, IconButton } from "@mui/material";
import ChevronLeftIcon from "@mui/icons-material/ChevronLeft";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import KeyboardArrowUpIcon from "@mui/icons-material/KeyboardArrowUp";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";

export function ResizeHandle({
  axis,
  onResize,
  children,
  onResizeStart,
  onResizeEnd,
}: {
  axis: "horizontal" | "vertical";
  onResize: (delta: number) => void;
  children?: ReactNode;
  onResizeStart?: () => void;
  onResizeEnd?: () => void;
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
        flex: "0 0 auto", zIndex: 2, background: "#46515c", position: "relative",
        ...(axis === "horizontal"
          ? { width: 4, cursor: "col-resize" }
          : { height: 4, cursor: "row-resize" }),
        "&:hover, &:active": { background: "#c6f36b" },
      }}
      onPointerDown={(event) => {
        onResizeStart?.();
        down(event);
      }}
      onPointerMove={move}
      onPointerUp={(event) => {
        event.currentTarget.releasePointerCapture(event.pointerId);
        onResizeEnd?.();
      }}
    >
      {children}
    </Box>
  );
}

export function FoldButton({
  label,
  direction,
  onClick,
  divider = false,
  splitter = false,
}: {
  label: string;
  direction: "left" | "right" | "up" | "down";
  onClick: () => void;
  divider?: boolean;
  splitter?: boolean;
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
      className={splitter ? "fold-button side-splitter-button" : "fold-button"}
      sx={{
        flex: "0 0 auto",
        background: "#2b3540",
        border: "1px solid #46515c",
        boxShadow: "0 1px 2px rgba(0, 0, 0, 0.3)",
        ...(divider && {
          width: 40,
          height: 16,
          border: "2px solid #46515c",
          borderRadius: "0 0 5px 5px",
          p: 0,
        }),
        ...(splitter && {
          position: "absolute",
          top: "50%",
          left: "50%",
          width: direction === "left" || direction === "right" ? 16 : 48,
          height: direction === "left" || direction === "right" ? 48 : 16,
          minWidth: direction === "left" || direction === "right" ? 16 : 48,
          transform: "translate(-50%, -50%)",
          border: 0,
          borderRadius: 0,
          boxShadow: "none",
          opacity: 1,
          p: 0,
          transition: "opacity 120ms ease, background 120ms ease",
          "& svg": { opacity: 0, transition: "opacity 120ms ease" },
          "&:hover, &:focus-visible": { background: "#2b3540", "& svg": { opacity: 1 } },
        }),
        "&:hover": { background: "#36424e" },
      }}
      size="small"
      aria-label={label}
      onPointerDown={(event) => event.stopPropagation()}
      onPointerMove={(event) => event.stopPropagation()}
      onPointerUp={(event) => event.stopPropagation()}
      onClick={onClick}
    >
      <Icon />
    </IconButton>
  );
}
