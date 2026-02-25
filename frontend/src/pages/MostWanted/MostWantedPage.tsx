import { PlaceholderPage } from "../../components/ui";

/**
 * Most Wanted page placeholder.
 * Requirement (§5.5): Display heavily wanted criminals/suspects (300 pts).
 */
export default function MostWantedPage() {
  return (
    <PlaceholderPage
      title="Most Wanted"
      description="Suspects wanted for over a month, ranked by max-wanted-days × crime-level. Shows bounty amounts and details."
    />
  );
}
