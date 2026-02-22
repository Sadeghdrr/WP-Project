import React from 'react';

// TODO: Evidence registration form — polymorphic for all evidence types
// - Type selector: Testimony, Biological, Vehicle, Identity, Other
// - Common fields: title, description
// - Type-specific fields:
//   * Testimony: statement text, media upload
//   * Biological: images, coroner result (read-only until verified)
//   * Vehicle: model, color, license_plate XOR serial_number
//   * Identity: owner_name, key-value details (dynamic fields)
//   * Other: title + description only

export const EvidenceForm: React.FC = () => {
  return <form>{/* TODO: Implement Evidence Registration Form */}</form>;
};
