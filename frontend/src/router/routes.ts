/**
 * Route configuration data structure.
 *
 * This module defines the route tree as plain data so that it can be consumed
 * by any router library (react-router-dom v7 is recommended).
 *
 * No router package is installed yet — this file is purely declarative.
 * When react-router-dom is added (Step 04+), wrap these definitions in
 * createBrowserRouter() or <Route> elements.
 *
 * Guard behaviour:
 *   - authRequired: false  → public page, no token check
 *   - authRequired: true   → token must exist (any role)
 *   - minHierarchy          → user.hierarchy_level >= value
 *   - requiredPermissions   → user must have ALL listed permissions
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface RouteConfig {
  /** URL path segment (relative to parent). Use `:param` for dynamic segments. */
  path: string;
  /** Human-readable page title (for <title>, breadcrumbs, etc.) */
  title: string;
  /** Whether authentication is required to access this route */
  authRequired: boolean;
  /** Minimum role hierarchy level needed (0 = any authenticated user) */
  minHierarchy?: number;
  /** Permission codenames the user must possess (AND logic) */
  requiredPermissions?: string[];
  /** Whether the route component should be lazy-loaded */
  lazy: boolean;
  /** Child routes */
  children?: RouteConfig[];
}

// ---------------------------------------------------------------------------
// Well-known hierarchy levels (from project-doc.md §3.1 + accounts.Role)
// ---------------------------------------------------------------------------

export const HIERARCHY = {
  BASE_USER: 0,
  SUSPECT: 0,
  CRIMINAL: 0,
  COMPLAINANT: 1,
  WITNESS: 1,
  JUDGE: 2,
  CORONER: 3,
  CADET: 4,
  PATROL_OFFICER: 5,
  POLICE_OFFICER: 6,
  DETECTIVE: 7,
  SERGEANT: 8,
  CAPTAIN: 9,
  POLICE_CHIEF: 10,
  SYSTEM_ADMIN: 100,
} as const;

// ---------------------------------------------------------------------------
// Route tree
// ---------------------------------------------------------------------------

export const routes: RouteConfig[] = [
  // ── Public ──────────────────────────────────────────────────────────
  {
    path: "/",
    title: "Home",
    authRequired: false,
    lazy: false,
  },
  {
    path: "/login",
    title: "Login",
    authRequired: false,
    lazy: true,
  },
  {
    path: "/register",
    title: "Register",
    authRequired: false,
    lazy: true,
  },

  // ── Authenticated ───────────────────────────────────────────────────
  {
    path: "/dashboard",
    title: "Dashboard",
    authRequired: true,
    lazy: false,
  },
  {
    path: "/profile",
    title: "My Profile",
    authRequired: true,
    lazy: true,
  },
  {
    path: "/notifications",
    title: "Notifications",
    authRequired: true,
    lazy: true,
  },
  {
    path: "/most-wanted",
    title: "Most Wanted",
    authRequired: true,
    minHierarchy: HIERARCHY.BASE_USER,
    lazy: true,
  },

  // ── Cases ───────────────────────────────────────────────────────────
  {
    path: "/cases",
    title: "Cases",
    authRequired: true,
    lazy: true,
    children: [
      {
        path: "new/complaint",
        title: "File Complaint",
        authRequired: true,
        minHierarchy: HIERARCHY.COMPLAINANT,
        lazy: true,
      },
      {
        path: "new/crime-scene",
        title: "Report Crime Scene",
        authRequired: true,
        minHierarchy: HIERARCHY.POLICE_OFFICER,
        lazy: true,
      },
      {
        path: ":caseId",
        title: "Case Detail",
        authRequired: true,
        lazy: true,
        children: [
          {
            path: "evidence",
            title: "Case Evidence",
            authRequired: true,
            lazy: true,
          },
          {
            path: "evidence/new",
            title: "Add Evidence",
            authRequired: true,
            minHierarchy: HIERARCHY.DETECTIVE,
            lazy: true,
          },
          {
            path: "suspects",
            title: "Case Suspects",
            authRequired: true,
            minHierarchy: HIERARCHY.DETECTIVE,
            lazy: true,
          },
          {
            path: "suspects/:suspectId",
            title: "Suspect Detail",
            authRequired: true,
            minHierarchy: HIERARCHY.DETECTIVE,
            lazy: true,
          },
          {
            path: "interrogations",
            title: "Interrogations",
            authRequired: true,
            minHierarchy: HIERARCHY.DETECTIVE,
            requiredPermissions: ["suspects.can_conduct_interrogation"],
            lazy: true,
          },
          {
            path: "trial",
            title: "Trial",
            authRequired: true,
            minHierarchy: HIERARCHY.JUDGE,
            requiredPermissions: ["suspects.can_judge_trial"],
            lazy: true,
          },
        ],
      },
    ],
  },

  // ── Detective Board ─────────────────────────────────────────────────
  {
    path: "/detective-board/:caseId",
    title: "Detective Board",
    authRequired: true,
    minHierarchy: HIERARCHY.DETECTIVE,
    lazy: true,
  },

  // ── Reporting ───────────────────────────────────────────────────────
  {
    path: "/reports",
    title: "General Reporting",
    authRequired: true,
    minHierarchy: HIERARCHY.JUDGE,
    lazy: true,
  },

  // ── Bounty System ───────────────────────────────────────────────────
  {
    path: "/bounty-tips",
    title: "Bounty Tips",
    authRequired: true,
    lazy: true,
    children: [
      {
        path: "new",
        title: "Submit Tip",
        authRequired: true,
        lazy: true,
      },
      {
        path: "verify",
        title: "Verify Reward",
        authRequired: true,
        minHierarchy: HIERARCHY.POLICE_OFFICER,
        lazy: true,
      },
    ],
  },

  // ── Admin Panel ─────────────────────────────────────────────────────
  {
    path: "/admin",
    title: "Admin Panel",
    authRequired: true,
    minHierarchy: HIERARCHY.SYSTEM_ADMIN,
    lazy: true,
    children: [
      {
        path: "users",
        title: "User Management",
        authRequired: true,
        minHierarchy: HIERARCHY.SYSTEM_ADMIN,
        lazy: true,
      },
      {
        path: "roles",
        title: "Role Management",
        authRequired: true,
        minHierarchy: HIERARCHY.SYSTEM_ADMIN,
        lazy: true,
      },
    ],
  },

  // ── 404 catch-all ───────────────────────────────────────────────────
  {
    path: "*",
    title: "Not Found",
    authRequired: false,
    lazy: true,
  },
];
