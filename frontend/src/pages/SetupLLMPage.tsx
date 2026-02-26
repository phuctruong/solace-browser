import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { setByokKey } from "../services/solaceagiClient";

export function SetupLLMPage(): JSX.Element {
  const [mode, setMode] = useState<"byok" | "managed" | null>(null);
  const [apiKey, setApiKey] = useState("");
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  async function proceed(): Promise<void> {
    setError(null);
    try {
      if (mode === "byok") {
        await setByokKey(apiKey);
      }
      navigate("/setup/membership");
    } catch (e) {
      setError(e instanceof Error ? e.message : "LLM configuration failed");
    }
  }

  return (
    <section>
      <h2>Choose LLM Mode</h2>
      <label>
        <input type="radio" name="llm" checked={mode === "byok"} onChange={() => setMode("byok")} />
        BYOK
      </label>
      <label>
        <input type="radio" name="llm" checked={mode === "managed"} onChange={() => setMode("managed")} />
        Managed
      </label>
      {mode === "byok" ? (
        <input
          aria-label="API key"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          placeholder="sk-..."
        />
      ) : null}
      <button type="button" onClick={proceed} disabled={!mode || (mode === "byok" && apiKey.length < 6)}>
        Continue
      </button>
      {error ? <p role="alert">{error}</p> : null}
    </section>
  );
}
