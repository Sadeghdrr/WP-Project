// TODO: Define Case, Complaint, CaseWitness, CaseComplainant, CaseStatusLog interfaces
// Should mirror backend cases app models

export interface Case {
  // TODO: id, title, description, crime_level, status, creation_type, assigned_detective, etc.
}

export interface CaseComplainant {
  // TODO: case, user, status (pending/approved/rejected), rejection_count
}

export interface CaseWitness {
  // TODO: case, phone_number, national_id, name, statement
}

export interface CaseStatusLog {
  // TODO: case, old_status, new_status, changed_by, message, timestamp
}

export enum CrimeLevel {
  // TODO: LEVEL_3 = 1, LEVEL_2 = 2, LEVEL_1 = 3, CRITICAL = 4
}

export enum CaseStatus {
  // TODO: Mirror backend CaseStatus choices
}

export enum CaseCreationType {
  // TODO: COMPLAINT, CRIME_SCENE
}
