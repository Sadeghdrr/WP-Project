import { Link } from "react-router-dom";
import styles from "./ForbiddenPage.module.css";

/**
 * 403 Forbidden page — shown when user lacks permission for a route.
 */
export default function ForbiddenPage() {
  return (
    <div className={styles.container}>
      <p className={styles.code}>403</p>
      <h1 className={styles.title}>Access Denied</h1>
      <p className={styles.message}>
        You don&apos;t have permission to access this page.
      </p>
      <Link to="/dashboard" className={styles.link}>
        Back to Dashboard
      </Link>
    </div>
  );
}
