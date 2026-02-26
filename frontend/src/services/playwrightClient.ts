interface ExecuteRequest {
  appId: string;
  recipeId: string;
  seed: string;
  scopes: string[];
}

interface ExecuteResult {
  status: "success" | "failed";
  durationMs: number;
  screenshots: string[];
  output: Record<string, unknown>;
}

function seededInt(seed: string): number {
  let hash = 0;
  for (let i = 0; i < seed.length; i += 1) {
    hash = (hash * 31 + seed.charCodeAt(i)) >>> 0;
  }
  return hash;
}

export async function executeHeadless(request: ExecuteRequest): Promise<ExecuteResult> {
  if (request.scopes.length === 0) {
    throw new Error("No scopes granted for execution");
  }
  const val = seededInt(`${request.appId}:${request.recipeId}:${request.seed}`);
  const durationMs = 8_000 + (val % 9_000);
  return {
    status: "success",
    durationMs,
    screenshots: ["step_1.png", "step_2.png"],
    output: {
      recipe_id: request.recipeId,
      app_id: request.appId,
      deterministic_nonce: val,
    },
  };
}
