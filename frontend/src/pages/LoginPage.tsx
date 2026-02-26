import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { registerBrowser } from "../services/solaceagiClient";
import { signInWithPopup } from "../services/firebaseAuth";
import { encryptSecret } from "../services/vault";
import { STORAGE_KEYS } from "../utils/constants";
import { saveJson } from "../utils/storage";
import { useSessionStore } from "../state/useSessionStore";

export function LoginPage(): JSX.Element {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  const setSession = useSessionStore((s) => s.setSession);

  async function startLogin(provider: "gmail" | "github"): Promise<void> {
    setLoading(true);
    setError(null);
    try {
      const auth = await signInWithPopup(provider);
      const registration = await registerBrowser(auth.uid, auth.email);
      const encrypted = await encryptSecret(registration.apiKey, auth.uid);
      saveJson(STORAGE_KEYS.VAULT, {
        user: auth.uid,
        payload: encrypted,
        deviceId: registration.deviceId,
      });
      setSession({
        uid: auth.uid,
        email: auth.email,
        apiKey: registration.apiKey,
        creditsUsd: 0,
        connectedApps: ["solace"],
      });
      navigate("/setup/llm-choice");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section>
      <h2>Login</h2>
      <p>Sign in with Solace to unlock apps.</p>
      <button type="button" disabled={loading} onClick={() => startLogin("gmail")}>
        Continue with Gmail
      </button>
      <button type="button" disabled={loading} onClick={() => startLogin("github")}>
        Continue with GitHub
      </button>
      {error ? <p role="alert">{error}</p> : null}
    </section>
  );
}
