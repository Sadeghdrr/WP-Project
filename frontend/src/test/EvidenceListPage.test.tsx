/**
 * EvidenceListPage — unit tests.
 *
 * Tests:
 *   1. Renders evidence list items
 *   2. Clear filters button resets search and type immediately
 *   3. Type filter changes re-fetch
 */

import { describe, it, expect, vi, beforeEach, type Mock } from "vitest";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import EvidenceListPage from "../pages/Evidence/EvidenceListPage";

// Mock the evidence hook
vi.mock("../hooks/useEvidence", () => ({
  useEvidence: vi.fn(),
  EVIDENCE_QUERY_KEY: ["evidence"],
}));

// eslint-disable-next-line @typescript-eslint/no-require-imports
import { useEvidence } from "../hooks/useEvidence";
const mockUseEvidence = useEvidence as Mock;

// Mock the debounce hook to be instant in tests
vi.mock("../hooks", () => ({
  useDebounce: (value: string) => value,
}));

// Mock CSS modules
vi.mock("../pages/Evidence/EvidenceListPage.module.css", () => ({
  default: new Proxy(
    {},
    {
      get: (_target, prop) => String(prop),
    },
  ),
}));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const MOCK_EVIDENCE = [
  {
    id: 1,
    title: "Blood Sample A",
    description: "Found at crime scene",
    evidence_type: "biological",
    evidence_type_display: "Biological",
    case: 42,
    registered_by: 1,
    registered_by_name: "Det. Smith",
    created_at: "2025-01-10T12:00:00Z",
    updated_at: "2025-01-10T12:00:00Z",
  },
  {
    id: 2,
    title: "Stolen Honda Civic",
    description: "VIN cross-referenced",
    evidence_type: "vehicle",
    evidence_type_display: "Vehicle",
    case: 42,
    registered_by: 2,
    registered_by_name: "Off. Jones",
    created_at: "2025-01-11T09:30:00Z",
    updated_at: "2025-01-11T09:30:00Z",
  },
];

function renderPage(caseId = "42") {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[`/cases/${caseId}/evidence`]}>
        <Routes>
          <Route
            path="/cases/:caseId/evidence"
            element={<EvidenceListPage />}
          />
          <Route
            path="/cases/:caseId/evidence/:evidenceId"
            element={<div data-testid="detail-page">Detail</div>}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("EvidenceListPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseEvidence.mockReturnValue({
      data: MOCK_EVIDENCE,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });
  });

  it("renders evidence list items", () => {
    renderPage();
    expect(screen.getByText(/Blood Sample A/)).toBeInTheDocument();
    expect(screen.getByText(/Stolen Honda Civic/)).toBeInTheDocument();
  });

  it("shows Clear button only when filters are active", () => {
    renderPage();
    // Clear button should not exist initially
    expect(screen.queryByText("Clear")).not.toBeInTheDocument();

    // Type some search text
    fireEvent.change(screen.getByPlaceholderText("Search evidence…"), {
      target: { value: "blood" },
    });
    expect(screen.getByText("Clear")).toBeInTheDocument();
  });

  it("clears search and type filter when Clear is clicked", async () => {
    renderPage();
    const searchInput = screen.getByPlaceholderText(
      "Search evidence…",
    ) as HTMLInputElement;

    // Set search and type filter
    fireEvent.change(searchInput, { target: { value: "honda" } });
    const typeSelect = screen.getByRole("combobox") as HTMLSelectElement;
    fireEvent.change(typeSelect, { target: { value: "vehicle" } });

    // Click clear
    fireEvent.click(screen.getByText("Clear"));

    await waitFor(() => {
      expect(searchInput.value).toBe("");
      expect(typeSelect.value).toBe("");
    });
  });

  it("calls useEvidence with case filter", () => {
    renderPage("42");
    expect(mockUseEvidence).toHaveBeenCalledWith(
      expect.objectContaining({ case: 42 }),
    );
  });

  it("renders loading skeletons when loading", () => {
    mockUseEvidence.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });

    renderPage();
    // Should not show evidence items
    expect(screen.queryByText("Blood Sample A")).not.toBeInTheDocument();
  });

  it("renders error state when fetch fails", () => {
    mockUseEvidence.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      error: new Error("Network error"),
      refetch: vi.fn(),
    });

    renderPage();
    expect(screen.getByText("Network error")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /try again/i })).toBeInTheDocument();
  });
});
