import { useParams } from "react-router-dom";
import { PlaceholderPage } from "../../components/ui";

/**
 * Case detail page placeholder.
 * Shows details, evidence, suspects, and status transitions for a single case.
 */
export default function CaseDetailPage() {
  const { caseId } = useParams();

  return (
    <PlaceholderPage
      title={`Case #${caseId ?? "?"}`}
      description="Full case detail — evidence, suspects, complainants, witnesses, status log, and action buttons based on permissions."
    />
  );
}
