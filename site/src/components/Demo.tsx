import { useEffect, useState } from "react";
import LineChart from "./LineChart";

interface ManifestEntry {
  slug: string;
  name: string;
  category: "validation" | "discovery";
  headline: string;
}

interface TargetData {
  slug: string;
  name: string;
  category: string;
  headline: string;
  phase_hours: number[];
  folded_flux: number[];
  periodogram_period: number[];
  periodogram_power: number[];
  // validation-only
  published_period?: number;
  recovered_period?: number;
  error_percent?: number;
  n_planets_recovered?: number;
  n_planets_total?: number;
  // discovery-only
  catalog_period?: number;
  recovered_by_pipeline?: boolean;
  planet_radius_re?: [number, number, number];
  semi_major_axis_au?: [number, number, number];
  eq_temp_k?: [number, number, number];
  hz_verdict?: string;
  caveat?: string;
}

function fmtRange(v?: [number, number, number], unit = "") {
  if (!v) return "–";
  return `${v[0].toFixed(2)}${unit} (${v[1].toFixed(2)}–${v[2].toFixed(2)})`;
}

export default function Demo() {
  const [manifest, setManifest] = useState<ManifestEntry[] | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [data, setData] = useState<TargetData | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetch("/data/manifest.json")
      .then((r) => r.json())
      .then((m: ManifestEntry[]) => {
        setManifest(m);
        if (m.length > 0) setSelected(m[0].slug);
      })
      .catch(() => setManifest([]));
  }, []);

  useEffect(() => {
    if (!selected) return;
    setLoading(true);
    fetch(`/data/${selected}.json`)
      .then((r) => r.json())
      .then((d: TargetData) => setData(d))
      .finally(() => setLoading(false));
  }, [selected]);

  if (manifest === null) {
    return <p className="demo-status">Loading targets…</p>;
  }
  if (manifest.length === 0) {
    return <p className="demo-status">Demo data not available yet.</p>;
  }

  const validationTargets = manifest.filter((m) => m.category === "validation");
  const discoveryTargets = manifest.filter((m) => m.category === "discovery");

  return (
    <div className="demo">
      <div className="picker">
        <div className="picker-group">
          <span className="picker-group-label">Validation systems</span>
          {validationTargets.map((t, i) => (
            <span key={t.slug}>
              {i > 0 && <span className="sep">·</span>}
              <button className={`pick-link ${selected === t.slug ? "active" : ""}`} onClick={() => setSelected(t.slug)}>
                {t.name}
              </button>
            </span>
          ))}
        </div>
        <div className="picker-group">
          <span className="picker-group-label">Unconfirmed TESS candidates</span>
          {discoveryTargets.map((t, i) => (
            <span key={t.slug}>
              {i > 0 && <span className="sep">·</span>}
              <button className={`pick-link ${selected === t.slug ? "active" : ""}`} onClick={() => setSelected(t.slug)}>
                {t.name}
              </button>
            </span>
          ))}
        </div>
      </div>

      {loading && <p className="demo-status">Loading…</p>}

      {data && !loading && (
        <div className="demo-body">
          <h3>{data.name}</h3>
          <p className="demo-headline">{data.headline}</p>

          <div className="chart-row">
            <figure className="chart-figure">
              <figcaption>Real light curve, phase-folded</figcaption>
              <LineChart
                x={data.phase_hours}
                y={data.folded_flux}
                xLabel="Hours from mid-transit"
                yLabel="Normalized flux"
                variant="primary"
              />
            </figure>
            <figure className="chart-figure">
              <figcaption>BLS periodogram (bounded search)</figcaption>
              <LineChart
                x={data.periodogram_period}
                y={data.periodogram_power}
                xLabel="Period (days)"
                yLabel="Power"
                variant="secondary"
                markX={data.recovered_period ?? data.catalog_period}
                markLabel="recovered"
              />
            </figure>
          </div>

          {data.category === "validation" ? (
            <div className="verdict">
              <div className="verdict-row">
                <div>
                  <div className="verdict-label">Published period</div>
                  <div className="verdict-val">{data.published_period?.toFixed(6)} d</div>
                </div>
                <div>
                  <div className="verdict-label">Recovered period</div>
                  <div className="verdict-val">{data.recovered_period?.toFixed(6)} d</div>
                </div>
                <div>
                  <div className="verdict-label">Error</div>
                  <div className="verdict-val">{data.error_percent !== undefined ? `${data.error_percent > 0 ? "+" : ""}${data.error_percent.toFixed(3)}%` : "–"}</div>
                </div>
                <div>
                  <div className="verdict-label">System total</div>
                  <div className="verdict-val">{data.n_planets_recovered}/{data.n_planets_total} recovered</div>
                </div>
              </div>
            </div>
          ) : (
            <div className="verdict">
              <div className="verdict-row">
                <div>
                  <div className="verdict-label">Independently recovered</div>
                  <div className="verdict-val">
                    {data.recovered_by_pipeline ? (
                      <span className="mark mark-good">✓ yes, by our BLS</span>
                    ) : (
                      <span className="mark mark-bad">✗ no, catalog depth used</span>
                    )}
                  </div>
                </div>
                <div>
                  <div className="verdict-label">Planet radius</div>
                  <div className="verdict-val">{fmtRange(data.planet_radius_re, " R⊕")}</div>
                </div>
                <div>
                  <div className="verdict-label">Orbital distance</div>
                  <div className="verdict-val">{fmtRange(data.semi_major_axis_au, " AU")}</div>
                </div>
                <div>
                  <div className="verdict-label">Equilibrium temp.</div>
                  <div className="verdict-val">{fmtRange(data.eq_temp_k, " K")}</div>
                </div>
                <div>
                  <div className="verdict-label">Habitable zone</div>
                  <div className="verdict-val">{data.hz_verdict}</div>
                </div>
              </div>
              <p className="caveat demo-caveat">
                <strong>Not a confirmed planet.</strong> {data.caveat}
              </p>
            </div>
          )}
        </div>
      )}

      <style>{`
        .demo-status { color: var(--ink-dim); padding: 20px 0; }
        .picker { margin-bottom: 36px; }
        .picker-group { margin-bottom: 10px; line-height: 2.2; }
        .picker-group-label {
          font-family: var(--font-mono);
          font-size: 0.72rem;
          text-transform: uppercase;
          letter-spacing: 0.05em;
          color: var(--ink-faint);
          margin-right: 14px;
        }
        .sep { color: var(--ink-faint); margin: 0 8px; }
        .pick-link {
          background: none;
          border: none;
          padding: 0;
          font-family: var(--font-serif);
          font-size: 1.02rem;
          color: var(--ink-dim);
          cursor: pointer;
          text-decoration: underline;
          text-decoration-color: transparent;
          text-underline-offset: 3px;
          transition: color 180ms ease-out, text-decoration-color 180ms ease-out;
        }
        .pick-link:hover { color: var(--ink); text-decoration-color: var(--rule-strong); }
        .pick-link:active { transform: translateY(1px); }
        .pick-link.active { color: var(--accent); font-weight: 600; text-decoration-color: var(--accent); }
        .demo-body h3 { margin-bottom: 2px; font-style: italic; }
        .demo-headline { color: var(--ink-dim); margin-bottom: 24px; }
        .chart-row { display: grid; grid-template-columns: 1fr 1fr; gap: 32px; margin-bottom: 32px; }
        .chart-figure figcaption {
          font-family: var(--font-mono);
          font-size: 0.72rem;
          text-transform: uppercase;
          letter-spacing: 0.04em;
          color: var(--ink-faint);
          margin: 0 0 10px;
        }
        .linechart { width: 100%; height: auto; }
        .verdict { border-top: 1px solid var(--rule); padding-top: 20px; }
        .verdict-row { display: flex; flex-wrap: wrap; gap: 28px; }
        .verdict-label {
          font-family: var(--font-mono);
          font-size: 0.7rem;
          color: var(--ink-faint);
          text-transform: uppercase;
          letter-spacing: 0.04em;
          margin-bottom: 5px;
        }
        .verdict-val {
          font-family: var(--font-mono);
          font-size: 1rem;
          font-variant-numeric: tabular-nums;
          color: var(--ink);
        }
        .demo-caveat { margin-top: 18px; margin-bottom: 0; }

        @media (max-width: 640px) {
          .chart-row { grid-template-columns: 1fr; }
        }
      `}</style>
    </div>
  );
}
