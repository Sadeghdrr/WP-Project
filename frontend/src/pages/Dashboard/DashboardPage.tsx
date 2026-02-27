import { Link } from "react-router-dom";
import { useAuth } from "../../auth/useAuth";
import { canAny } from "../../auth/can";
import { P } from "../../auth/permissions";
import { useDashboardStats } from "../../hooks/useDashboardStats";
import { Skeleton, ErrorState } from "../../components/ui";
import type { DashboardStats } from "../../types/core";
import styles from "./DashboardPage.module.css";

// ---------------------------------------------------------------------------
// Module visibility config — permission-driven, no role-name hardcoding
// ---------------------------------------------------------------------------

interface ModuleDef {
  key: string;
  /** At least one of these permissions must be present to show the module */
  anyPermission: readonly string[];
}

/**
 * Defines which dashboard modules are visible to the user based on their
 * permissions. Uses OR logic — if the user has *any* listed permission,
 * the module is shown.
 *
 * This replaces hardcoded role-name checks and automatically adapts when
 * roles/permissions are modified at runtime via the admin panel.
 */
const MODULE_VISIBILITY: Record<string, ModuleDef> = {
  casesByStatus: {
    key: "casesByStatus",
    anyPermission: [P.CASES.VIEW_CASE],
  },
  casesByCrimeLevel: {
    key: "casesByCrimeLevel",
    anyPermission: [P.CASES.VIEW_CASE],
  },
  topWanted: {
    key: "topWanted",
    anyPermission: [P.SUSPECTS.VIEW_SUSPECT],
  },
  evidence: {
    key: "evidence",
    anyPermission: [P.EVIDENCE.VIEW_EVIDENCE],
  },
  detectiveBoard: {
    key: "detectiveBoard",
    anyPermission: [P.BOARD.VIEW_DETECTIVEBOARD],
  },
  interrogations: {
    key: "interrogations",
    anyPermission: [P.SUSPECTS.VIEW_INTERROGATION, P.SUSPECTS.CAN_CONDUCT_INTERROGATION],
  },
  trials: {
    key: "trials",
    anyPermission: [P.SUSPECTS.VIEW_TRIAL, P.SUSPECTS.CAN_JUDGE_TRIAL],
  },
  bountyTips: {
    key: "bountyTips",
    anyPermission: [P.SUSPECTS.VIEW_BOUNTYTIP, P.SUSPECTS.CAN_REVIEW_BOUNTY_TIP],
  },
  reporting: {
    key: "reporting",
    anyPermission: [P.CASES.VIEW_CASE],
  },
  admin: {
    key: "admin",
    anyPermission: [P.ACCOUNTS.VIEW_USER, P.ACCOUNTS.VIEW_ROLE],
  },
};

function useVisibleModules() {
  const { permissionSet } = useAuth();
  const visible = new Set<string>();
  for (const [key, def] of Object.entries(MODULE_VISIBILITY)) {
    if (canAny(permissionSet, def.anyPermission)) {
      visible.add(key);
    }
  }
  return visible;
}

// ---------------------------------------------------------------------------
// Quick action definitions (permission-gated)
// ---------------------------------------------------------------------------

interface QuickAction {
  label: string;
  icon: string;
  to: string;
  anyPermission: readonly string[];
}

const QUICK_ACTIONS: QuickAction[] = [
  {
    label: "File Complaint",
    icon: "📝",
    to: "/cases/new/complaint",
    anyPermission: [P.CASES.ADD_CASECOMPLAINANT],
  },
  {
    label: "Report Crime Scene",
    icon: "🔍",
    to: "/cases/new/crime-scene",
    anyPermission: [P.CASES.ADD_CASE],
  },
  {
    label: "Browse Cases",
    icon: "📋",
    to: "/cases",
    anyPermission: [P.CASES.VIEW_CASE],
  },
  {
    label: "Most Wanted",
    icon: "🎯",
    to: "/most-wanted",
    anyPermission: [P.SUSPECTS.VIEW_SUSPECT],
  },
  {
    label: "Submit Tip",
    icon: "💡",
    to: "/bounty-tips/new",
    anyPermission: [P.SUSPECTS.ADD_BOUNTYTIP],
  },
  {
    label: "Admin Panel",
    icon: "⚙️",
    to: "/admin",
    anyPermission: [P.ACCOUNTS.VIEW_USER, P.ACCOUNTS.VIEW_ROLE],
  },
];

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function StatsOverview({ stats }: { stats: DashboardStats }) {
  const items = [
    { label: "Total Cases", value: stats.total_cases, accent: "" },
    { label: "Active", value: stats.active_cases, accent: styles.statActive },
    { label: "Closed", value: stats.closed_cases, accent: styles.statClosed },
    { label: "Voided", value: stats.voided_cases, accent: styles.statDanger },
    { label: "Suspects", value: stats.total_suspects, accent: styles.statInfo },
    { label: "Evidence", value: stats.total_evidence, accent: "" },
    { label: "Employees", value: stats.total_employees, accent: "" },
  ];

  return (
    <div className={styles.statsGrid}>
      {items.map((item) => (
        <div
          key={item.label}
          className={`${styles.statCard} ${item.accent}`}
        >
          <p className={styles.statValue}>{item.value.toLocaleString()}</p>
          <p className={styles.statLabel}>{item.label}</p>
        </div>
      ))}
    </div>
  );
}

