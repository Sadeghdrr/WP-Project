/**
 * ErrorBoundary — component tests.
 *
 * Tests:
 *   1. Renders children when no error occurs
 *   2. Renders fallback UI when a child throws
 *   3. Displays the error message in the fallback
 *   4. Renders custom fallback when provided
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import ErrorBoundary from "../components/ui/ErrorBoundary";

// A component that throws an error on render
function ThrowingChild({ message = "Test error" }: { message?: string }) {
  throw new Error(message);
  return null;
}

describe("ErrorBoundary", () => {
  // Suppress console.error for expected error boundary logs
  beforeEach(() => {
    vi.spyOn(console, "error").mockImplementation(() => {});
  });

  it("renders children when no error occurs", () => {
    render(
      <ErrorBoundary>
        <div data-testid="safe-child">Hello</div>
      </ErrorBoundary>,
    );
    expect(screen.getByTestId("safe-child")).toBeInTheDocument();
  });

  it("renders fallback UI when a child throws", () => {
    render(
      <ErrorBoundary>
        <ThrowingChild />
      </ErrorBoundary>,
    );
    expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
  });

  it("displays the error message in the fallback", () => {
    render(
      <ErrorBoundary>
        <ThrowingChild message="Kaboom!" />
      </ErrorBoundary>,
    );
    expect(screen.getByText("Kaboom!")).toBeInTheDocument();
  });

  it("renders custom fallback when provided", () => {
    render(
      <ErrorBoundary fallback={<div data-testid="custom-fallback">Custom error</div>}>
        <ThrowingChild />
      </ErrorBoundary>,
    );
    expect(screen.getByTestId("custom-fallback")).toBeInTheDocument();
    expect(screen.queryByText(/something went wrong/i)).not.toBeInTheDocument();
  });

  it("shows a reload button in the default fallback", () => {
    render(
      <ErrorBoundary>
        <ThrowingChild />
      </ErrorBoundary>,
    );
    expect(screen.getByRole("button", { name: /reload/i })).toBeInTheDocument();
  });
});
