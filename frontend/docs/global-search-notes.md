# Global Search Notes

## Endpoint Used

**`GET /api/core/search/`** (requires authentication)

### Query Parameters
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `q` | string | Yes | Search term (min 2 characters) |
| `category` | string | No | Filter to: `cases`, `suspects`, or `evidence` |
| `limit` | integer | No | Max results per category (default 10, max 50) |

### Response Shape
```json
{
  "query": "john",
  "total_results": 15,
  "cases": [
    { "id": 7, "title": "Downtown Heist", "status": "investigation", "crime_level": 2, "crime_level_label": "Level 2 (Medium)", "created_at": "2025-05-01T09:00:00Z" }
  ],
  "suspects": [
    { "id": 42, "full_name": "John Doe", "national_id": "1234567890", "status": "wanted", "case_id": 7, "case_title": "Downtown Heist" }
  ],
  "evidence": [
    { "id": 88, "title": "Fingerprint on glass", "evidence_type": "biological", "evidence_type_label": "Biological / Medical", "case_id": 7, "case_title": "Downtown Heist" }
  ]
}
```

### Error Responses
- `400`: `{ "detail": "Search query must be at least 2 characters." }` or `{ "detail": "Invalid category '...'" }`
- `401`: Missing/invalid auth token

---

## Payload Interpretation

The backend groups results into three separate arrays (`cases`, `suspects`, `evidence`). Each category has a distinct result shape. This is reflected in three typed interfaces:
- `SearchCaseResult`
- `SearchSuspectResult`
- `SearchEvidenceResult`

The search is permission-scoped on the backend — users only see entities they have access to.

---

## Navigation Mapping by Result Type

| Result Type | Click Target | Route |
|-------------|-------------|-------|
| Case | Case detail page | `/cases/:id` |
| Suspect | Suspect detail (within case) | `/cases/:caseId/suspects/:suspectId` |
| Evidence | Evidence list for case | `/cases/:caseId/evidence` |

Suspects and evidence are context-linked to their parent case, so the URLs use the `case_id` from the search result.

---

## Implementation Details

### Debounce
- 350ms debounce on query input via `useDebounce` hook
- No request fires for queries shorter than 2 characters (matching backend minimum)

### React Query Caching
- `queryKey: ["global-search", debouncedQuery, category, limit]`
- `staleTime: 30s` — re-searching the same term within 30s uses cache
- `retry: false` — no auto-retry on search failures

### UI Behavior
- Search appears in the header only when user is authenticated (search requires auth)
- Dropdown appears on focus/typing, closes on:
  - Outside click
  - Escape key
  - Result click (navigates + clears input)
- Results grouped by category with count badges
- Shows loading spinner, empty state, or error message as appropriate

---

## Limitations / Deferred Improvements

1. **Keyboard navigation**: Arrow-key result traversal is not implemented. Only Escape key is handled.
2. **Category filtering UI**: The `category` query param is supported by the hook but no UI toggle is exposed yet. Feature pages could add category tabs.
3. **Highlighting**: Search term highlighting in results is not implemented.
4. **Recent searches**: No history of recent queries.
5. **Mobile UX**: Search collapses with the nav on very small screens. A dedicated search button/modal pattern may be needed for mobile.
6. **Result pagination**: The backend supports a `limit` param but not pagination. If results exceed the limit, some are truncated silently.
