import { useState } from "react";
import type { FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../../auth/useAuth";
import styles from "./RegisterPage.module.css";

/**
 * Registration page (§5.2, §4.1).
 *
 * Required fields: username, password, password_confirm,
 * email, phone_number, first_name, last_name, national_id.
 *
 * On success, auto-logs in and redirects to /dashboard.
 */
export default function RegisterPage() {
  const { status, register } = useAuth();
  const navigate = useNavigate();

  const [form, setForm] = useState({
    username: "",
    email: "",
    phone_number: "",
    national_id: "",
    first_name: "",
    last_name: "",
    password: "",
    password_confirm: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string[]>>({});
  const [submitting, setSubmitting] = useState(false);

  // If already logged in, redirect
  if (status === "authenticated") {
    return <Navigate to="/dashboard" replace />;
  }

  function updateField(field: string, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setFieldErrors({});

    // Client-side checks
    if (form.password !== form.password_confirm) {
      setFieldErrors({ password_confirm: ["Passwords do not match."] });
      return;
    }
    if (form.password.length < 8) {
      setFieldErrors({ password: ["Password must be at least 8 characters."] });
      return;
    }

    setSubmitting(true);
    const result = await register(form);

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

  /** Helper to render a form field */
  function renderField(
    id: string,
    label: string,
    type: string = "text",
    opts?: { autoComplete?: string; hint?: string },
  ) {
    const fieldKey = id as keyof typeof form;
    return (
      <div className={styles.field}>
        <label htmlFor={id} className={styles.label}>
          {label}
        </label>
        <input
          id={id}
          type={type}
          className={`${styles.input} ${fieldErrors[id] ? styles.inputError : ""}`}
          value={form[fieldKey]}
          onChange={(e) => updateField(id, e.target.value)}
          required
          autoComplete={opts?.autoComplete}
          disabled={submitting}
        />
        {opts?.hint && <span className={styles.hint}>{opts.hint}</span>}
        {fieldErrors[id]?.map((msg) => (
          <span key={msg} className={styles.fieldError}>{msg}</span>
        ))}
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <h1 className={styles.title}>Create Account</h1>
        <p className={styles.subtitle}>
          Register for the LAPD Case Management System
        </p>

        {error && <div className={styles.error}>{error}</div>}

        <form className={styles.form} onSubmit={handleSubmit}>
          {renderField("username", "Username", "text", {
            autoComplete: "username",
          })}

          <div className={styles.row}>
            {renderField("first_name", "First Name", "text", {
              autoComplete: "given-name",
            })}
            {renderField("last_name", "Last Name", "text", {
              autoComplete: "family-name",
            })}
          </div>

          {renderField("email", "Email", "email", {
            autoComplete: "email",
          })}

          {renderField("phone_number", "Phone Number", "tel", {
            autoComplete: "tel",
            hint: "Iranian mobile: 09XXXXXXXXX or +989XXXXXXXXX",
          })}

          {renderField("national_id", "National ID", "text", {
            hint: "Exactly 10 digits",
          })}

          {renderField("password", "Password", "password", {
            autoComplete: "new-password",
            hint: "Minimum 8 characters",
          })}

          {renderField("password_confirm", "Confirm Password", "password", {
            autoComplete: "new-password",
          })}

          <button
            type="submit"
            className={styles.button}
            disabled={submitting}
          >
            {submitting ? "Creating account…" : "Register"}
          </button>
        </form>

        <div className={styles.footer}>
          Already have an account?{" "}
          <Link to="/login">Sign In</Link>
        </div>
      </div>
    </div>
  );
}
