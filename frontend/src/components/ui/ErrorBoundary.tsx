/**
 * ErrorBoundary — catches unhandled React runtime errors.
 *
 * How it works:
 *  1. Wraps children in a class component (required for getDerivedStateFromError)
 *  2. On error, renders a user-friendly fallback UI
 *  3. Logs the error for debugging
 *  4. Offers Retry (re-mount) and Go Home recovery actions
 *
 * Where it's used:
 *  - Globally in App.tsx around the router
 *  - Per-section in DashboardLayout around <Outlet />
 *
 * This complements API error handling (which uses try/catch + toast).
 * ErrorBoundary only catches rendering errors, event handler errors
 * are NOT caught here (those use try/catch).
 */
import { Component, type ErrorInfo, type ReactNode } from 'react';

/* ── Fallback UI ─────────────────────────────────────────────────── */

interface ErrorFallbackProps {
  error: Error;
  resetError: () => void;
}

function ErrorFallback({ error, resetError }: ErrorFallbackProps) {
  return (
    <div className="error-boundary" role="alert">
      <div className="error-boundary__card">
        <div className="error-boundary__icon" aria-hidden="true">
          ⚠️
        </div>
        <h2 className="error-boundary__title">Something went wrong</h2>
        <p className="error-boundary__message">
          An unexpected error occurred. This has been logged for review.
        </p>
        {import.meta.env.DEV && (
          <details className="error-boundary__details">
            <summary>Error details (development only)</summary>
            <pre className="error-boundary__stack">{error.message}</pre>
          </details>
        )}
        <div className="error-boundary__actions">
          <button
            className="btn btn--primary btn--md"
            onClick={resetError}
          >
            Try Again
          </button>
          <button
            className="btn btn--secondary btn--md"
            onClick={() => {
              window.location.href = '/';
            }}
          >
            Go Home
          </button>
        </div>
      </div>
    </div>
  );
}

/* ── Error Boundary class component ──────────────────────────────── */

interface ErrorBoundaryProps {
  children: ReactNode;
  /** Custom fallback renderer (optional). Defaults to ErrorFallback. */
  fallback?: (props: ErrorFallbackProps) => ReactNode;
  /** Called when an error is caught. Use for error reporting. */
  onError?: (error: Error, info: ErrorInfo) => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // Log to console in dev, could send to error reporting service
    console.error('[ErrorBoundary] Caught error:', error, info);
    this.props.onError?.(error, info);
  }

  resetError = (): void => {
    this.setState({ hasError: false, error: null });
  };

  render(): ReactNode {
    if (this.state.hasError && this.state.error) {
      const FallbackComponent = this.props.fallback ?? ErrorFallback;
      return (
        <FallbackComponent
          error={this.state.error}
          resetError={this.resetError}
        />
      );
    }
    return this.props.children;
  }
}
