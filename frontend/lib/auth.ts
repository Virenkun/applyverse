const SALT = "applyverse-session-v1";

export const SESSION_COOKIE = "av_session";

function password(): string {
  return process.env.APPLYVERSE_PASSWORD ?? "applyverse";
}

/** Deterministic session token derived from the access password.
 * crypto.subtle so it runs in both the node runtime and the proxy. */
export async function sessionToken(): Promise<string> {
  const data = new TextEncoder().encode(`${SALT}:${password()}`);
  const digest = await crypto.subtle.digest("SHA-256", data);
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

export function checkPassword(candidate: string): boolean {
  return candidate === password();
}