function StatsOverviewSkeleton() {
  return (
    <div className={styles.skeletonGrid}>
      {Array.from({ length: 8 }).map((_, i) => (
        <div key={i} className={styles.skeletonCard}>
          <Skeleton variant="text" width="40%" />
          <Skeleton variant="text" width="70%" height="1.75rem" />
        </div>
      ))}
    </div>
  );
}

function CasesByStatusWidget({ stats }: { stats: DashboardStats }) {
  if (!stats.cases_by_status?.length) return null;
  return (
    <div className={styles.widget}>
      <div className={styles.widgetHeader}>
        <h3 className={styles.widgetTitle}>
          <span className={styles.widgetIcon}>📊</span> Cases by Status
        </h3>
        <Link to="/cases" className={styles.widgetLink}>View all →</Link>
      </div>
      <div className={styles.widgetBody}>
        <ul className={styles.breakdownList}>
          {stats.cases_by_status.map((entry) => (
            <li key={entry.status} className={styles.breakdownItem}>
              <span className={styles.breakdownLabel}>{entry.label}</span>
              <span className={styles.breakdownCount}>{entry.count}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function CasesByCrimeLevelWidget({ stats }: { stats: DashboardStats }) {
  if (!stats.cases_by_crime_level?.length) return null;
  return (
    <div className={styles.widget}>
      <div className={styles.widgetHeader}>
        <h3 className={styles.widgetTitle}>
          <span className={styles.widgetIcon}>⚖️</span> Cases by Crime Level
        </h3>
      </div>
      <div className={styles.widgetBody}>
        <ul className={styles.breakdownList}>
          {stats.cases_by_crime_level.map((entry) => (
            <li key={entry.crime_level} className={styles.breakdownItem}>
              <span className={styles.breakdownLabel}>{entry.label}</span>
              <span className={styles.breakdownCount}>{entry.count}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function TopWantedWidget({ stats }: { stats: DashboardStats }) {
  if (!stats.top_wanted_suspects?.length) return null;
  return (
    <div className={styles.widget}>
      <div className={styles.widgetHeader}>
        <h3 className={styles.widgetTitle}>
          <span className={styles.widgetIcon}>🎯</span> Top Wanted
        </h3>
        <Link to="/most-wanted" className={styles.widgetLink}>View all →</Link>
      </div>
      <div className={styles.widgetBody}>
        <table className={styles.wantedTable}>
          <thead>
            <tr>
              <th>Name</th>
              <th>Score</th>
              <th>Days</th>
            </tr>
          </thead>
          <tbody>
            {stats.top_wanted_suspects.slice(0, 5).map((suspect) => (
              <tr key={suspect.id}>
                <td className={styles.wantedName}>{suspect.full_name}</td>
                <td className={styles.wantedScore}>{suspect.most_wanted_score}</td>
                <td>{suspect.days_wanted}d</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function RecentActivityWidget({ stats }: { stats: DashboardStats }) {
  if (!stats.recent_activity?.length) return null;
  return (
    <div className={styles.widget}>
      <div className={styles.widgetHeader}>
        <h3 className={styles.widgetTitle}>
          <span className={styles.widgetIcon}>🕒</span> Recent Activity
        </h3>
      </div>
      <div className={styles.widgetBody}>
        <ul className={styles.activityList}>
          {stats.recent_activity.slice(0, 8).map((item, idx) => (
            <li key={idx} className={styles.activityItem}>
              <span className={styles.activityDesc}>{item.description}</span>
              <span className={styles.activityMeta}>
                {item.actor ? `${item.actor} · ` : ""}
                {new Date(item.timestamp).toLocaleString()}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function EvidenceWidget({ stats }: { stats: DashboardStats }) {
  return (
    <div className={styles.widget}>
      <div className={styles.widgetHeader}>
        <h3 className={styles.widgetTitle}>
          <span className={styles.widgetIcon}>🧪</span> Evidence Overview
        </h3>
      </div>
      <div className={styles.widgetBody}>
        <ul className={styles.breakdownList}>
          <li className={styles.breakdownItem}>
            <span className={styles.breakdownLabel}>Total Evidence Items</span>
            <span className={styles.breakdownCount}>{stats.total_evidence}</span>
          </li>
          <li className={styles.breakdownItem}>
            <span className={styles.breakdownLabel}>Unassigned</span>
            <span className={styles.breakdownCount}>{stats.unassigned_evidence_count}</span>
          </li>
        </ul>
      </div>
    </div>
  );
}

function DetectiveBoardWidget() {
  return (
    <div className={styles.widget}>
      <div className={styles.widgetHeader}>
        <h3 className={styles.widgetTitle}>
          <span className={styles.widgetIcon}>🗺️</span> Detective Board
        </h3>
      </div>
      <div className={styles.widgetBody}>
        <p style={{ fontSize: "0.875rem", color: "var(--color-text-muted)", margin: 0 }}>
          Open a case to access its detective board — pin evidence, suspects,
          and notes to a visual canvas with connections.
        </p>
        <div style={{ marginTop: "var(--space-sm)" }}>
          <Link to="/cases" className={styles.actionLink}>
            📋 Browse Cases
          </Link>
        </div>
      </div>
    </div>
  );
}

function QuickActionsWidget({ permissionSet }: { permissionSet: ReadonlySet<string> }) {
  const available = QUICK_ACTIONS.filter((a) => canAny(permissionSet, a.anyPermission));
  if (available.length === 0) return null;
  return (
    <div className={styles.widget}>
      <div className={styles.widgetHeader}>
        <h3 className={styles.widgetTitle}>
          <span className={styles.widgetIcon}>⚡</span> Quick Actions
        </h3>
      </div>
      <div className={styles.widgetBody}>
        <div className={styles.quickActions}>
          {available.map((action) => (
            <Link key={action.to} to={action.to} className={styles.actionLink}>
              {action.icon} {action.label}
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}

function ModuleWidgetsSkeleton() {
  return (
    <div className={styles.moduleGrid}>
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className={styles.skeletonCard} style={{ minHeight: 180 }}>
          <Skeleton variant="text" width="60%" />
          <div style={{ marginTop: 12 }}>
            <Skeleton count={4} />
          </div>
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Dashboard Page
// ---------------------------------------------------------------------------

/**
 * Modular Dashboard (§5.3 — 800 pts).
 *
 * Renders permission-aware modules/widgets driven by the user's permission
 * set. No role-name hardcoding — visibility is determined by checking
 * `canAny(permissionSet, requiredPermissions)` for each module.
 *
 * Data source: GET /api/core/dashboard/ (role-aware backend aggregation).
 */
export default function DashboardPage() {
  const { user, permissionSet } = useAuth();
  const { data: stats, isLoading, isError, error, refetch } = useDashboardStats();
  const visibleModules = useVisibleModules();

  const greeting = user
    ? `Welcome back, ${user.first_name || user.username}`
    : "Dashboard";

  const roleLabel = user?.role_detail?.name ?? "Unknown role";

  // If user has zero visible modules, show a graceful empty state
  const hasModules = visibleModules.size > 0;

  return (
    <div className={styles.page}>
      {/* Header */}
      <div className={styles.pageHeader}>
        <h1 className={styles.pageTitle}>{greeting}</h1>
        <p className={styles.pageSubtitle}>
          Role: {roleLabel} · Your personalized overview of department operations.
        </p>
      </div>

      {/* Loading state */}
      {isLoading && (
        <>
          <StatsOverviewSkeleton />
          <ModuleWidgetsSkeleton />
        </>
      )}

      {/* Error state */}
      {isError && (
        <ErrorState
          message={
            error instanceof Error
              ? error.message
              : "Failed to load dashboard data."
          }
          onRetry={() => refetch()}
        />
      )}

      {/* Loaded state */}
      {stats && (
        <>
          {/* Top-level stats — always visible for authenticated users */}
          <StatsOverview stats={stats} />

          {/* Quick Actions */}
          <div style={{ marginBottom: "var(--space-md)" }}>
            <QuickActionsWidget permissionSet={permissionSet} />
          </div>

          {/* Permission-gated module widgets */}
          {hasModules ? (
            <div className={styles.moduleGrid}>
              {visibleModules.has("casesByStatus") && (
                <CasesByStatusWidget stats={stats} />
              )}
              {visibleModules.has("casesByCrimeLevel") && (
                <CasesByCrimeLevelWidget stats={stats} />
              )}
              {visibleModules.has("topWanted") && (
                <TopWantedWidget stats={stats} />
              )}
              {visibleModules.has("evidence") && (
                <EvidenceWidget stats={stats} />
              )}
              {visibleModules.has("detectiveBoard") && (
                <DetectiveBoardWidget />
              )}
              <RecentActivityWidget stats={stats} />
            </div>
          ) : (
            <div className={styles.emptyDash}>
              <div className={styles.emptyIcon}>🔒</div>
              <h2 className={styles.emptyTitle}>No modules available</h2>
              <p className={styles.emptyDesc}>
                Your current role does not have permissions to view any
                dashboard modules. Contact your administrator for access.
              </p>
            </div>
          )}
        </>
      )}
    </div>
  );
}

