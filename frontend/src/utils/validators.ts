/**
 * Client-side validation helpers for form inputs.
 */

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const PHONE_RE = /^09\d{9}$/;
const NATIONAL_ID_RE = /^\d{10}$/;
const LICENSE_PLATE_RE = /^\d{2}[\u0600-\u06FF]\d{3}-\d{2}$/;

export function validateEmail(email: string): boolean {
  return EMAIL_RE.test(email);
}

export function validatePhoneNumber(phone: string): boolean {
  return PHONE_RE.test(phone);
}

export function validateNationalId(id: string): boolean {
  return NATIONAL_ID_RE.test(id);
}

export interface PasswordValidation {
  valid: boolean;
  errors: string[];
}

export function validatePassword(password: string): PasswordValidation {
  const errors: string[] = [];
  if (password.length < 8) errors.push('Must be at least 8 characters');
  if (!/[A-Z]/.test(password)) errors.push('Must contain an uppercase letter');
  if (!/[a-z]/.test(password)) errors.push('Must contain a lowercase letter');
  if (!/\d/.test(password)) errors.push('Must contain a digit');
  return { valid: errors.length === 0, errors };
}

export function validateLicensePlate(plate: string): boolean {
  return LICENSE_PLATE_RE.test(plate);
}

/**
 * XOR check for vehicle evidence:
 * exactly one of (plate, serial) must be provided.
 */
export function validateVehicleXOR(
  plate?: string,
  serial?: string,
): boolean {
  const hasPlate = !!plate?.trim();
  const hasSerial = !!serial?.trim();
  return hasPlate !== hasSerial; // XOR
}
