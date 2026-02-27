import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useCreateCrimeSceneCase } from "../../hooks/useCases";
import type { CrimeLevel } from "../../types";
import css from "./CrimeScenePage.module.css";

interface WitnessEntry {
  full_name: string;
  phone_number: string;
  national_id: string;
}

const emptyWitness = (): WitnessEntry => ({
  full_name: "",
  phone_number: "",
  national_id: "",
});

/**
 * Report a crime scene (case creation via crime scene).
 * Requirement (§4.2.2).
 */
export default function CrimeScenePage() {
  const navigate = useNavigate();
  const createCase = useCreateCrimeSceneCase();

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [crimeLevel, setCrimeLevel] = useState<CrimeLevel>(1);
  const [incidentDate, setIncidentDate] = useState("");
  const [location, setLocation] = useState("");
  const [witnesses, setWitnesses] = useState<WitnessEntry[]>([]);
  const [formError, setFormError] = useState("");

  const addWitness = () => setWitnesses((w) => [...w, emptyWitness()]);
  const removeWitness = (idx: number) =>
    setWitnesses((w) => w.filter((_, i) => i !== idx));
  const updateWitness = (
    idx: number,
    field: keyof WitnessEntry,
    value: string,
  ) =>
    setWitnesses((w) =>
      w.map((entry, i) => (i === idx ? { ...entry, [field]: value } : entry)),
    );

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

    // Filter out empty witness rows
    const validWitnesses = witnesses.filter(
      (w) => w.full_name.trim() || w.phone_number.trim() || w.national_id.trim(),
    );

    createCase.mutate(
      {
        title: title.trim(),
        description: description.trim(),
        crime_level: crimeLevel,
        ...(incidentDate ? { incident_date: incidentDate } : {}),
        ...(location.trim() ? { location: location.trim() } : {}),
        ...(validWitnesses.length > 0 ? { witnesses: validWitnesses } : {}),
      },
      {
        onSuccess: (data) => {
          navigate(`/cases/${data.id}`);
        },
        onError: (err) => setFormError(err.message),
      },
    );
  };

  return (
    <div className={css.container}>
      <Link to="/cases" className={css.backLink}>
        ← Back to Cases
      </Link>

      <div className={css.header}>
        <h1>Report Crime Scene</h1>
        <p className={css.subtitle}>
          Log crime-scene details, time/date, and witness information to create a new case.
        </p>
      </div>

      <form className={css.form} onSubmit={handleSubmit}>
        <div className={css.field}>
          <label htmlFor="title">Title *</label>
          <input
            id="title"
            type="text"
            placeholder="Brief title for the crime scene report"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
          />
        </div>

        <div className={css.field}>
          <label htmlFor="description">Description *</label>
          <textarea
            id="description"
            placeholder="Describe the crime scene in detail…"
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
            placeholder="e.g. Corner of 5th & Broadway"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
          />
          <span className={css.hint}>Optional — where is the crime scene?</span>
        </div>

        {/* ── Witnesses ──────────────────────────────────────── */}
        <div className={css.witnessSection}>
          <div className={css.witnessSectionHeader}>
            <h3>Witnesses</h3>
            <button type="button" className={css.addBtn} onClick={addWitness}>
              + Add Witness
            </button>
          </div>

          {witnesses.length === 0 && (
            <p className={css.hint}>No witnesses added yet.</p>
          )}

          {witnesses.map((w, idx) => (
            <div key={idx} className={css.witnessCard}>
              <div className={css.witnessFields}>
                <input
                  placeholder="Full name"
                  value={w.full_name}
                  onChange={(e) => updateWitness(idx, "full_name", e.target.value)}
                />
                <input
                  placeholder="Phone number"
                  value={w.phone_number}
                  onChange={(e) => updateWitness(idx, "phone_number", e.target.value)}
                />
                <input
                  placeholder="National ID"
                  value={w.national_id}
                  onChange={(e) => updateWitness(idx, "national_id", e.target.value)}
                />
              </div>
              <button
                type="button"
                className={css.removeBtn}
                onClick={() => removeWitness(idx)}
              >
                Remove
              </button>
            </div>
          ))}
        </div>

        {formError && <p className={css.errorText}>{formError}</p>}

        <div className={css.btnRow}>
          <button
            type="submit"
            className={css.submitBtn}
            disabled={createCase.isPending}
          >
            {createCase.isPending ? "Submitting…" : "Report Crime Scene"}
          </button>
        </div>
      </form>
    </div>
  );
}
