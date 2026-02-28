import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "../auth/AuthContext";
import { useAuth } from "../auth/useAuth";
import type { User } from "../types/auth";

vi.mock("../api/auth", () => ({
  loginApi: vi.fn(),
  registerApi: vi.fn(),
  refreshTokenApi: vi.fn(),
  fetchMeApi: vi.fn(),
}));

vi.mock("../api/client", () => ({
  setAccessToken: vi.fn(),
  setOnUnauthorized: vi.fn(),
}));

vi.mock("../auth/tokenStorage", () => ({
  getStoredRefreshToken: vi.fn(),
  storeRefreshToken: vi.fn(),
  clearStoredRefreshToken: vi.fn(),
}));

import { loginApi } from "../api/auth";
import { getStoredRefreshToken } from "../auth/tokenStorage";

function makeUser(id: number): User {
  return {
    id,
    username: `user-${id}`,
    email: `user-${id}@example.com`,
    first_name: "Test",
    last_name: "User",
    national_id: `000000000${id}`,
    phone_number: `0912000000${id}`,
    role: "Detective",
    role_detail: {
      id: 1,
      name: "Detective",
      description: "Investigates cases",
      hierarchy_level: 6,
    },
    permissions: ["cases.view_case"],
    is_active: true,
    date_joined: "2026-01-01T00:00:00Z",
  };
}

function CacheHarness() {
  const { status, login, logout } = useAuth();

  return (
    <div>
      <div data-testid="status">{status}</div>
      <button
        type="button"
        onClick={() => {
          void login({ identifier: "detective", password: "secret" });
        }}
      >
        Login
      </button>
      <button type="button" onClick={logout}>
        Logout
      </button>
    </div>
  );
}

function renderAuthHarness(queryClient: QueryClient) {
  return render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <CacheHarness />
      </AuthProvider>
    </QueryClientProvider>,
  );
}

describe("AuthProvider", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getStoredRefreshToken).mockReturnValue(null);
  });

  it("clears stale query cache when a different user logs in", async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    vi.mocked(loginApi).mockResolvedValue({
      ok: true,
      status: 200,
      data: {
        access: "access-token",
        refresh: "refresh-token",
        user: makeUser(2),
      },
    });

    renderAuthHarness(queryClient);

    await waitFor(() => {
      expect(screen.getByTestId("status")).toHaveTextContent("unauthenticated");
    });

    queryClient.setQueryData(["cases"], "admin-cached-cases");
    expect(queryClient.getQueryData(["cases"])).toBe("admin-cached-cases");

    fireEvent.click(screen.getByRole("button", { name: "Login" }));

    await waitFor(() => {
      expect(screen.getByTestId("status")).toHaveTextContent("authenticated");
    });
    expect(queryClient.getQueryData(["cases"])).toBeUndefined();
  });

  it("clears cached data on logout", async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    vi.mocked(loginApi).mockResolvedValue({
      ok: true,
      status: 200,
      data: {
        access: "access-token",
        refresh: "refresh-token",
        user: makeUser(3),
      },
    });

    renderAuthHarness(queryClient);

    await waitFor(() => {
      expect(screen.getByTestId("status")).toHaveTextContent("unauthenticated");
    });

    fireEvent.click(screen.getByRole("button", { name: "Login" }));

    await waitFor(() => {
      expect(screen.getByTestId("status")).toHaveTextContent("authenticated");
    });

    queryClient.setQueryData(["cases"], "cached-cases");
    expect(queryClient.getQueryData(["cases"])).toBe("cached-cases");

    fireEvent.click(screen.getByRole("button", { name: "Logout" }));

    await waitFor(() => {
      expect(screen.getByTestId("status")).toHaveTextContent("unauthenticated");
    });
    expect(queryClient.getQueryData(["cases"])).toBeUndefined();
  });
});
