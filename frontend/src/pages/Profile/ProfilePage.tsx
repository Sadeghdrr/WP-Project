import { useState, useEffect, useCallback } from "react";
import type { FormEvent } from "react";
import { getCurrentUser, updateCurrentUser } from "../../api/profile";
import type { UpdateProfileRequest } from "../../api/profile";
import type { User } from "../../types/auth";
import css from "./ProfilePage.module.css";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Basic email regex — good enough for client-side pre-validation. */
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/** Format ISO date string into a readable locale string. */
function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Profile page — view and edit the currently authenticated user.
 *
 * Read-only fields: username, role, date_joined
 * Editable fields : email, phone_number, first_name, last_name
 */
export default function ProfilePage() {
  // ── Data state ───────────────────────────────────────────────────
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);

  // ── Form state ───────────────────────────────────────────────────
  const [email, setEmail] = useState("");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");

  // ── Submission state ─────────────────────────────────────────────
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // ── Populate form from user data ─────────────────────────────────
  const populateForm = useCallback((u: User) => {
    setEmail(u.email ?? "");
    setPhoneNumber(u.phone_number ?? "");
    setFirstName(u.first_name ?? "");
    setLastName(u.last_name ?? "");
  }, []);

  // ── Fetch current user on mount ──────────────────────────────────
  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setFetchError(null);

      const res = await getCurrentUser();
      if (cancelled) return;

      if (res.ok) {
        setUser(res.data);
        populateForm(res.data);
      } else {
        setFetchError(res.error.message || "Failed to load profile.");
      }
      setLoading(false);
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [populateForm]);

  // ── Client-side validation ───────────────────────────────────────
  function validate(): boolean {
    const errs: Record<string, string> = {};

    if (!email.trim()) {
      errs.email = "Email is required.";
    } else if (!EMAIL_RE.test(email.trim())) {
      errs.email = "Enter a valid email address.";
    }

    if (!firstName.trim()) {
      errs.first_name = "First name is required.";
    }

    if (!lastName.trim()) {
      errs.last_name = "Last name is required.";
    }

    setFieldErrors(errs);
    return Object.keys(errs).length === 0;
  }

  // ── Submit handler ───────────────────────────────────────────────
  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSuccessMsg(null);
    setSubmitError(null);

    if (!validate()) return;

    setSubmitting(true);

    const payload: UpdateProfileRequest = {
      email: email.trim(),
      phone_number: phoneNumber.trim(),
      first_name: firstName.trim(),
      last_name: lastName.trim(),
    };

    const res = await updateCurrentUser(payload);

    if (res.ok) {
      setUser(res.data);
      populateForm(res.data);
      setSuccessMsg("Profile updated successfully.");
      setFieldErrors({});
    } else {
      setSubmitError(res.error.message || "Failed to update profile.");
      // Map backend field errors if present
      if (res.error.fieldErrors) {
        const mapped: Record<string, string> = {};
        for (const [key, msgs] of Object.entries(res.error.fieldErrors)) {
          mapped[key] = msgs.join(" ");
        }
        setFieldErrors(mapped);
      }
    }

    setSubmitting(false);
  }

  // ── Render: loading ──────────────────────────────────────────────
  if (loading) {
    return (
      <div className={css.page}>
        <div className={css.loading}>Loading profile…</div>
      </div>
    );
  }

  // ── Render: fetch error ──────────────────────────────────────────
  if (fetchError || !user) {
    return (
      <div className={css.page}>
        <div className={css.errorBox}>
          {fetchError ?? "Unable to load profile."}
        </div>
      </div>
    );
  }

  // ── Render: profile form ─────────────────────────────────────────
  return (
    <div className={css.page}>
      {/* Page header */}
      <div className={css.header}>
        <h1 className={css.title}>My Profile</h1>
        <p className={css.subtitle}>View and manage your account information.</p>
      </div>

      {/* Read-only info section */}
      <div className={css.infoSection}>
        <div className={css.infoRow}>
          <span className={css.infoLabel}>Username</span>
          <span className={css.infoValue}>{user.username}</span>
        </div>
        <div className={css.infoRow}>
          <span className={css.infoLabel}>Role</span>
          <span className={css.infoValue}>
            {user.role_detail?.name ?? user.role ?? "—"}
          </span>
        </div>
        <div className={css.infoRow}>
          <span className={css.infoLabel}>Joined</span>
          <span className={css.infoValue}>{formatDate(user.date_joined)}</span>
        </div>
      </div>

      {/* Editable form */}
      <form className={css.form} onSubmit={handleSubmit} noValidate>
        <div className={css.sectionLabel}>Editable Information</div>

        <div className={css.row}>
          <div className={css.field}>
            <label htmlFor="firstName" className={css.label}>
              First Name
            </label>
            <input
              id="firstName"
              type="text"
              className={`${css.input} ${fieldErrors.first_name ? css.inputError : ""}`}
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
              disabled={submitting}
            />
            {fieldErrors.first_name && (
              <span className={css.fieldError}>{fieldErrors.first_name}</span>
            )}
          </div>

          <div className={css.field}>
            <label htmlFor="lastName" className={css.label}>
              Last Name
            </label>
            <input
              id="lastName"
              type="text"
              className={`${css.input} ${fieldErrors.last_name ? css.inputError : ""}`}
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
              disabled={submitting}
            />
            {fieldErrors.last_name && (
              <span className={css.fieldError}>{fieldErrors.last_name}</span>
            )}
          </div>
        </div>

        <div className={css.field}>
          <label htmlFor="email" className={css.label}>
            Email
          </label>
          <input
            id="email"
            type="email"
            className={`${css.input} ${fieldErrors.email ? css.inputError : ""}`}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={submitting}
          />
          {fieldErrors.email && (
            <span className={css.fieldError}>{fieldErrors.email}</span>
          )}
        </div>

        <div className={css.field}>
          <label htmlFor="phoneNumber" className={css.label}>
            Phone Number
          </label>
          <input
            id="phoneNumber"
            type="tel"
            className={`${css.input} ${fieldErrors.phone_number ? css.inputError : ""}`}
            value={phoneNumber}
            onChange={(e) => setPhoneNumber(e.target.value)}
            disabled={submitting}
          />
          {fieldErrors.phone_number && (
            <span className={css.fieldError}>{fieldErrors.phone_number}</span>
          )}
        </div>

        {/* Feedback messages */}
        {successMsg && <div className={css.success}>{successMsg}</div>}
        {submitError && <div className={css.inlineError}>{submitError}</div>}

        {/* Actions */}
        <div className={css.actions}>
          <button
            type="submit"
            className={css.button}
            disabled={submitting}
          >
            {submitting ? "Saving…" : "Save Changes"}
          </button>
        </div>
      </form>
    </div>
  );
}
