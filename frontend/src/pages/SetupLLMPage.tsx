import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { setByokKey } from "../services/solaceagiClient";

type LlmMode = "byok" | "managed" | null;

export function SetupLLMPage(): JSX.Element {
  const navigate = useNavigate();
  const [mode, setMode] = useState<LlmMode>(null);
  const [apiKey, setApiKey] = useState("");
  const [validationMessage, setValidationMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function continueFlow(): Promise<void> {
    if (!mode) {
      return;
    }
    setSaving(true);
    setError(null);
    setValidationMessage(null);
    try {
      if (mode === "byok") {
        await setByokKey(apiKey);
        setValidationMessage("API key validated.");
      }
      navigate("/setup/membership");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Validation failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="setup-page">
      <div className="hero-panel">
        <div>
          <p className="eyebrow">LLM Setup</p>
          <h2>Choose your inference mode</h2>
          <p>Validate a private API key or keep managed routing so every task can estimate cost before execution.</p>
        </div>
      </div>

      {error ? <p role="alert">{error}</p> : null}

      <div className="detail-grid">
        <article className={`detail-card selectable-card ${mode === "byok" ? "selected-card" : ""}`}>
          <label>
            <input type="radio" name="llm" checked={mode === "byok"} onChange={() => setMode("byok")} />
            BYOK
          </label>
          <p>Use your own provider key and validate it against the OAuth3 token endpoint.</p>
          {mode === "byok" ? (
            <input
              aria-label="API key"
              value={apiKey}
              onChange={(event) => setApiKey(event.target.value)}
              placeholder="sk-..."
            />
          ) : null}
        </article>

        <article className={`detail-card selectable-card ${mode === "managed" ? "selected-card" : ""}`}>
          <label>
            <input type="radio" name="llm" checked={mode === "managed"} onChange={() => setMode("managed")} />
            Managed
          </label>
          <p>Together.ai routing with a fixed $3/mo managed layer for browser-safe task execution.</p>
          <p>Best for shared workspaces and teams who want one predictable cost path.</p>
        </article>
      </div>

      {validationMessage ? <p>{validationMessage}</p> : null}

      <div className="actions">
        <button
          type="button"
          onClick={() => void continueFlow()}
          disabled={saving || mode === null || (mode === "byok" && apiKey.length < 6)}
        >
          Continue
        </button>
      </div>
    </section>
  );
}
