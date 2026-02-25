import styles from "./PlaceholderPage.module.css";

interface PlaceholderPageProps {
  title: string;
  description?: string;
}

/**
 * Reusable placeholder for pages that are not yet implemented.
 * Shows a clear title and description so developers know what goes here.
 */
export default function PlaceholderPage({
  title,
  description = "This page will be implemented in a future step.",
}: PlaceholderPageProps) {
  return (
    <div className={styles.placeholder}>
      <h1 className={styles.title}>{title}</h1>
      <p className={styles.subtitle}>{description}</p>
      <span className={styles.badge}>Placeholder</span>
    </div>
  );
}
