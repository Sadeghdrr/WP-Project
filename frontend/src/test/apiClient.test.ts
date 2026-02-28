/**
 * API client — unit tests.
 *
 * Tests the core fetch wrapper: token injection, error normalization,
 * 401 handler, and convenience methods.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  apiFetch,
  setAccessToken,
  getAccessToken,
  setOnUnauthorized,
} from "../api/client";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Create a mock fetch response */
function mockFetchResponse(
  status: number,
  body: unknown,
  ok?: boolean,
): Response {
  return {
    ok: ok ?? (status >= 200 && status < 300),
    status,
    json: () => Promise.resolve(body),
    headers: new Headers(),
  } as unknown as Response;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("API client", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    setAccessToken(null);
    setOnUnauthorized(null);
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    setAccessToken(null);
    setOnUnauthorized(null);
  });

  // -- Token management --

  it("stores and retrieves access token", () => {
    expect(getAccessToken()).toBeNull();
    setAccessToken("test-access-token");
    expect(getAccessToken()).toBe("test-access-token");
  });

  // -- Authorization header --

  it("adds Authorization header when access token is set", async () => {
    setAccessToken("my-token");
    globalThis.fetch = vi.fn().mockResolvedValue(
      mockFetchResponse(200, { result: "ok" }),
    );

    await apiFetch("/test/");

    const [, options] = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    const headers = options.headers as Headers;
    expect(headers.get("Authorization")).toBe("Bearer my-token");
  });

  it("does not add Authorization header when no token is set", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      mockFetchResponse(200, { result: "ok" }),
    );

    await apiFetch("/test/");

    const [, options] = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    const headers = options.headers as Headers;
    expect(headers.get("Authorization")).toBeNull();
  });

  // -- Successful response --

  it("returns ok: true for a successful JSON response", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      mockFetchResponse(200, { id: 1, name: "Case 1" }),
    );

    const result = await apiFetch("/cases/1/");
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.data).toEqual({ id: 1, name: "Case 1" });
      expect(result.status).toBe(200);
    }
  });

  it("handles 204 No Content responses", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      mockFetchResponse(204, null, true),
    );

    const result = await apiFetch("/resource/", { method: "DELETE" });
    expect(result.ok).toBe(true);
    expect(result.status).toBe(204);
  });

  // -- Error normalization --

  it("normalizes DRF detail errors", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      mockFetchResponse(403, { detail: "Permission denied" }),
    );

    const result = await apiFetch("/forbidden/");
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error.message).toBe("Permission denied");
    }
  });

  it("normalizes DRF validation field errors", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      mockFetchResponse(400, {
        username: ["This field is required."],
        email: ["Enter a valid email."],
      }),
    );

    const result = await apiFetch("/register/", { method: "POST" });
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error.message).toBe("This field is required.");
      expect(result.error.fieldErrors).toEqual({
        username: ["This field is required."],
        email: ["Enter a valid email."],
      });
    }
  });

  it("uses non_field_errors as the main message when present", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      mockFetchResponse(400, {
        non_field_errors: ["Invalid credentials"],
      }),
    );

    const result = await apiFetch("/login/", { method: "POST" });
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error.message).toBe("Invalid credentials");
    }
  });

  // -- 401 handler --

  it("calls onUnauthorized callback on 401 response", async () => {
    const onUnauth = vi.fn();
    setOnUnauthorized(onUnauth);

    globalThis.fetch = vi.fn().mockResolvedValue(
      mockFetchResponse(401, { detail: "Token expired" }),
    );

    await apiFetch("/protected/");
    expect(onUnauth).toHaveBeenCalledOnce();
  });

  it("does not call onUnauthorized on non-401 errors", async () => {
    const onUnauth = vi.fn();
    setOnUnauthorized(onUnauth);

    globalThis.fetch = vi.fn().mockResolvedValue(
      mockFetchResponse(403, { detail: "Forbidden" }),
    );

    await apiFetch("/forbidden/");
    expect(onUnauth).not.toHaveBeenCalled();
  });

  // -- Network error --

  it("returns a network error when fetch throws", async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new TypeError("Failed to fetch"));

    const result = await apiFetch("/offline/");
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error.message).toContain("Network error");
      expect(result.status).toBe(0);
    }
  });

  // -- Content-Type header --

  it("sets Content-Type to application/json for JSON body requests", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      mockFetchResponse(201, { id: 1 }),
    );

    await apiFetch("/create/", {
      method: "POST",
      body: JSON.stringify({ title: "Test" }),
    });

    const [, options] = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    const headers = options.headers as Headers;
    expect(headers.get("Content-Type")).toBe("application/json");
  });

  it("does NOT set Content-Type for FormData body", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      mockFetchResponse(201, { id: 1 }),
    );

    const fd = new FormData();
    fd.append("file", "data");

    await apiFetch("/upload/", {
      method: "POST",
      body: fd,
    });

    const [, options] = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    const headers = options.headers as Headers;
    expect(headers.get("Content-Type")).toBeNull();
  });
});
