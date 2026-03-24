import { type FormEvent, useEffect, useState } from "react";

import TanakhScenePanel from "./TanakhScenePanel";

type Props = {
  payload: any;
  liveEnabled: boolean;
  canRun: boolean;
  running: boolean;
  onRun: (request: any) => Promise<void>;
};

function shortHash(value: string | undefined): string {
  if (!value) return "—";
  return value.slice(0, 12);
}

export default function TanakhPanel({ payload, liveEnabled, canRun, running, onRun }: Props) {
  const bundle = payload?.bundle ?? {};
  const scene = bundle.scene ?? {};
  const passage = bundle.passage ?? {};
  const analyses = bundle.analyses ?? {};
  const validation = bundle.validation ?? {};
  const [ref, setRef] = useState(payload?.current_ref ?? "Ezek 1");
  const [preprocess, setPreprocess] = useState(bundle.params?.preprocess ?? "strip_pointing");
  const [gematriaScheme, setGematriaScheme] = useState(bundle.params?.gematria_scheme ?? "mispar_hechrechi");
  const [notarikonMode, setNotarikonMode] = useState(bundle.params?.notarikon_mode ?? "first_letter");
  const [theme, setTheme] = useState(bundle.params?.scene?.theme ?? "amber");
  const [seed, setSeed] = useState(String(bundle.params?.scene?.seed ?? 11));
  const [letterAngle, setLetterAngle] = useState(String(bundle.params?.scene?.letter_angle ?? 0.14));
  const [wordRadius, setWordRadius] = useState(String(bundle.params?.scene?.word_radius ?? 0.22));
  const [verseHeight, setVerseHeight] = useState(String(bundle.params?.scene?.verse_height ?? 1.1));
  const [oscillationAmplitude, setOscillationAmplitude] = useState(String(bundle.params?.scene?.oscillation_amplitude ?? 0.18));
  const [showDebugJson, setShowDebugJson] = useState(false);

  useEffect(() => {
    setRef(payload?.current_ref ?? "Ezek 1");
    setPreprocess(bundle.params?.preprocess ?? "strip_pointing");
    setGematriaScheme(bundle.params?.gematria_scheme ?? "mispar_hechrechi");
    setNotarikonMode(bundle.params?.notarikon_mode ?? "first_letter");
    setTheme(bundle.params?.scene?.theme ?? "amber");
    setSeed(String(bundle.params?.scene?.seed ?? 11));
    setLetterAngle(String(bundle.params?.scene?.letter_angle ?? 0.14));
    setWordRadius(String(bundle.params?.scene?.word_radius ?? 0.22));
    setVerseHeight(String(bundle.params?.scene?.verse_height ?? 1.1));
    setOscillationAmplitude(String(bundle.params?.scene?.oscillation_amplitude ?? 0.18));
    setShowDebugJson(false);
  }, [bundle.params, payload?.current_ref]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canRun) return;
    await onRun({
      ref,
      params: {
        preprocess,
        gematria_scheme: gematriaScheme,
        notarikon_mode: notarikonMode,
        temurah_mapping: "atbash",
        scene: {
          theme,
          seed: Number(seed),
          letter_angle: Number(letterAngle),
          word_radius: Number(wordRadius),
          verse_height: Number(verseHeight),
          oscillation_amplitude: Number(oscillationAmplitude),
        },
      },
    });
  }

  return (
    <div className="tanakh-surface">
      <form className="tanakh-controls" onSubmit={handleSubmit}>
        <label>
          <span>Reference</span>
          <input onChange={(event) => setRef(event.target.value)} value={ref} />
        </label>
        <label>
          <span>Preprocess</span>
          <select onChange={(event) => setPreprocess(event.target.value)} value={preprocess}>
            <option value="strip_pointing">Strip pointing</option>
            <option value="keep_vowels">Keep vowels</option>
            <option value="keep_cantillation">Keep cantillation</option>
          </select>
        </label>
        <label>
          <span>Gematria</span>
          <select onChange={(event) => setGematriaScheme(event.target.value)} value={gematriaScheme}>
            <option value="mispar_hechrechi">Mispar hechrechi</option>
            <option value="mispar_gadol">Mispar gadol</option>
          </select>
        </label>
        <label>
          <span>Notarikon</span>
          <select onChange={(event) => setNotarikonMode(event.target.value)} value={notarikonMode}>
            <option value="first_letter">First letter</option>
            <option value="last_letter">Last letter</option>
          </select>
        </label>
        <label>
          <span>Theme</span>
          <select onChange={(event) => setTheme(event.target.value)} value={theme}>
            <option value="amber">Amber</option>
            <option value="brass">Brass</option>
            <option value="sea">Sea</option>
          </select>
        </label>
        <label>
          <span>Seed</span>
          <input onChange={(event) => setSeed(event.target.value)} value={seed} />
        </label>
        <label>
          <span>Letter angle</span>
          <input onChange={(event) => setLetterAngle(event.target.value)} value={letterAngle} />
        </label>
        <label>
          <span>Word radius</span>
          <input onChange={(event) => setWordRadius(event.target.value)} value={wordRadius} />
        </label>
        <label>
          <span>Verse height</span>
          <input onChange={(event) => setVerseHeight(event.target.value)} value={verseHeight} />
        </label>
        <label>
          <span>Oscillation</span>
          <input onChange={(event) => setOscillationAmplitude(event.target.value)} value={oscillationAmplitude} />
        </label>
        <button className="toolbar-button is-active" disabled={!canRun || running} type="submit">
          {running ? "Running..." : canRun ? "Run Tanakh analysis" : "Live server required"}
        </button>
      </form>
      <p className="placeholder-copy">
        {canRun
          ? "Running Tanakh analysis refreshes derived sidecars only. It does not write measurement events or commit graph mutation."
          : "Static export keeps the Tanakh reader and derived artifacts visible, but live re-runs are disabled without the observatory server."}
      </p>

      <div className="toolbar toolbar-badges">
        <span className="badge badge-observed">Canonical text</span>
        <span className="badge badge-derived">Derived scene</span>
        <span className="badge badge-derived">Dataset {bundle.manifest?.dataset_id ?? "—"}</span>
        <span className="badge badge-warning">Layout != evidence</span>
      </div>

      <div className="tanakh-grid">
        <section className="tanakh-card tanakh-reader-card">
          <header>
            <h2>{payload?.current_ref ?? "Tanakh surface"}</h2>
            <p>Canonical reader stays DOM/CSS. Derived preprocess output is shown alongside it.</p>
          </header>
          <div className="tanakh-provenance-row">
            <span>Bundle hash {shortHash(payload?.bundle_hash)}</span>
            <span>Scene hash {shortHash(scene.scene_hash)}</span>
            <span>{canRun ? "Live API enabled" : "Static export only"}</span>
          </div>
          <article className="tanakh-reader" dir="rtl" lang="he">
            {(passage.verses ?? []).map((verse: any) => (
              <div key={verse.ref} className="tanakh-verse">
                <span className="tanakh-verse-ref">{verse.ref}</span>
                <div className="tanakh-verse-text">{verse.canonical_text}</div>
                <div className="tanakh-verse-processed">{verse.processed?.text}</div>
              </div>
            ))}
          </article>
        </section>

        <section className="tanakh-card tanakh-analysis-card">
          <header>
            <h2>Analyzer outputs</h2>
            <p>Every card is derived and provenance-bearing.</p>
          </header>
          <div className="tanakh-analysis-stack">
            <div className="tanakh-analysis-item">
              <strong>Gematria</strong>
              <div>Total {analyses.gematria?.total ?? "—"}</div>
              <div>Scheme {analyses.gematria?.scheme ?? "—"}</div>
              <div>Hash {shortHash(analyses.gematria?.output_hash)}</div>
            </div>
            <div className="tanakh-analysis-item">
              <strong>Notarikon</strong>
              <div>{analyses.notarikon?.result ?? "—"}</div>
              <div>Mode {analyses.notarikon?.mode ?? "—"}</div>
              <div>Hash {shortHash(analyses.notarikon?.output_hash)}</div>
            </div>
            <div className="tanakh-analysis-item">
              <strong>Temurah</strong>
              <div className="analysis-result">{analyses.temurah?.result ?? "—"}</div>
              <div>Mapping {analyses.temurah?.mapping ?? "—"}</div>
              <div>Hash {shortHash(analyses.temurah?.output_hash)}</div>
            </div>
          </div>
        </section>

        <section className="tanakh-card tanakh-scene-card">
          <header>
            <h2>Merkavah scene</h2>
            <p>Derived visualization only. Node ids map back to citation spans in the JSON artifact.</p>
          </header>
          <TanakhScenePanel scene={scene} />
        </section>

        <section className="tanakh-card tanakh-debug-card">
          <header>
            <h2>Provenance and debug</h2>
            <p>Static files are the audit surface; reveal full JSON only when artifact-level provenance is needed.</p>
          </header>
          <dl className="metric-list">
            <div className="metric-row">
              <dt>Validation</dt>
              <dd>{validation.comparison_status ?? "—"}</dd>
            </div>
            <div className="metric-row">
              <dt>Validation hash</dt>
              <dd>{shortHash(validation.report_hash)}</dd>
            </div>
            <div className="metric-row">
              <dt>Source hash</dt>
              <dd>{shortHash(bundle.manifest?.archive_sha256)}</dd>
            </div>
            <div className="metric-row">
              <dt>Build</dt>
              <dd>{bundle.manifest?.build ?? "—"}</dd>
            </div>
          </dl>
          <div className="json-preview">
            <div className="json-preview-toolbar">
              <dl className="metric-list">
                <div className="metric-row">
                  <dt>Artifact entries</dt>
                  <dd>{Array.isArray(payload?.artifacts) ? payload.artifacts.length : payload?.artifacts ? Object.keys(payload.artifacts).length : 0}</dd>
                </div>
                <div className="metric-row">
                  <dt>Validation cases</dt>
                  <dd>{Array.isArray(validation.cases) ? validation.cases.length : validation.cases ? Object.keys(validation.cases).length : 0}</dd>
                </div>
              </dl>
              <button className="toolbar-button" onClick={() => setShowDebugJson((current) => !current)} type="button">
                {showDebugJson ? "Hide Debug JSON" : "Show Debug JSON"}
              </button>
            </div>
            {showDebugJson ? (
              <pre className="debug-json">{JSON.stringify({ artifacts: payload?.artifacts, validation: validation.cases }, null, 2)}</pre>
            ) : (
              <p className="placeholder-copy">Debug JSON stays hidden until you explicitly reveal the Tanakh artifact payload.</p>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
