import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Header } from "./components/Header";
import { AppDetailPage } from "./pages/AppDetailPage";
import { HomePage } from "./pages/HomePage";
import { LoginPage } from "./pages/LoginPage";
import { RunDetailPage } from "./pages/RunDetailPage";
import { SetupLLMPage } from "./pages/SetupLLMPage";
import { SetupMembershipPage } from "./pages/SetupMembershipPage";
import { useSessionStore } from "./state/useSessionStore";

import "./App.css";

export default function App(): JSX.Element {
  const session = useSessionStore((s) => s.session);
  return (
    <BrowserRouter>
      <div className="layout">
        <Header authenticated={Boolean(session)} creditsUsd={session?.creditsUsd ?? 0} />
        <main>
          <Routes>
            <Route path="/" element={<Navigate to="/home" replace />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/setup/llm-choice" element={<SetupLLMPage />} />
            <Route path="/setup/membership" element={<SetupMembershipPage />} />
            <Route path="/home" element={<HomePage />} />
            <Route path="/app/:appId" element={<AppDetailPage />} />
            <Route path="/run/:runId" element={<RunDetailPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
