/**
 * Permission utility tests — pure functions (no React).
 *
 * Covers: can, canAll, canAny, checkAccess, buildPermissionSet
 */

import { describe, it, expect } from "vitest";
import {
  can,
  canAll,
  canAny,
  checkAccess,
  buildPermissionSet,
} from "../auth/can";

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const PERMS = new Set([
  "cases.view_case",
  "cases.add_case",
  "evidence.view_evidence",
]);

// ---------------------------------------------------------------------------
// can()
// ---------------------------------------------------------------------------

describe("can()", () => {
  it("returns true when the user has the requested permission", () => {
    expect(can(PERMS, "cases.view_case")).toBe(true);
  });

  it("returns false when the user lacks the requested permission", () => {
    expect(can(PERMS, "cases.delete_case")).toBe(false);
  });

  it("returns false for an empty permission set", () => {
    expect(can(new Set(), "cases.view_case")).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// canAll()
// ---------------------------------------------------------------------------

describe("canAll()", () => {
  it("returns true when the user has ALL requested permissions", () => {
    expect(canAll(PERMS, ["cases.view_case", "cases.add_case"])).toBe(true);
  });

  it("returns false when the user is missing at least one permission", () => {
    expect(canAll(PERMS, ["cases.view_case", "cases.delete_case"])).toBe(false);
  });

  it("returns true for an empty requirements array", () => {
    expect(canAll(PERMS, [])).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// canAny()
// ---------------------------------------------------------------------------

describe("canAny()", () => {
  it("returns true when the user has at least one of the permissions", () => {
    expect(canAny(PERMS, ["cases.delete_case", "cases.view_case"])).toBe(true);
  });

  it("returns false when the user has none of the permissions", () => {
    expect(canAny(PERMS, ["accounts.view_role", "accounts.add_role"])).toBe(false);
  });

  it("returns false for an empty requirements array", () => {
    expect(canAny(PERMS, [])).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// checkAccess()
// ---------------------------------------------------------------------------

describe("checkAccess()", () => {
  it("returns true when no requirements are specified", () => {
    expect(checkAccess(PERMS, {})).toBe(true);
  });

  it("returns true when all permission requirements are met", () => {
    expect(
      checkAccess(PERMS, {
        permissions: ["cases.view_case"],
      }),
    ).toBe(true);
  });

  it("returns false when permissions are missing", () => {
    expect(
      checkAccess(PERMS, {
        permissions: ["cases.delete_case"],
      }),
    ).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// buildPermissionSet()
// ---------------------------------------------------------------------------

describe("buildPermissionSet()", () => {
  it("builds a Set from a permission list", () => {
    const perms = buildPermissionSet(["a.b", "c.d"]);
    expect(perms.has("a.b")).toBe(true);
    expect(perms.has("c.d")).toBe(true);
    expect(perms.has("e.f")).toBe(false);
  });

  it("returns an empty Set for an empty array", () => {
    const perms = buildPermissionSet([]);
    expect(perms.size).toBe(0);
  });
});
