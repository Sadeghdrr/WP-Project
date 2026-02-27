/**
 * RouteGuards — component tests.
 *
 * Tests:
 *   1. ProtectedRoute renders children when authenticated
 *   2. ProtectedRoute redirects to / when unauthenticated
 *   3. ProtectedRoute shows loading state while bootstrapping
 *   4. GuestRoute renders children when unauthenticated
 *   5. GuestRoute redirects to /dashboard when authenticated
 *   6. GuestRoute shows loading state while bootstrapping
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes, Outlet } from "react-router-dom";

// Mock useAuth
vi.mock("../auth/useAuth", () => ({
  useAuth: vi.fn(),
}));

import { useAuth } from "../auth/useAuth";
import type { AuthContextValue } from "../auth/AuthContext";
import { ProtectedRoute, GuestRoute } from "../components/auth/RouteGuards";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function mockUseAuth(overrides: Partial<AuthContextValue> = {}) {
  const defaults: AuthContextValue = {
    status: "unauthenticated",
    user: null,
    permissionSet: new Set(),
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
  };
  vi.mocked(useAuth).mockReturnValue({ ...defaults, ...overrides });
}

// ---------------------------------------------------------------------------
// ProtectedRoute tests
// ---------------------------------------------------------------------------

describe("ProtectedRoute", () => {
  beforeEach(() => vi.clearAllMocks());

  it("renders child route when authenticated", () => {
    mockUseAuth({ status: "authenticated" });
    render(
      <MemoryRouter initialEntries={["/app"]}>
        <Routes>
          <Route element={<ProtectedRoute />}>
            <Route path="/app" element={<div data-testid="protected-child">Protected Content</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );
    expect(screen.getByTestId("protected-child")).toBeInTheDocument();
  });

  it("redirects to / when unauthenticated", () => {
    mockUseAuth({ status: "unauthenticated" });
    render(
      <MemoryRouter initialEntries={["/app"]}>
        <Routes>
          <Route element={<ProtectedRoute />}>
            <Route path="/app" element={<div data-testid="protected-child">Protected</div>} />
          </Route>
          <Route path="/" element={<div data-testid="dashboard-page">Dashboard</div>} />
        </Routes>
      </MemoryRouter>,
    );
    expect(screen.queryByTestId("protected-child")).not.toBeInTheDocument();
    expect(screen.getByTestId("dashboard-page")).toBeInTheDocument();
  });

  it("shows loading state while auth is bootstrapping", () => {
    mockUseAuth({ status: "loading" });
    render(
      <MemoryRouter initialEntries={["/app"]}>
        <Routes>
          <Route element={<ProtectedRoute />}>
            <Route path="/app" element={<div data-testid="protected-child">Protected</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );
    expect(screen.queryByTestId("protected-child")).not.toBeInTheDocument();
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// GuestRoute tests
// ---------------------------------------------------------------------------

describe("GuestRoute", () => {
  beforeEach(() => vi.clearAllMocks());

  it("renders child route when unauthenticated", () => {
    mockUseAuth({ status: "unauthenticated" });
    render(
      <MemoryRouter initialEntries={["/login"]}>
        <Routes>
          <Route element={<GuestRoute />}>
            <Route path="/login" element={<div data-testid="guest-child">Login Form</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );
    expect(screen.getByTestId("guest-child")).toBeInTheDocument();
  });

  it("redirects to /dashboard when authenticated", () => {
    mockUseAuth({ status: "authenticated" });
    render(
      <MemoryRouter initialEntries={["/login"]}>
        <Routes>
          <Route element={<GuestRoute />}>
            <Route path="/login" element={<div data-testid="guest-child">Login</div>} />
          </Route>
          <Route path="/dashboard" element={<div data-testid="dashboard-page">Dashboard</div>} />
        </Routes>
      </MemoryRouter>,
    );
    expect(screen.queryByTestId("guest-child")).not.toBeInTheDocument();
    expect(screen.getByTestId("dashboard-page")).toBeInTheDocument();
  });

  it("shows loading state while auth is bootstrapping", () => {
    mockUseAuth({ status: "loading" });
    render(
      <MemoryRouter initialEntries={["/login"]}>
        <Routes>
          <Route element={<GuestRoute />}>
            <Route path="/login" element={<div data-testid="guest-child">Login</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );
    expect(screen.queryByTestId("guest-child")).not.toBeInTheDocument();
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });
});
