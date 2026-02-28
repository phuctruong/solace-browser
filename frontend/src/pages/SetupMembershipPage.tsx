import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { createStripeSession, getMembershipPlans } from "../services/solaceagiClient";
import type { MembershipPlan } from "../services/solaceagiClient";
import { useSessionStore } from "../state/useSessionStore";
import { MEMBERSHIP_PLANS } from "../utils/constants";

function planLabel(plan: MembershipPlan): string {
  return `${plan.name} ${plan.priceLabel}`.trim();
}

export function SetupMembershipPage(): JSX.Element {
  const navigate = useNavigate();
  const session = useSessionStore((state) => state.session);
  const setSession = useSessionStore((state) => state.setSession);
  const [plans, setPlans] = useState<MembershipPlan[]>(MEMBERSHIP_PLANS);
  const [selectedPlan, setSelectedPlan] = useState<string>("pro");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function loadPlans(): Promise<void> {
      try {
        const nextPlans = await getMembershipPlans();
        if (!active) {
          return;
        }
        setPlans(nextPlans);
        if (!nextPlans.some((plan) => plan.id === selectedPlan)) {
          setSelectedPlan(nextPlans.find((plan) => plan.current)?.id ?? nextPlans[0]?.id ?? "pro");
        }
      } catch (err) {
        if (!active) {
          return;
        }
        setError(err instanceof Error ? err.message : "Failed to load billing plans");
      }
    }

    void loadPlans();
    return () => {
      active = false;
    };
  }, []);

  async function upgrade(): Promise<void> {
    if (!session) {
      navigate("/login");
      return;
    }

    const activePlan = plans.find((plan) => plan.id === selectedPlan) ?? plans[0];
    if (!activePlan) {
      setError("No plan selected");
      return;
    }

    setError(null);
    try {
      await createStripeSession(planLabel(activePlan));
      setSession({
        ...session,
        membershipTier: planLabel(activePlan),
        creditsUsd: 5,
      });
      navigate("/home");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Checkout failed");
    }
  }

  return (
    <section className="setup-page">
      <div className="hero-panel">
        <div>
          <p className="eyebrow">Membership</p>
          <h2>Select your plan</h2>
          <p>Choose the review lane and billing path that matches how much browser work you want to automate.</p>
        </div>
      </div>

      {error ? <p role="alert">{error}</p> : null}

      <div className="detail-grid plan-grid">
        {plans.map((plan) => (
          <article key={plan.id} className={`detail-card selectable-card ${selectedPlan === plan.id ? "selected-card" : ""}`}>
            <div className="plan-header">
              <div>
                <h3>{plan.name}</h3>
                <p>{plan.priceLabel}</p>
                <p>{planLabel(plan)}</p>
              </div>
              {plan.current ? <span className="badge">Current</span> : null}
            </div>
            <ul className="approval-list">
              {plan.features.map((feature) => (
                <li key={feature}>{feature}</li>
              ))}
            </ul>
            <label>
              <input
                type="radio"
                name="membership"
                checked={selectedPlan === plan.id}
                onChange={() => setSelectedPlan(plan.id)}
              />
              Select {plan.name}
            </label>
          </article>
        ))}
      </div>

      <div className="actions">
        <button type="button" onClick={() => void upgrade()}>
          Pay & Unlock Apps
        </button>
        <button type="button" onClick={() => window.location.assign("mailto:sales@solaceagi.com")}>
          Contact Sales
        </button>
      </div>
    </section>
  );
}
