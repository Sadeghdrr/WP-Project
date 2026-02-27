import { useQuery } from "@tanstack/react-query";
import { useAuth } from "../../auth/useAuth";
import { apiGet } from "../../api/client";
import { API } from "../../api/endpoints";
import { ErrorState } from "../../components/ui";
import type { DashboardStats } from "../../types/core";
import styles from "./HomePage.module.css";

/**
 * Home page — public landing page.
 *
 * Requirement (§5.1): General introduction to the system + police department,
 * plus at least 3 statistics on cases.
 *
 * The dashboard stats endpoint requires authentication. When the user is
 * unauthenticated we render graceful "—" placeholders instead of numbers.
 */

// ---------------------------------------------------------------------------
// Data fetching
// ---------------------------------------------------------------------------

async function fetchDashboardStats(): Promise<DashboardStats> {
  const result = await apiGet<DashboardStats>(API.DASHBOARD_STATS);
  if (!result.ok) throw new Error(result.error.message);
  return result.data;
}

const STATS_QUERY_KEY = ["dashboard-stats"] as const;

// ---------------------------------------------------------------------------
// Stat helpers
// ---------------------------------------------------------------------------

interface StatDef {
  label: string;
  value: number | undefined;
  accent?: string;
}

function formatStat(value: number | undefined): string {
  if (value === undefined || value === null) return "—";
  return value.toLocaleString();
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function HomePage() {
  const { status: authStatus } = useAuth();
  const isAuthenticated = authStatus === "authenticated";

  const {
    data: stats,
    isLoading,
    isError,
    refetch,
  } = useQuery<DashboardStats>({
    queryKey: [...STATS_QUERY_KEY],
    queryFn: fetchDashboardStats,
    enabled: authStatus !== "loading",
    staleTime: 5 * 60 * 1000, // 5 min
    retry: isAuthenticated ? 1 : 0,
  });

  const statCards: StatDef[] = [
    { label: "Total Cases", value: stats?.total_cases },
    { label: "Active Cases", value: stats?.active_cases, accent: "warning" },
    { label: "Total Suspects", value: stats?.total_suspects },
    { label: "Employees", value: stats?.total_employees },
  ];

  return (
    <div className={styles.home}>
      {/* ── Hero ─────────────────────────────────────────────────────── */}
      <section className={styles.hero}>
        <h1 className={styles.heroTitle}>LAPD Case Management System</h1>
        <p className={styles.heroSubtitle}>
          Automating police department operations — case management, evidence
          tracking, suspect identification, and judicial proceedings, all in one
          place.
        </p>
      </section>

      {/* ── Statistics ───────────────────────────────────────────────── */}
      <section className={styles.statsSection}>
        <h2 className={styles.sectionTitle}>Department Overview</h2>

        {isLoading && (
          <div className={styles.stats}>
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className={`${styles.statCard} ${styles.skeleton}`}>
                <p className={styles.statValue}>&nbsp;</p>
                <p className={styles.statLabel}>&nbsp;</p>
              </div>
            ))}
          </div>
        )}

        {!isLoading && isError && isAuthenticated && (
          <ErrorState
            message="Unable to load statistics. Please try again later."
            onRetry={() => refetch()}
            compact
          />
        )}

        {!isLoading && (!isError || !isAuthenticated) && (
          <div className={styles.stats}>
            {statCards.map((s) => (
              <div
                key={s.label}
                className={`${styles.statCard} ${
                  s.accent ? styles[`accent_${s.accent}`] ?? "" : ""
                }`}
              >
                <p className={styles.statValue}>{formatStat(s.value)}</p>
                <p className={styles.statLabel}>{s.label}</p>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* ── Duties ───────────────────────────────────────────────────── */}
      <section className={styles.duties}>
        <h2 className={styles.sectionTitle}>Core Duties</h2>
        <ul className={styles.dutyList}>
          <li className={styles.dutyItem}>
            <strong>Case Management</strong> — File complaints, open
            investigations, assign officers, and track case progress.
          </li>
          <li className={styles.dutyItem}>
            <strong>Evidence Handling</strong> — Catalogue, verify, and
            maintain chain-of-custody for all types of evidence.
          </li>
          <li className={styles.dutyItem}>
            <strong>Suspect Identification</strong> — Record suspect details,
            issue arrest warrants, and manage most-wanted lists.
          </li>
          <li className={styles.dutyItem}>
            <strong>Judicial Coordination</strong> — Schedule interrogations,
            coordinate trials, and process bail applications.
          </li>
        </ul>
      </section>
      {/* ── About / Introduction ─────────────────────────────────────── */}
      <section className={styles.intro}>
        <h2 className={styles.sectionTitle}>About the Department</h2>
        <p className={styles.introText}>
          The Los Angeles Police Department (LAPD) is the primary law
          enforcement agency for the city of Los Angeles. Our officers and
          detectives work around the clock to investigate crimes, collect
          evidence, apprehend suspects, and ensure justice is served through
          fair judicial proceedings.
        </p>
        <p className={styles.introText}>
          This system supports the department's daily operations by providing a
          centralised platform for filing complaints, managing active
          investigations, cataloguing physical and digital evidence, tracking
          suspect information, and coordinating bail and trial processes.
        </p>
      </section>
    </div>
  );
}
