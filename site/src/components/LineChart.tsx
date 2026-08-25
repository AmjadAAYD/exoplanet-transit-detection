import { useMemo, useRef, useState } from "react";

interface LineChartProps {
  x: number[];
  y: number[];
  width?: number;
  height?: number;
  xLabel: string;
  yLabel: string;
  variant?: "primary" | "secondary";
  markX?: number; // optional vertical marker (e.g. recovered period)
  markLabel?: string;
  xFormat?: (v: number) => string;
  yFormat?: (v: number) => string;
}

const PAD = { top: 12, right: 16, bottom: 34, left: 60 };

export default function LineChart({
  x,
  y,
  width = 440,
  height = 230,
  xLabel,
  yLabel,
  variant = "primary",
  markX,
  markLabel,
  xFormat = (v) => v.toPrecision(4),
  yFormat = (v) => v.toPrecision(3),
}: LineChartProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);

  const scales = useMemo(() => {
    if (x.length === 0 || y.length === 0) return null;
    const xMin = Math.min(...x);
    const xMax = Math.max(...x);
    const yMin = Math.min(...y);
    const yMax = Math.max(...y);
    const yPad = (yMax - yMin) * 0.08 || 0.001;
    const y0 = yMin - yPad;
    const y1 = yMax + yPad;
    const plotW = width - PAD.left - PAD.right;
    const plotH = height - PAD.top - PAD.bottom;
    const sx = (v: number) => PAD.left + ((v - xMin) / (xMax - xMin || 1)) * plotW;
    const sy = (v: number) => PAD.top + plotH - ((v - y0) / (y1 - y0 || 1)) * plotH;
    return { xMin, xMax, y0, y1, sx, sy, plotW, plotH };
  }, [x, y, width, height]);

  const path = useMemo(() => {
    if (!scales) return "";
    return x.map((xv, i) => `${i === 0 ? "M" : "L"} ${scales.sx(xv).toFixed(2)} ${scales.sy(y[i]).toFixed(2)}`).join(" ");
  }, [x, y, scales]);

  if (!scales) return null;

  const xTicks = [scales.xMin, scales.xMin + (scales.xMax - scales.xMin) / 2, scales.xMax];
  const yTicks = [
    scales.y0 + (scales.y1 - scales.y0) * 0.15,
    scales.y0 + (scales.y1 - scales.y0) * 0.5,
    scales.y0 + (scales.y1 - scales.y0) * 0.85,
  ];
  const markPx = markX !== undefined ? scales.sx(markX) : null;
  const lineColor = variant === "primary" ? "var(--accent)" : "var(--ink-dim)";

  function handleMove(e: React.MouseEvent<SVGSVGElement>) {
    const svg = svgRef.current;
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    const px = ((e.clientX - rect.left) / rect.width) * width;
    // nearest index by x pixel position
    let nearest = 0;
    let best = Infinity;
    for (let i = 0; i < x.length; i++) {
      const d = Math.abs(scales.sx(x[i]) - px);
      if (d < best) {
        best = d;
        nearest = i;
      }
    }
    setHoverIdx(nearest);
  }

  const hoverX = hoverIdx !== null ? scales.sx(x[hoverIdx]) : null;
  const hoverY = hoverIdx !== null ? scales.sy(y[hoverIdx]) : null;

  return (
    <svg
      ref={svgRef}
      viewBox={`0 0 ${width} ${height}`}
      className="linechart"
      role="img"
      aria-label={`${yLabel} vs ${xLabel}`}
      onMouseMove={handleMove}
      onMouseLeave={() => setHoverIdx(null)}
    >
      {/* recessive gridlines */}
      {yTicks.map((t, i) => (
        <line key={`gy${i}`} x1={PAD.left} y1={scales.sy(t)} x2={width - PAD.right} y2={scales.sy(t)} stroke="var(--rule)" strokeWidth="1" opacity="0.6" />
      ))}

      <line x1={PAD.left} y1={PAD.top} x2={PAD.left} y2={height - PAD.bottom} stroke="var(--rule-strong)" strokeWidth="1" />
      <line x1={PAD.left} y1={height - PAD.bottom} x2={width - PAD.right} y2={height - PAD.bottom} stroke="var(--rule-strong)" strokeWidth="1" />

      {yTicks.map((t, i) => (
        <text key={`ty${i}`} x={PAD.left - 8} y={scales.sy(t) + 4} textAnchor="end" fontSize="10" fontFamily="var(--font-mono)" fill="var(--ink-faint)">
          {yFormat(t)}
        </text>
      ))}
      {xTicks.map((t, i) => (
        <text key={`tx${i}`} x={scales.sx(t)} y={height - PAD.bottom + 16} textAnchor="middle" fontSize="10" fontFamily="var(--font-mono)" fill="var(--ink-faint)">
          {xFormat(t)}
        </text>
      ))}

      {markPx !== null && (
        <>
          <line x1={markPx} y1={PAD.top} x2={markPx} y2={height - PAD.bottom} stroke="var(--accent)" strokeWidth="1" strokeDasharray="2 3" opacity="0.7" />
          {markLabel && (
            <text x={markPx} y={PAD.top - 2} textAnchor="middle" fontSize="9" fontFamily="var(--font-mono)" fill="var(--accent)">
              {markLabel}
            </text>
          )}
        </>
      )}

      <path d={path} fill="none" stroke={lineColor} strokeWidth="1.5" />

      {hoverIdx !== null && hoverX !== null && hoverY !== null && (
        <>
          <line x1={hoverX} y1={PAD.top} x2={hoverX} y2={height - PAD.bottom} stroke="var(--ink-faint)" strokeWidth="1" strokeDasharray="1 2" />
          <circle cx={hoverX} cy={hoverY} r="3" fill={lineColor} />
          <TooltipBox
            x={hoverX}
            y={hoverY}
            width={width}
            xText={xFormat(x[hoverIdx])}
            yText={yFormat(y[hoverIdx])}
          />
        </>
      )}

      <text x={width / 2} y={height - 4} textAnchor="middle" fontSize="10.5" fontFamily="var(--font-mono)" fill="var(--ink-faint)">
        {xLabel}
      </text>
      <text
        x={12}
        y={height / 2}
        textAnchor="middle"
        fontSize="10.5"
        fontFamily="var(--font-mono)"
        fill="var(--ink-faint)"
        transform={`rotate(-90 12 ${height / 2})`}
      >
        {yLabel}
      </text>
    </svg>
  );
}

function TooltipBox({ x, y, width, xText, yText }: { x: number; y: number; width: number; xText: string; yText: string }) {
  const boxW = 90;
  const boxH = 32;
  const flip = x + 10 + boxW > width;
  const bx = flip ? x - 10 - boxW : x + 10;
  const by = Math.max(2, y - boxH - 6);
  return (
    <g pointerEvents="none">
      <rect x={bx} y={by} width={boxW} height={boxH} fill="var(--bg)" stroke="var(--rule-strong)" strokeWidth="1" />
      <text x={bx + 8} y={by + 13} fontSize="9.5" fontFamily="var(--font-mono)" fill="var(--ink-faint)">
        {xText}
      </text>
      <text x={bx + 8} y={by + 25} fontSize="9.5" fontFamily="var(--font-mono)" fill="var(--ink)">
        {yText}
      </text>
    </g>
  );
}
