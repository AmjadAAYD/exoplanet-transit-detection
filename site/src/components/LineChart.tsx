import { useMemo } from "react";

interface LineChartProps {
  x: number[];
  y: number[];
  width?: number;
  height?: number;
  xLabel: string;
  yLabel: string;
  color?: string;
  markX?: number; // optional vertical marker (e.g. recovered period)
  markLabel?: string;
}

const PAD = { top: 12, right: 16, bottom: 34, left: 56 };

export default function LineChart({
  x,
  y,
  width = 440,
  height = 220,
  xLabel,
  yLabel,
  color = "#5ec9ff",
  markX,
  markLabel,
}: LineChartProps) {
  const { path, xTicks, yTicks, markPx } = useMemo(() => {
    if (x.length === 0 || y.length === 0) {
      return { path: "", xTicks: [], yTicks: [], markPx: null as number | null };
    }
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

    const d = x.map((xv, i) => `${i === 0 ? "M" : "L"} ${sx(xv).toFixed(2)} ${sy(y[i]).toFixed(2)}`).join(" ");

    const xTickVals = [xMin, xMin + (xMax - xMin) / 2, xMax];
    const yTickVals = [y0 + (y1 - y0) * 0.1, y0 + (y1 - y0) * 0.5, y0 + (y1 - y0) * 0.9];

    return {
      path: d,
      xTicks: xTickVals.map((v) => ({ v, px: sx(v) })),
      yTicks: yTickVals.map((v) => ({ v, px: sy(v) })),
      markPx: markX !== undefined ? sx(markX) : null,
    };
  }, [x, y, width, height, markX]);

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="linechart" role="img" aria-label={`${yLabel} vs ${xLabel}`}>
      <line x1={PAD.left} y1={PAD.top} x2={PAD.left} y2={height - PAD.bottom} stroke="var(--border)" />
      <line x1={PAD.left} y1={height - PAD.bottom} x2={width - PAD.right} y2={height - PAD.bottom} stroke="var(--border)" />
      {yTicks.map((t, i) => (
        <text key={i} x={PAD.left - 8} y={t.px + 4} textAnchor="end" fontSize="10" fill="var(--text-dim)">
          {t.v.toPrecision(3)}
        </text>
      ))}
      {xTicks.map((t, i) => (
        <text key={i} x={t.px} y={height - PAD.bottom + 16} textAnchor="middle" fontSize="10" fill="var(--text-dim)">
          {t.v.toPrecision(4)}
        </text>
      ))}
      {markPx !== null && (
        <>
          <line x1={markPx} y1={PAD.top} x2={markPx} y2={height - PAD.bottom} stroke="var(--accent)" strokeDasharray="3 3" />
          {markLabel && (
            <text x={markPx} y={PAD.top - 2} textAnchor="middle" fontSize="10" fill="var(--accent)">
              {markLabel}
            </text>
          )}
        </>
      )}
      <path d={path} fill="none" stroke={color} strokeWidth="1.6" />
      <text x={width / 2} y={height - 4} textAnchor="middle" fontSize="11" fill="var(--text-dim)">
        {xLabel}
      </text>
      <text
        x={12}
        y={height / 2}
        textAnchor="middle"
        fontSize="11"
        fill="var(--text-dim)"
        transform={`rotate(-90 12 ${height / 2})`}
      >
        {yLabel}
      </text>
    </svg>
  );
}
