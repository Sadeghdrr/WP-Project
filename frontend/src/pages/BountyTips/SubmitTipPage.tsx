import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { useBountyTipActions } from "../../hooks/useSuspects";
import css from "./SubmitTipPage.module.css";

/**
 * Submit a new bounty tip (§4.8).
 *
 * Citizen provides a suspect ID and/or case ID plus textual information.
 * At least one of suspect or case is required by the backend.
 */
export default function SubmitTipPage() {
  const { createTip } = useBountyTipActions();

  const [suspect, setSuspect] = useState("");
  const [caseId, setCaseId] = useState("");
  const [information, setInformation] = useState("");
  const [formError, setFormError] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    setFormError("");

    if (!suspect && !caseId) {
      setFormError("Please provide at least a suspect ID or case ID.");
      return;
    }
    if (!information.trim()) {
      setFormError("Information field is required.");
      return;
    }

    createTip.mutate(
      {
        suspect: suspect ? Number(suspect) : undefined,
        case: caseId ? Number(caseId) : undefined,
        information: information.trim(),
      },
      {
        onSuccess: () => setSubmitted(true),
        onError: (err) => setFormError(err.message),
      },
    );
  };

  if (submitted) {
    return (
      <div className={css.container}>
        <div className={css.successCard}>
          <h2>Tip Submitted!</h2>
          <p>
            Your tip has been received and is pending officer review.
            If verified, you will receive a unique code for reward collection.
          </p>
          <Link to="/bounty-tips" className={css.backLink}>
            ← Back to Bounty Tips
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className={css.container}>
      <Link to="/bounty-tips" className={css.backLink}>
        ← Back to Bounty Tips
      </Link>

      <div className={css.header}>
        <h1>Submit a Tip</h1>
        <p className={css.subtitle}>
          Provide information about a suspect or case to earn a bounty reward
        </p>
      </div>

      <form className={css.form} onSubmit={handleSubmit}>
        <div className={css.field}>
          <label htmlFor="suspect">Suspect ID</label>
          <input
            id="suspect"
            type="number"
            placeholder="e.g. 12"
            value={suspect}
            onChange={(e) => setSuspect(e.target.value)}
          />
          <span className={css.hint}>
            Optional — provide suspect ID if known
          </span>
        </div>

        <div className={css.field}>
          <label htmlFor="caseId">Case ID</label>
          <input
            id="caseId"
            type="number"
            placeholder="e.g. 5"
            value={caseId}
            onChange={(e) => setCaseId(e.target.value)}
          />
          <span className={css.hint}>
            Optional — provide case ID if known
          </span>
        </div>

        <div className={css.field}>
          <label htmlFor="information">Information *</label>
          <textarea
            id="information"
            placeholder="Describe what you know — sighting details, locations, timestamps…"
            value={information}
            onChange={(e) => setInformation(e.target.value)}
            required
          />
        </div>

        {formError && <p className={css.errorText}>{formError}</p>}

        <div className={css.btnRow}>
          <button
            type="submit"
            className={css.submitBtn}
            disabled={createTip.isPending}
          >
            {createTip.isPending ? "Submitting…" : "Submit Tip"}
          </button>
        </div>
      </form>
    </div>
  );
}
