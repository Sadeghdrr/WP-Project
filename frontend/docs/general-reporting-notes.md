# General Reporting — Implementation Notes

## Endpoints Used

| Endpoint                          | Method | Purpose                                   |
|-----------------------------------|--------|-------------------------------------------|
| `GET /api/cases/`                 | GET    | List all cases for the reporting index     |
| `GET /api/cases/{id}/report/`     | GET    | Full aggregated case report (single case)  |

## Report Sections Rendered

The case report view (`/reports/:caseId`) renders the following sections from the `CaseReportSerializer` payload:

1. **Case Information** — title, status, crime level, creation type, incident date, location, created/updated timestamps, rejection count, description
2. **Personnel Involved** — created_by, approved_by, assigned detective/sergeant/captain/judge (name + role)
3. **Complainants** — name, primary flag, status, reviewed by
4. **Witnesses** — full name, phone number, national ID
5. **Evidence & Testimonies** — title, type, registered by, created date, description
6. **Suspects** — full name, national ID, status, wanted since, days wanted, identified by, sergeant approval, with nested:
   - **Interrogations** — detective, sergeant, guilt scores, notes, date
   - **Trials** — judge, verdict, punishment title/description, date
7. **Status History** — timeline of status transitions with changed_by, message, timestamps
8. **Calculations** — crime level degree, days since creation, tracking threshold, reward (Rials)

## Print / Export Approach

- A **Print button** triggers `window.print()` for browser-native print dialog
- `@media print` CSS rules:
  - Hide top bar (back link + print button)
  - Remove max-width constraints
  - `break-inside: avoid` on sections and suspect cards
  - Force color-adjust on badges for consistent badge printing
- No server-side PDF generation (not required by project-doc)

## Access-Control Handling

- The **report list** (`/reports`) is visible to all authenticated users (uses standard cases list endpoint)
- The **individual report** (`/reports/:caseId`) calls `GET /api/cases/{id}/report/` which is backend-restricted to:
  - Judge
  - Captain
  - Police Chief
  - System Administrator
- **403 responses** are caught and render a dedicated "Access Denied" UI with explanation
- **404 responses** are handled as standard errors
- No retry on 403/404 errors

## Deferred Enhancements

- PDF generation/download (not required by project-doc)
- Server-side report pagination for very large datasets
- Report filtering by date range, status, crime level directly on the report list
- Printable header/footer with page numbers
- Chart/graph visualizations for case statistics
