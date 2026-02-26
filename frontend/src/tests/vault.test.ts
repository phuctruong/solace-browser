import { describe, expect, it } from "vitest";
import { decryptSecret, encryptSecret } from "../services/vault";

describe("vault", () => {
  it("encrypts and decrypts with same passphrase", async () => {
    const secret = "sk_browser_xyz789";
    const passphrase = "user123";

    const encrypted = await encryptSecret(secret, passphrase);
    const decrypted = await decryptSecret(encrypted, passphrase);

    expect(encrypted).not.toEqual(secret);
    expect(decrypted).toEqual(secret);
  });
});
