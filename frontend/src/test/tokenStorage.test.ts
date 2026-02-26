/**
 * Token storage helpers — unit tests.
 *
 * Tests localStorage get/store/clear operations for the refresh token.
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import {
  getStoredRefreshToken,
  storeRefreshToken,
  clearStoredRefreshToken,
} from "../auth/tokenStorage";

const KEY = "lapd_refresh_token";

describe("tokenStorage", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("returns null when no token is stored", () => {
    expect(getStoredRefreshToken()).toBeNull();
  });

  it("stores and retrieves a refresh token", () => {
    storeRefreshToken("my-refresh-token");
    expect(getStoredRefreshToken()).toBe("my-refresh-token");
  });

  it("clears the stored refresh token", () => {
    storeRefreshToken("some-token");
    clearStoredRefreshToken();
    expect(getStoredRefreshToken()).toBeNull();
  });

  it("handles localStorage errors gracefully on get", () => {
    const spy = vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("Quota exceeded");
    });
    expect(getStoredRefreshToken()).toBeNull();
    spy.mockRestore();
  });

  it("handles localStorage errors gracefully on store", () => {
    const spy = vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("Quota exceeded");
    });
    // Should not throw
    expect(() => storeRefreshToken("tok")).not.toThrow();
    spy.mockRestore();
  });

  it("stores under the correct key", () => {
    storeRefreshToken("test-token");
    expect(localStorage.getItem(KEY)).toBe("test-token");
  });
});
