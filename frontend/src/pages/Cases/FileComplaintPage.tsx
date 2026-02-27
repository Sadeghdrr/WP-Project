import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useCreateComplaintCase } from "../../hooks/useCases";
import { submitForReview } from "../../api/cases";
import type { CrimeLevel, CaseDetail } from "../../types";
import css from "./FileComplaintPage.module.css";

/**
 * File a complaint (case creation via complaint).
 * Requirement (§4.2.1).
 */
export default function FileComplaintPage() {
  const navigate = useNavigate();
  const createCase = useCreateComplaintCase();

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [crimeLevel, setCrimeLevel] = useState<CrimeLevel>(1);
  const [incidentDate, setIncidentDate] = useState("");
  const [location, setLocation] = useState("");
  const [formError, setFormError] = useState("");

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    setFormError("");

    if (!title.trim()) {
      setFormError("Title is required.");
      return;
    }
    if (!description.trim()) {
      setFormError("Description is required.");
      return;
    }

    createCase.mutate(
      {
        title: title.trim(),
        description: description.trim(),
        crime_level: crimeLevel,
        ...(incidentDate ? { incident_date: incidentDate } : {}),
        ...(location.trim() ? { location: location.trim() } : {}),
      },
      {
        onSuccess: async (data: CaseDetail) => {
          // Step 2: Submit the created case for review
          try {
            await submitForReview(data.id);
          } catch {
            // If submit fails, still navigate — user can submit from detail page
          }
          navigate(`/cases/${data.id}`);
        },
        onError: (err: Error) => setFormError(err.message),
      },
    );
  };

  return (
    <div className={css.container}>
      <Link to="/cases" className={css.backLink}>
        ← Back to Cases
      </Link>

      <div className={css.header}>
        <h1>File a Complaint</h1>
        <p className={css.subtitle}>
          Submit complaint details for initial review by a cadet and then a police officer.
        </p>
      </div>

      <form className={css.form} onSubmit={handleSubmit}>
        <div className={css.field}>
          <label htmlFor="title">Title *</label>
          <input
            id="title"
            type="text"
            placeholder="Brief title for the complaint"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
          />
        </div>

        <div className={css.field}>
          <label htmlFor="description">Description *</label>
          <textarea
            id="description"
            placeholder="Describe the incident in detail…"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            required
          />
        </div>

        <div className={css.field}>
          <label htmlFor="crimeLevel">Crime Level *</label>
          <select
            id="crimeLevel"
            value={crimeLevel}
            onChange={(e) => setCrimeLevel(Number(e.target.value) as CrimeLevel)}
          >
            <option value={1}>Level 3 — Minor</option>
            <option value={2}>Level 2 — Medium</option>
            <option value={3}>Level 1 — Major</option>
            <option value={4}>Critical</option>
          </select>
        </div>

        <div className={css.field}>
          <label htmlFor="incidentDate">Incident Date</label>
          <input
            id="incidentDate"
            type="datetime-local"
            value={incidentDate}
            onChange={(e) => setIncidentDate(e.target.value)}
          />
          <span className={css.hint}>Optional — when did the incident occur?</span>
        </div>

        <div className={css.field}>
          <label htmlFor="location">Location</label>
          <input
            id="location"
            type="text"
            placeholder="e.g. 123 Main St, Downtown"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
          />
          <span className={css.hint}>Optional — where did the incident take place?</span>
        </div>

        {formError && <p className={css.errorText}>{formError}</p>}

        <div className={css.btnRow}>
          <button
            type="submit"
            className={css.submitBtn}
            disabled={createCase.isPending}
          >
            {createCase.isPending ? "Submitting…" : "File Complaint"}
          </button>
        </div>
      </form>
    </div>
  );
}
