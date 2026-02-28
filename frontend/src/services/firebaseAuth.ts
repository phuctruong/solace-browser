export interface AuthResult {
  uid: string;
  email: string;
  idToken: string;
}

export async function signInWithPopup(provider: "gmail" | "github" = "gmail"): Promise<AuthResult> {
  if (typeof window === "undefined") {
    throw new Error("Browser environment required for popup auth");
  }

  const popup = window.open(
    "https://solaceagi.com/auth/browser-register",
    "solaceAuth",
    "width=480,height=720",
  );

  if (!popup) {
    throw new Error("Authentication popup was blocked. Please allow popups for this site and try again.");
  }

  return new Promise<AuthResult>((resolve, reject) => {
    const timeout = window.setTimeout(() => {
      window.removeEventListener("message", onMessage);
      reject(new Error("Auth popup timed out"));
    }, 30_000);

    function onMessage(event: MessageEvent): void {
      if (event.origin !== "https://solaceagi.com") {
        return;
      }
      if (!event.data || event.data.type !== "solace-auth-success") {
        return;
      }
      window.clearTimeout(timeout);
      window.removeEventListener("message", onMessage);
      resolve(event.data.payload as AuthResult);
      if (popup) {
        popup.close();
      }
    }

    window.addEventListener("message", onMessage);
  });
}
