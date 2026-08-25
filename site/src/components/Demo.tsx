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
  if (!v) return "—";
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
          <div className="picker-group-label">Validation systems</div>
          <div className="picker-buttons">
            {validationTargets.map((t) => (
              <button
                key={t.slug}
                className={`pick-btn ${selected === t.slug ? "active" : ""}`}
                onClick={() => setSelected(t.slug)}
              >
                {t.name}
              </button>
            ))}
          </div>
        </div>
        <div className="picker-group">
          <div className="picker-group-label">Unconfirmed TESS candidates</div>
          <div className="picker-buttons">
            {discoveryTargets.map((t) => (
              <button
                key={t.slug}
                className={`pick-btn ${selected === t.slug ? "active" : ""}`}
                onClick={() => setSelected(t.slug)}
              >
                {t.name}
              </button>
            ))}
          </div>
        </div>
      </div>

      {loading && <p className="demo-status">Loading…</p>}

      {data && !loading && (
        <div className="demo-body">
          <h3>{data.name}</h3>
          <p className="demo-headline">{data.headline}</p>

          <div className="chart-row">
            <div className="card chart-card">
              <div className="chart-title">Real light curve, phase-folded</div>
              <LineChart
                x={data.phase_hours}
                y={data.folded_flux}
                xLabel="Hours from mid-transit"
                yLabel="Normalized flux"
                color="#5ec9ff"
              />
            </div>
            <div className="card chart-card">
              <div className="chart-title">BLS periodogram (bounded search)</div>
              <LineChart
                x={data.periodogram_period}
                y={data.periodogram_power}
                xLabel="Period (days)"
                yLabel="Power"
                color="#ffb454"
                markX={data.recovered_period ?? data.catalog_period}
                markLabel="recovered"
              />
            </div>
          </div>

          {data.category === "validation" ? (
            <div className="card verdict-card">
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
                  <div className="verdict-val">{data.error_percent !== undefined ? `${data.error_percent > 0 ? "+" : ""}${data.error_percent.toFixed(3)}%` : "—"}</div>
                </div>
                <div>
                  <div className="verdict-label">System total</div>
                  <div className="verdict-val">{data.n_planets_recovered}/{data.n_planets_total} recovered</div>
                </div>
              </div>
            </div>
          ) : (
            <div className="card verdict-card">
              <div className="verdict-row">
                <div>
                  <div className="verdict-label">Independently recovered</div>
                  <div className="verdict-val">
                    {data.recovered_by_pipeline ? (
                      <span className="tag tag-good">yes, by our BLS</span>
                    ) : (
                      <span className="tag tag-bad">no, catalog depth used</span>
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
              <div className="caveat demo-caveat">
                <strong>Not a confirmed planet.</strong> {data.caveat}
              </div>
            </div>
          )}
        </div>
      )}

      <style>{`
        .demo-status { color: var(--text-dim); padding: 20px 0; }
        .picker { display: flex; flex-direction: column; gap: 16px; margin-bottom: 28px; }
        .picker-group-label { font-size: 0.82rem; color: var(--text-dim); margin-bottom: 8px; }
        .picker-buttons { display: flex; flex-wrap: wrap; gap: 8px; }
        .pick-btn {
          background: var(--bg-panel);
          border: 1px solid var(--border);
          color: var(--text);
          padding: 8px 14px;
          border-radius: 999px;
          font-size: 0.86rem;
          cursor: pointer;
          transition: all 0.15s ease;
        }
        .pick-btn:hover { border-color: var(--accent-2); }
        .pick-btn.active { background: var(--accent-2); border-color: var(--accent-2); color: #0b0e17; font-weight: 600; }
        .demo-body h3 { margin-bottom: 2px; }
        .demo-headline { color: var(--text-dim); margin-bottom: 20px; }
        .chart-row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 20px; }
        .chart-card { padding: 16px; }
        .chart-title { font-size: 0.82rem; color: var(--text-dim); margin-bottom: 10px; }
        .linechart { width: 100%; height: auto; }
        .verdict-card { padding: 20px 24px; }
        .verdict-row { display: flex; flex-wrap: wrap; gap: 24px; }
        .verdict-label { font-size: 0.78rem; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.03em; margin-bottom: 4px; }
        .verdict-val { font-size: 1.05rem; font-weight: 600; font-variant-numeric: tabular-nums; }
        .demo-caveat { margin-top: 18px; }

        @media (max-width: 640px) {
          .chart-row { grid-template-columns: 1fr; }
        }
      `}</style>
    </div>
  );
}
