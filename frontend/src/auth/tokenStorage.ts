/**
 * Token persistence helpers.
 *
 * Strategy:
 *   - Access token: in-memory only (module-scoped via api/client.ts)
 *   - Refresh token: localStorage (survives page reload, cleared on logout)
 *
 * This is a practical balance between security and UX:
 *   - Access token never touches storage → XSS can't leak it
 *   - Refresh token in localStorage lets us silently refresh on reload
 *   - 7-day refresh lifetime (backend) with rotation + blacklisting
 */

const REFRESH_KEY = "lapd_refresh_token";

export function getStoredRefreshToken(): string | null {
  try {
    return localStorage.getItem(REFRESH_KEY);
  } catch {
    return null;
  }
}

export function storeRefreshToken(token: string): void {
  try {
    localStorage.setItem(REFRESH_KEY, token);
  } catch {
    // Private browsing or storage full — fail silently
  }
}

export function clearStoredRefreshToken(): void {
  try {
    localStorage.removeItem(REFRESH_KEY);
  } catch {
    // Ignore
  }
}
