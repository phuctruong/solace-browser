import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createStripeSession } from "../services/solaceagiClient";
import { useSessionStore } from "../state/useSessionStore";

const TIERS = ["Dragon Warrior $8/month", "Dragon Warrior $80/year", "Enterprise $99/month"];

export function SetupMembershipPage(): JSX.Element {
  const [tier, setTier] = useState<string>(TIERS[0]);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  const session = useSessionStore((s) => s.session);
  const setSession = useSessionStore((s) => s.setSession);

  async function pay(): Promise<void> {
    if (!session) {
      navigate("/login");
      return;
    }
    setError(null);
    try {
      await createStripeSession(tier);
      setSession({ ...session, membershipTier: tier, creditsUsd: 5 });
      navigate("/home");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Payment failed");
    }
  }

  return (
    <section>
      <h2>Select Membership</h2>
      {TIERS.map((value) => (
        <label key={value}>
          <input type="radio" name="tier" checked={tier === value} onChange={() => setTier(value)} />
          {value}
        </label>
      ))}
      <p>Including $5 monthly credits for LLM calls</p>
      <button type="button" onClick={pay}>Pay & Unlock Apps</button>
      {error ? <p role="alert">{error}</p> : null}
    </section>
  );
}
