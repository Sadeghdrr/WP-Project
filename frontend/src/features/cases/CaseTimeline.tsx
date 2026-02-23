/**
 * CaseTimeline — visual timeline of case status transitions.
 */
import type { CaseStatusLog } from '@/types/case.types';

interface CaseTimelineProps {
  logs: CaseStatusLog[];
}

export function CaseTimeline({ logs }: CaseTimelineProps) {
  if (logs.length === 0) {
    return <p className="text-muted">No status changes recorded yet.</p>;
  }

  return (
    <div className="case-timeline">
      {logs.map((log) => (
        <div key={log.id} className="case-timeline__item">
          <div className="case-timeline__marker" />
          <div className="case-timeline__content">
            <div className="case-timeline__header">
              <strong>{log.to_status.replace(/_/g, ' ')}</strong>
              <span className="case-timeline__date">
                {new Date(log.created_at).toLocaleString()}
              </span>
            </div>
            {log.changed_by && (
              <p className="case-timeline__actor">
                by {typeof log.changed_by === 'object' ? `${log.changed_by.first_name} ${log.changed_by.last_name}` : log.changed_by}
              </p>
            )}
            {log.message && (
              <p className="case-timeline__message">{log.message}</p>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
