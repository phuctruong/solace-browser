import type { FormEvent } from "react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { GoogleAuthProvider, createUserWithEmailAndPassword, getAuth, signInWithPopup } from "firebase/auth";
import { registerBrowser } from "../services/solaceagiClient";
import { encryptSecret } from "../services/vault";
import { useSessionStore } from "../state/useSessionStore";
import { STORAGE_KEYS } from "../utils/constants";
import { saveJson } from "../utils/storage";

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function LoginPage(): JSX.Element {
  const navigate = useNavigate();
  const setSession = useSessionStore((state) => state.setSession);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function completeLogin(uid: string, accountEmail: string): Promise<void> {
    const registration = await registerBrowser(uid, accountEmail);
    const encrypted = await encryptSecret(registration.apiKey, uid);
    saveJson(STORAGE_KEYS.VAULT, {
      user: uid,
      payload: encrypted,
      deviceId: registration.deviceId,
    });
    setSession({
      uid,
      email: accountEmail,
      apiKey: registration.apiKey,
      membershipTier: undefined,
      creditsUsd: 0,
      connectedApps: ["solace"],
    });
    navigate("/setup/llm-choice");
  }

  async function handleGoogle(): Promise<void> {
    setLoading(true);
    setError(null);
    try {
      const auth = getAuth();
      const credential = await signInWithPopup(auth, new GoogleAuthProvider());
      await completeLogin(credential.user.uid, credential.user.email ?? "");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Google sign-in failed");
    } finally {
      setLoading(false);
    }
  }

  async function handleEmailSignup(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!EMAIL_PATTERN.test(email)) {
      setError("Enter a valid email address.");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const auth = getAuth();
      const credential = await createUserWithEmailAndPassword(auth, email, password);
      await completeLogin(credential.user.uid, credential.user.email ?? email);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Email sign-up failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="auth-page">
      <div className="hero-panel">
        <div>
          <p className="eyebrow">Identity</p>
          <h2>Login</h2>
          <p>Authenticate with Google or create an email account to unlock the browser workspace.</p>
        </div>
      </div>

      <div className="auth-grid">
        <article className="auth-card">
          <h3>Google sign-in</h3>
          <p>Use Firebase popup auth and redirect back into the setup flow after a successful browser registration.</p>
          <button type="button" onClick={() => void handleGoogle()} disabled={loading}>
            Continue with Google
          </button>
        </article>

        <article className="auth-card">
          <h3>Email account</h3>
          <form onSubmit={(event) => void handleEmailSignup(event)}>
            <label htmlFor="email-address">Email address</label>
            <input
              id="email-address"
              aria-label="Email address"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@example.com"
            />

            <label htmlFor="password">Password</label>
            <input
              id="password"
              aria-label="Password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Minimum 8 characters"
            />

            <button type="submit" disabled={loading}>
              Create account
            </button>
          </form>
        </article>
      </div>

      {loading ? <p aria-live="polite">Loading authentication state...</p> : null}
      {error ? <p role="alert">{error}</p> : null}
    </section>
  );
}
