/**
 * BoardErrorBoundary — React class-based error boundary for the Detective Board.
 *
 * Catches runtime errors (including "Maximum update depth exceeded") inside
 * the board workspace and presents a friendly recovery UI instead of the bare
 * React crash screen.
 */

import { Component, type ReactNode } from "react";
import { Link } from "react-router-dom";

interface Props {
  children: ReactNode;
  /** Optional case ID used to rebuild the board URL for the retry link */
  caseId?: string | number;
}

interface State {
  hasError: boolean;
  errorMessage: string;
}

export class BoardErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, errorMessage: "" };
  }

  static getDerivedStateFromError(error: unknown): State {
    const msg =
      error instanceof Error ? error.message : "An unexpected error occurred";
    return { hasError: true, errorMessage: msg };
  }

  componentDidCatch(error: unknown, info: { componentStack: string }) {
    // Log for debugging without crashing further
    console.error("[BoardErrorBoundary] Caught error:", error, info);
  }

  handleRetry = () => {
    this.setState({ hasError: false, errorMessage: "" });
  };

  render() {
    if (!this.state.hasError) {
      return this.props.children;
    }

    const { caseId } = this.props;

    return (
      <div
        style={{
          padding: "2rem",
          maxWidth: "640px",
          margin: "4rem auto",
          fontFamily: "system-ui, sans-serif",
        }}
      >
        <h2 style={{ color: "#991b1b", marginBottom: "0.75rem" }}>
          Detective Board Error
        </h2>
        <p style={{ color: "#374151", marginBottom: "0.5rem" }}>
          The board workspace encountered an error and could not complete its
          last operation.
        </p>
        <pre
          style={{
            background: "#fee2e2",
            color: "#7f1d1d",
            padding: "0.75rem 1rem",
            borderRadius: "6px",
            fontSize: "0.8rem",
            overflowX: "auto",
            marginBottom: "1.25rem",
            whiteSpace: "pre-wrap",
            wordBreak: "break-word",
          }}
        >
          {this.state.errorMessage}
        </pre>
        <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
          <button
            type="button"
            onClick={this.handleRetry}
            style={{
              padding: "0.5rem 1.25rem",
              background: "#4f46e5",
              color: "#fff",
              border: "none",
              borderRadius: "6px",
              cursor: "pointer",
              fontWeight: 600,
            }}
          >
            Retry
          </button>
          {caseId && (
            <Link
              to={`/cases/${caseId}`}
              style={{
                padding: "0.5rem 1.25rem",
                background: "#f3f4f6",
                color: "#374151",
                border: "1px solid #d1d5db",
                borderRadius: "6px",
                textDecoration: "none",
                fontWeight: 500,
              }}
            >
              ← Back to Case
            </Link>
          )}
          <Link
            to="/cases"
            style={{
              padding: "0.5rem 1.25rem",
              background: "#f3f4f6",
              color: "#374151",
              border: "1px solid #d1d5db",
              borderRadius: "6px",
              textDecoration: "none",
              fontWeight: 500,
            }}
          >
            All Cases
          </Link>
        </div>
      </div>
    );
  }
}
