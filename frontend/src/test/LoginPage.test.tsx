/**
 * LoginPage — component tests.
 *
 * Tests:
 *   1. Renders the login form with identifier + password fields
 *   2. Submit button is disabled when fields are empty
 *   3. Redirects to /dashboard when user is already authenticated
 *   4. Displays the backend login error message on failure
 *   5. Calls login with correct credentials on submit
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

// We mock useAuth to control auth state without needing the full provider
vi.mock("../auth/useAuth", () => ({
  useAuth: vi.fn(),
}));

import { useAuth } from "../auth/useAuth";
import type { AuthContextValue } from "../auth/AuthContext";
import LoginPage from "../pages/Login/LoginPage";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function mockUseAuth(overrides: Partial<AuthContextValue> = {}) {
  const defaults: AuthContextValue = {
    status: "unauthenticated",
    user: null,
    permissionSet: new Set(),
    login: vi.fn().mockResolvedValue({ ok: true }),
    register: vi.fn().mockResolvedValue({ ok: true }),
    logout: vi.fn(),
  };
  const value = { ...defaults, ...overrides };
  vi.mocked(useAuth).mockReturnValue(value);
  return value;
}

function renderLogin(initialEntries = ["/login"]) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/dashboard"
          element={<div data-testid="dashboard-page">Dashboard</div>}
        />
      </Routes>
    </MemoryRouter>,
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("LoginPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders identifier and password fields", () => {
    mockUseAuth();
    renderLogin();
    expect(screen.getByLabelText(/username, email, phone/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
  });

  it("disables submit button when fields are empty", () => {
    mockUseAuth();
    renderLogin();
    const btn = screen.getByRole("button", { name: /sign in/i });
    expect(btn).toBeDisabled();
  });

  it("enables submit button when both fields are filled", () => {
    mockUseAuth();
    renderLogin();
    fireEvent.change(screen.getByLabelText(/username, email, phone/i), {
      target: { value: "detective" },
    });
    fireEvent.change(screen.getByLabelText(/password/i), {
      target: { value: "secret123" },
    });
    const btn = screen.getByRole("button", { name: /sign in/i });
    expect(btn).toBeEnabled();
  });

  it("redirects to /dashboard when already authenticated", () => {
    mockUseAuth({ status: "authenticated" });
    renderLogin();
    expect(screen.getByTestId("dashboard-page")).toBeInTheDocument();
  });

  it("calls login with entered credentials on submit", async () => {
    const authValue = mockUseAuth();
    renderLogin();

    fireEvent.change(screen.getByLabelText(/username, email, phone/i), {
      target: { value: "detective" },
    });
    fireEvent.change(screen.getByLabelText(/password/i), {
      target: { value: "pass123" },
    });
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(authValue.login).toHaveBeenCalledWith({
        identifier: "detective",
        password: "pass123",
      });
    });
  });

  it("displays error message on login failure", async () => {
    mockUseAuth({
      login: vi.fn().mockResolvedValue({
        ok: false,
        error: {
          message:
            "Incorrect username, email, phone number, national ID, or password.",
        },
      }),
    });
    renderLogin();

    fireEvent.change(screen.getByLabelText(/username, email, phone/i), {
      target: { value: "user" },
    });
    fireEvent.change(screen.getByLabelText(/password/i), {
      target: { value: "wrong" },
    });
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(
        screen.getByText(
          "Incorrect username, email, phone number, national ID, or password.",
        ),
      ).toBeInTheDocument();
    });
  });

  it("shows a link to the registration page", () => {
    mockUseAuth();
    renderLogin();
    expect(screen.getByRole("link", { name: /register/i })).toHaveAttribute(
      "href",
      "/register",
    );
  });
});
