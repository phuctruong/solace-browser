import { Link } from "react-router-dom";
import { formatUsd } from "../utils/formatting";

interface HeaderProps {
  authenticated: boolean;
  creditsUsd: number;
}

export function Header({ authenticated, creditsUsd }: HeaderProps): JSX.Element {
  return (
    <header className="header">
      <Link to="/home" className="brand">
        Solace Browser
      </Link>
      <nav>
        <Link to="/setup/llm-choice">LLM Setup</Link>
      </nav>
      <div>{authenticated ? `${formatUsd(creditsUsd)} credits` : "Guest mode"}</div>
    </header>
  );
}
