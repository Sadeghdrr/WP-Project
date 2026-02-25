import { useState } from "react";
import type { FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../../auth/useAuth";
import styles from "./LoginPage.module.css";

/**
 * Login page (§5.2).
 *
 * Accepts identifier (username / email / phone / national_id) + password.
 * On success, redirects to /dashboard.
 */
export default function LoginPage() {
  const { status, login } = useAuth();
  const navigate = useNavigate();

  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string[]>>({});
  const [submitting, setSubmitting] = useState(false);

  // If already logged in, redirect to dashboard
  if (status === "authenticated") {
    return <Navigate to="/dashboard" replace />;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setFieldErrors({});
    setSubmitting(true);

    const result = await login({ identifier, password });

    if (result.ok) {
      navigate("/dashboard", { replace: true });
    } else {
      setError(result.error.message);
      if (result.error.fieldErrors) {
        setFieldErrors(result.error.fieldErrors);
      }
    }

    setSubmitting(false);
  }

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <h1 className={styles.title}>Sign In</h1>
        <p className={styles.subtitle}>
          LAPD Case Management System
        </p>

        {error && <div className={styles.error}>{error}</div>}

        <form className={styles.form} onSubmit={handleSubmit}>
          <div className={styles.field}>
            <label htmlFor="identifier" className={styles.label}>
              Username, Email, Phone, or National ID
            </label>
            <input
              id="identifier"
              type="text"
              className={`${styles.input} ${fieldErrors.identifier ? styles.inputError : ""}`}
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              required
              autoComplete="username"
              autoFocus
              disabled={submitting}
            />
            {fieldErrors.identifier?.map((msg) => (
              <span key={msg} className={styles.fieldError}>{msg}</span>
            ))}
          </div>

          <div className={styles.field}>
            <label htmlFor="password" className={styles.label}>
              Password
            </label>
            <input
              id="password"
              type="password"
              className={`${styles.input} ${fieldErrors.password ? styles.inputError : ""}`}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
              disabled={submitting}
            />
            {fieldErrors.password?.map((msg) => (
              <span key={msg} className={styles.fieldError}>{msg}</span>
            ))}
          </div>

          <button
            type="submit"
            className={styles.button}
            disabled={submitting || !identifier || !password}
          >
            {submitting ? "Signing in…" : "Sign In"}
          </button>
        </form>

        <div className={styles.footer}>
          Don&apos;t have an account?{" "}
          <Link to="/register">Register</Link>
        </div>
      </div>
    </div>
  );
}
