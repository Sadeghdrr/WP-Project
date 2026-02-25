import styles from "./HomePage.module.css";

/**
 * Home page — public landing page.
 *
 * Requirement (§5.1): General introduction to the system + police department,
 * plus at least 3 statistics on cases.
 *
 * Stats will be fetched from GET /api/core/stats/ in a later step.
 * For now, placeholder values are rendered.
 */
export default function HomePage() {
  return (
    <div className={styles.home}>
      <section className={styles.hero}>
        <h1 className={styles.heroTitle}>LAPD Case Management System</h1>
        <p className={styles.heroSubtitle}>
          Automating police department operations — case management, evidence
          tracking, suspect identification, and judicial proceedings, all in one
          place.
        </p>
      </section>

      <section className={styles.stats}>
        <div className={styles.statCard}>
          <p className={styles.statValue}>—</p>
          <p className={styles.statLabel}>Solved Cases</p>
        </div>
        <div className={styles.statCard}>
          <p className={styles.statValue}>—</p>
          <p className={styles.statLabel}>Organization Employees</p>
        </div>
        <div className={styles.statCard}>
          <p className={styles.statValue}>—</p>
          <p className={styles.statLabel}>Active Cases</p>
        </div>
      </section>
    </div>
  );
}
