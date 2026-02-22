// TODO: Define Evidence, TestimonyEvidence, BiologicalEvidence,
//       VehicleEvidence, IdentityEvidence, EvidenceFile interfaces
// Should mirror backend evidence app models

export interface Evidence {
  // TODO: id, case, evidence_type, title, description, registered_by, created_at
}

export interface TestimonyEvidence {
  // TODO: extends Evidence — statement text + media files
}

export interface BiologicalEvidence {
  // TODO: extends Evidence — forensic items, coroner verification result
}

export interface VehicleEvidence {
  // TODO: extends Evidence — model, license_plate XOR serial_number, color
}

export interface IdentityEvidence {
  // TODO: extends Evidence — owner_name, details (key-value JSON)
}

export interface EvidenceFile {
  // TODO: evidence, file, file_type (image/video/audio/document)
}

export enum EvidenceType {
  // TODO: TESTIMONY, BIOLOGICAL, VEHICLE, IDENTITY, OTHER
}
