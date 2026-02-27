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
  /** Permission codenames the user must possess (AND logic) */
  requiredPermissions?: string[];
  /** Whether the route component should be lazy-loaded */
  lazy: boolean;
  /** Child routes */
  children?: RouteConfig[];
}

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
    requiredPermissions: ["suspects.view_suspect"],
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
        requiredPermissions: ["cases.add_casecomplainant"],
        lazy: true,
      },
      {
        path: "new/crime-scene",
        title: "Report Crime Scene",
        authRequired: true,
        requiredPermissions: ["cases.can_create_crime_scene"],
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
            requiredPermissions: ["evidence.add_evidence"],
            lazy: true,
          },
          {
            path: "evidence/:evidenceId",
            title: "Evidence Detail",
            authRequired: true,
            lazy: true,
          },
          {
            path: "suspects",
            title: "Case Suspects",
            authRequired: true,
            requiredPermissions: ["suspects.view_suspect"],
            lazy: true,
          },
          {
            path: "suspects/:suspectId",
            title: "Suspect Detail",
            authRequired: true,
            requiredPermissions: ["suspects.view_suspect"],
            lazy: true,
          },
          {
            path: "interrogations",
            title: "Interrogations",
            authRequired: true,
            requiredPermissions: ["suspects.can_conduct_interrogation"],
            lazy: true,
          },
          {
            path: "trial",
            title: "Trial",
            authRequired: true,
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
    requiredPermissions: ["board.view_detectiveboard"],
    lazy: true,
  },

  // ── Reporting ───────────────────────────────────────────────────────
  {
    path: "/reports",
    title: "General Reporting",
    authRequired: true,
    requiredPermissions: ["cases.can_view_case_report"],
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
        requiredPermissions: ["suspects.can_lookup_bounty_reward"],
        lazy: true,
      },
    ],
  },

  // ── Admin Panel ─────────────────────────────────────────────────────
  {
    path: "/admin",
    title: "Admin Panel",
    authRequired: true,
    requiredPermissions: ["accounts.can_manage_users"],
    lazy: true,
    children: [
      {
        path: "users",
        title: "User Management",
        authRequired: true,
        requiredPermissions: ["accounts.can_manage_users"],
        lazy: true,
      },
      {
        path: "roles",
        title: "Role Management",
        authRequired: true,
        requiredPermissions: ["accounts.can_manage_users"],
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
