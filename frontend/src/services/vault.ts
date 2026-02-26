const encoder = new TextEncoder();
const decoder = new TextDecoder();

function toBase64(input: Uint8Array): string {
  return btoa(String.fromCharCode(...input));
}

function fromBase64(input: string): Uint8Array {
  return Uint8Array.from(atob(input), (c) => c.charCodeAt(0));
}

async function deriveKey(passphrase: string): Promise<CryptoKey> {
  const passphraseHash = await crypto.subtle.digest("SHA-256", encoder.encode(passphrase));
  return crypto.subtle.importKey("raw", passphraseHash, "AES-GCM", false, ["encrypt", "decrypt"]);
}

export async function encryptSecret(secret: string, passphrase: string): Promise<string> {
  const key = await deriveKey(passphrase);
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const cipherBuffer = await crypto.subtle.encrypt(
    { name: "AES-GCM", iv },
    key,
    encoder.encode(secret),
  );

  const cipherBytes = new Uint8Array(cipherBuffer);
  const payload = new Uint8Array(iv.length + cipherBytes.length);
  payload.set(iv, 0);
  payload.set(cipherBytes, iv.length);
  return toBase64(payload);
}

export async function decryptSecret(payload: string, passphrase: string): Promise<string> {
  const bytes = fromBase64(payload);
  const iv = bytes.slice(0, 12);
  const cipher = bytes.slice(12);
  const key = await deriveKey(passphrase);
  const plain = await crypto.subtle.decrypt({ name: "AES-GCM", iv }, key, cipher);
  return decoder.decode(plain);
}
