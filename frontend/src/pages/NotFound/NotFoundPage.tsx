import { Link } from "react-router-dom";
import styles from "./NotFoundPage.module.css";

/**
 * 404 Not Found page — catch-all for unmatched routes.
 */
export default function NotFoundPage() {
  return (
    <div className={styles.container}>
      <p className={styles.code}>404</p>
      <h1 className={styles.title}>Page Not Found</h1>
      <p className={styles.message}>
        The page you&apos;re looking for doesn&apos;t exist or has been moved.
      </p>
      <Link to="/" className={styles.link}>
        Back to Home
      </Link>
    </div>
  );
}
