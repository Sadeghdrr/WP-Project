import { useState, useCallback } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { createEvidence as createEvidenceApi } from "../../api/evidence";
import { EVIDENCE_QUERY_KEY } from "../../hooks/useEvidence";
import {
  EVIDENCE_TYPE_LABELS,
  EVIDENCE_TYPE_ICONS,
} from "../../lib/evidenceHelpers";
import type { EvidenceType, EvidenceCreateRequest } from "../../types";
import css from "./AddEvidencePage.module.css";

// ---------------------------------------------------------------------------
// Ordered type list for the selector
// ---------------------------------------------------------------------------

const TYPES: EvidenceType[] = [
  "testimony",
  "biological",
  "vehicle",
  "identity",
  "other",
];

// ---------------------------------------------------------------------------
// Key-value pair helper (identity document)
// ---------------------------------------------------------------------------

interface KVPair {
  key: string;
  value: string;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Evidence registration form — dynamic fields by evidence type.
 * Requirement (§4.3, §5.8).
 */
export default function AddEvidencePage() {
  const { caseId } = useParams<{ caseId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // ─── Common fields ─────────────────────────────────────────
  const [evidenceType, setEvidenceType] = useState<EvidenceType | "">("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");

  // ─── Testimony fields ──────────────────────────────────────
  const [statementText, setStatementText] = useState("");

  // ─── Vehicle fields ────────────────────────────────────────
  const [vehicleModel, setVehicleModel] = useState("");
  const [color, setColor] = useState("");
  const [vehicleIdMode, setVehicleIdMode] = useState<"plate" | "serial">(
    "plate",
  );
  const [licensePlate, setLicensePlate] = useState("");
  const [serialNumber, setSerialNumber] = useState("");

  // ─── Identity fields ──────────────────────────────────────
  const [ownerFullName, setOwnerFullName] = useState("");
  const [docDetails, setDocDetails] = useState<KVPair[]>([
    { key: "", value: "" },
  ]);

  // ─── Submission state ──────────────────────────────────────
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [generalError, setGeneralError] = useState("");

  // ─── Key-value helpers ─────────────────────────────────────
  const addKVPair = () =>
    setDocDetails((prev) => [...prev, { key: "", value: "" }]);
  const removeKVPair = (idx: number) =>
    setDocDetails((prev) => prev.filter((_, i) => i !== idx));
  const updateKV = (idx: number, field: "key" | "value", val: string) =>
    setDocDetails((prev) =>
      prev.map((p, i) => (i === idx ? { ...p, [field]: val } : p)),
    );

  // ─── Validation ────────────────────────────────────────────
  const validate = useCallback((): boolean => {
    const errs: Record<string, string> = {};

    if (!evidenceType) errs.evidence_type = "Select an evidence type";
    if (!title.trim()) errs.title = "Title is required";

    if (evidenceType === "vehicle") {
      if (!vehicleModel.trim()) errs.vehicle_model = "Vehicle model is required";
      if (!color.trim()) errs.color = "Color is required";
      // XOR validation matching backend error messages exactly
      const hasPlate = !!licensePlate.trim();
      const hasSerial = !!serialNumber.trim();
      if (hasPlate && hasSerial) {
        errs._xor = "Provide either a license plate or a serial number, not both.";
      } else if (!hasPlate && !hasSerial) {
        if (vehicleIdMode === "plate") {
          errs.license_plate = "License plate is required";
        } else {
          errs.serial_number = "Serial number is required";
        }
      }
    }

    if (evidenceType === "identity") {
      if (!ownerFullName.trim())
        errs.owner_full_name = "Owner full name is required";
    }

    setFieldErrors(errs);
    return Object.keys(errs).length === 0;
  }, [
    evidenceType,
    title,
    vehicleModel,
    color,
    vehicleIdMode,
    licensePlate,
    serialNumber,
    ownerFullName,
  ]);

  // ─── Build payload ─────────────────────────────────────────
  const buildPayload = (): EvidenceCreateRequest | null => {
    if (!evidenceType || !caseId) return null;
    const caseNum = Number(caseId);

    const base = {
      case: caseNum,
      title: title.trim(),
      description: description.trim() || undefined,
    };

    switch (evidenceType) {
      case "testimony":
        return {
          ...base,
          evidence_type: "testimony",
          statement_text: statementText.trim() || undefined,
        };
      case "biological":
        return { ...base, evidence_type: "biological" };
      case "vehicle":
        return {
          ...base,
          evidence_type: "vehicle",
          vehicle_model: vehicleModel.trim(),
          color: color.trim(),
          license_plate: licensePlate.trim(),
          serial_number: serialNumber.trim(),
        };
      case "identity": {
        const details: Record<string, string> = {};
        docDetails.forEach((p) => {
          if (p.key.trim() && p.value.trim()) {
            details[p.key.trim()] = p.value.trim();
          }
        });
        return {
          ...base,
          evidence_type: "identity",
          owner_full_name: ownerFullName.trim(),
          document_details:
            Object.keys(details).length > 0 ? details : undefined,
        };
      }
      case "other":
        return { ...base, evidence_type: "other" };
    }
  };

  // ─── Submitting state ─────────────────────────────────────
  const [isSubmitting, setIsSubmitting] = useState(false);

  // ─── Submit ────────────────────────────────────────────────
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setGeneralError("");

    if (!validate()) return;

    const payload = buildPayload();
    if (!payload) return;

    setIsSubmitting(true);
    try {
      const res = await createEvidenceApi(payload);
      if (!res.ok) {
        // Map backend field errors into form
        if (res.error.fieldErrors) {
          const mapped: Record<string, string> = {};
          for (const [field, msgs] of Object.entries(res.error.fieldErrors)) {
            if (field === "non_field_errors") continue; // handled as generalError
            mapped[field] = msgs.join(", ");
          }
          if (Object.keys(mapped).length > 0) {
            setFieldErrors((prev) => ({ ...prev, ...mapped }));
          }
        }
        setGeneralError(res.error.message);
        return;
      }
      // Success — invalidate evidence queries and navigate
      queryClient.invalidateQueries({ queryKey: EVIDENCE_QUERY_KEY });
      navigate(`/cases/${caseId}/evidence/${res.data.id}`);
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Failed to register evidence";
      setGeneralError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const backUrl = `/cases/${caseId}/evidence`;

  return (
    <div className={css.container}>
      <Link to={backUrl} className={css.backLink}>
        ← Back to evidence list
      </Link>
      <h1>Register Evidence</h1>

      <form className={css.form} onSubmit={handleSubmit}>
        {/* ── Evidence type selector ─────────────────────────── */}
        <div className={css.fieldGroup}>
          <label>Evidence Type *</label>
          <div className={css.typeCards}>
            {TYPES.map((t) => (
              <button
                key={t}
                type="button"
                className={`${css.typeCard} ${evidenceType === t ? css.typeCardActive : ""}`}
                onClick={() => setEvidenceType(t)}
              >
                <span className={css.typeIcon}>
                  {EVIDENCE_TYPE_ICONS[t]}
                </span>
                <span className={css.typeLabel}>
                  {EVIDENCE_TYPE_LABELS[t]}
                </span>
              </button>
            ))}
          </div>
          {fieldErrors.evidence_type && (
            <span className={css.fieldError}>{fieldErrors.evidence_type}</span>
          )}
        </div>

        {/* ── Common fields ──────────────────────────────────── */}
        <div className={css.fieldGroup}>
          <label htmlFor="ev-title">Title *</label>
          <input
            id="ev-title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Short title for this evidence"
          />
          {fieldErrors.title && (
            <span className={css.fieldError}>{fieldErrors.title}</span>
          )}
        </div>

        <div className={css.fieldGroup}>
          <label htmlFor="ev-desc">Description</label>
          <textarea
            id="ev-desc"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Optional description or context"
          />
        </div>

        {/* ── Testimony fields ───────────────────────────────── */}
        {evidenceType === "testimony" && (
          <div className={css.fieldGroup}>
            <label htmlFor="ev-statement">Statement Text</label>
            <textarea
              id="ev-statement"
              value={statementText}
              onChange={(e) => setStatementText(e.target.value)}
              placeholder="Witness or testimonial statement text"
              rows={5}
            />
          </div>
        )}

        {/* ── Vehicle fields ─────────────────────────────────── */}
        {evidenceType === "vehicle" && (
          <>
            <div className={css.fieldGroup}>
              <label htmlFor="ev-vmodel">Vehicle Model *</label>
              <input
                id="ev-vmodel"
                value={vehicleModel}
                onChange={(e) => setVehicleModel(e.target.value)}
                placeholder="e.g. Toyota Camry 2021"
              />
              {fieldErrors.vehicle_model && (
                <span className={css.fieldError}>
                  {fieldErrors.vehicle_model}
                </span>
              )}
            </div>

            <div className={css.fieldGroup}>
              <label htmlFor="ev-color">Color *</label>
              <input
                id="ev-color"
                value={color}
                onChange={(e) => setColor(e.target.value)}
                placeholder="e.g. Black"
              />
              {fieldErrors.color && (
                <span className={css.fieldError}>{fieldErrors.color}</span>
              )}
            </div>

            <div className={css.xorGroup}>
              <div className={css.radioRow}>
                <label>
                  <input
                    type="radio"
                    name="vehicleIdMode"
                    checked={vehicleIdMode === "plate"}
                    onChange={() => {
                      setVehicleIdMode("plate");
                      setSerialNumber("");
                    }}
                  />{" "}
                  License Plate
                </label>
                <label>
                  <input
                    type="radio"
                    name="vehicleIdMode"
                    checked={vehicleIdMode === "serial"}
                    onChange={() => {
                      setVehicleIdMode("serial");
                      setLicensePlate("");
                    }}
                  />{" "}
                  Serial Number
                </label>
              </div>

              {vehicleIdMode === "plate" ? (
                <div className={css.fieldGroup}>
                  <label htmlFor="ev-plate">License Plate *</label>
                  <input
                    id="ev-plate"
                    value={licensePlate}
                    onChange={(e) => setLicensePlate(e.target.value)}
                    placeholder="e.g. ABC-1234"
                  />
                  {fieldErrors.license_plate && (
                    <span className={css.fieldError}>
                      {fieldErrors.license_plate}
                    </span>
                  )}
                </div>
              ) : (
                <div className={css.fieldGroup}>
                  <label htmlFor="ev-serial">Serial Number *</label>
                  <input
                    id="ev-serial"
                    value={serialNumber}
                    onChange={(e) => setSerialNumber(e.target.value)}
                    placeholder="Vehicle serial / VIN"
                  />
                  {fieldErrors.serial_number && (
                    <span className={css.fieldError}>
                      {fieldErrors.serial_number}
                    </span>
                  )}
                </div>
              )}
            </div>
          </>
        )}

        {/* ── Identity fields ────────────────────────────────── */}
        {evidenceType === "identity" && (
          <>
            <div className={css.fieldGroup}>
              <label htmlFor="ev-owner">Owner Full Name *</label>
              <input
                id="ev-owner"
                value={ownerFullName}
                onChange={(e) => setOwnerFullName(e.target.value)}
                placeholder="Full legal name on document"
              />
              {fieldErrors.owner_full_name && (
                <span className={css.fieldError}>
                  {fieldErrors.owner_full_name}
                </span>
              )}
            </div>

            <div className={css.fieldGroup}>
              <label>Document Details (key-value pairs)</label>
              <div className={css.kvPairs}>
                {docDetails.map((pair, idx) => (
                  <div key={idx} className={css.kvRow}>
                    <input
                      placeholder="Key (e.g. ID Number)"
                      value={pair.key}
                      onChange={(e) => updateKV(idx, "key", e.target.value)}
                    />
                    <input
                      placeholder="Value"
                      value={pair.value}
                      onChange={(e) => updateKV(idx, "value", e.target.value)}
                    />
                    {docDetails.length > 1 && (
                      <button
                        type="button"
                        className={css.kvRemoveBtn}
                        onClick={() => removeKVPair(idx)}
                      >
                        ✕
                      </button>
                    )}
                  </div>
                ))}
                <button
                  type="button"
                  className={css.kvAddBtn}
                  onClick={addKVPair}
                >
                  + Add field
                </button>
              </div>
            </div>
          </>
        )}

        {/* ── XOR validation error (vehicle) ────────────────── */}
        {fieldErrors._xor && (
          <div className={css.generalError}>{fieldErrors._xor}</div>
        )}

        {/* ── General error ──────────────────────────────────── */}
        {generalError && (
          <div className={css.generalError}>{generalError}</div>
        )}

        {/* ── Actions ────────────────────────────────────────── */}
        <div className={css.actions}>
          <button
            type="submit"
            className={css.submitBtn}
            disabled={isSubmitting}
          >
            {isSubmitting ? "Registering…" : "Register Evidence"}
          </button>
          <Link to={backUrl} className={css.cancelBtn}>
            Cancel
          </Link>
        </div>
      </form>
    </div>
  );
}
