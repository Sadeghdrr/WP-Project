/**
 * Case detail page — full case info, timeline, review actions.
 * Role-based: Cadet/Officer see ReviewActionPanel when status matches.
 */

import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { CaseResubmitSection } from '../../features/cases/CaseResubmitSection';
import {
  getCaseDetail,
  cadetReview,
  officerReview,
  reviewComplainant,
} from '../../services/api/cases.api';
import { useAuth } from '../../hooks/useAuth';
import { usePermissions } from '../../hooks/usePermissions';
import { StatusBadge } from '../../components/cases/StatusBadge';
import { CaseTimeline } from '../../components/cases/CaseTimeline';
import { ReviewActionPanel } from '../../components/cases/ReviewActionPanel';
import { ComplainantManager } from '../../features/cases/ComplainantManager';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { CasesPerms } from '../../config/permissions';
import { CaseStatus } from '../../types/case.types';
import type { Case } from '../../types/case.types';

const VOIDED_MESSAGE =
  'این پرونده به دلیل ارسال‌های نامعتبر مکرر باطل شده است.';

export const CaseDetailsPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { hasPermission } = usePermissions();
  const [caseData, setCaseData] = useState<Case | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canReviewComplaint = hasPermission(CasesPerms.CAN_REVIEW_COMPLAINT);
  const canApproveCase = hasPermission(CasesPerms.CAN_APPROVE_CASE);
  const isCadet = canReviewComplaint;
  const isOfficer = canApproveCase;

  const isVoided = caseData?.status === CaseStatus.VOIDED;
  const isReturnedToComplainant =
    caseData?.status === CaseStatus.RETURNED_TO_COMPLAINANT;
  const isPrimaryComplainant =
    user && caseData?.complainants?.some((c) => c.user === user.id && c.is_primary);
  const showResubmit = isReturnedToComplainant && isPrimaryComplainant && !isVoided;
  const showCadetReview =
    isCadet && caseData?.status === CaseStatus.CADET_REVIEW;
  const showOfficerReview =
    isOfficer && caseData?.status === CaseStatus.OFFICER_REVIEW;

  useEffect(() => {
    if (!id) return;
    getCaseDetail(parseInt(id, 10))
      .then(setCaseData)
      .catch(() => setCaseData(null))
      .finally(() => setIsLoading(false));
  }, [id]);

  const refreshCase = () => {
    if (!id) return;
    getCaseDetail(parseInt(id, 10)).then(setCaseData);
  };

  const handleCadetApprove = async () => {
    if (!id) return;
    setActionLoading(true);
    try {
      const updated = await cadetReview(parseInt(id, 10), {
        decision: 'approve',
      });
      setCaseData(updated);
    } catch (err) {
      const axiosError = err as { response?: { data?: { detail?: string } } };
      setError(axiosError.response?.data?.detail ?? 'خطا در تأیید.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleCadetReject = async (message: string) => {
    if (!id) return;
    setActionLoading(true);
    try {
      const updated = await cadetReview(parseInt(id, 10), {
        decision: 'reject',
        message,
      });
      setCaseData(updated);
    } catch (err) {
      const axiosError = err as { response?: { data?: { detail?: string } } };
      setError(axiosError.response?.data?.detail ?? 'خطا در رد.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleOfficerApprove = async () => {
    if (!id) return;
    setActionLoading(true);
    try {
      const updated = await officerReview(parseInt(id, 10), {
        decision: 'approve',
      });
      setCaseData(updated);
    } catch (err) {
      const axiosError = err as { response?: { data?: { detail?: string } } };
      setError(axiosError.response?.data?.detail ?? 'خطا در تأیید.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleOfficerReject = async (message: string) => {
    if (!id) return;
    setActionLoading(true);
    try {
      const updated = await officerReview(parseInt(id, 10), {
        decision: 'reject',
        message,
      });
      setCaseData(updated);
    } catch (err) {
      const axiosError = err as { response?: { data?: { detail?: string } } };
      setError(axiosError.response?.data?.detail ?? 'خطا در رد.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleComplainantReview = async (
    complainantId: number,
    decision: 'approve' | 'reject'
  ) => {
    if (!id) return;
    setActionLoading(true);
    try {
      await reviewComplainant(parseInt(id, 10), complainantId, { decision });
      refreshCase();
    } catch {
      setError('خطا در بررسی شاکی.');
    } finally {
      setActionLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
      </div>
    );
  }

  if (!caseData) {
    return (
      <div className="text-center">
        <p className="text-slate-500">پرونده یافت نشد.</p>
        <Button
          variant="ghost"
          className="mt-4"
          onClick={() => navigate('/cases')}
        >
          بازگشت به لیست
        </Button>
      </div>
    );
  }

  const latestRejectionMessage =
    caseData.status_logs?.find(
      (l) =>
        l.to_status === CaseStatus.RETURNED_TO_COMPLAINANT ||
        l.to_status === CaseStatus.RETURNED_TO_CADET
    )?.message ?? null;

  return (
    <div className="space-y-6">
      <div className="flex flex-row-reverse items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-100">{caseData.title}</h1>
        <StatusBadge
          status={caseData.status}
          displayText={caseData.status_display}
        />
      </div>

      {isVoided && (
        <div className="rounded-lg border border-red-500/50 bg-red-500/20 p-4 text-right text-red-200">
          {VOIDED_MESSAGE}
        </div>
      )}

      {error && (
        <div className="rounded-lg bg-red-500/20 p-4 text-right text-red-400">
          {error}
        </div>
      )}

      {isReturnedToComplainant && latestRejectionMessage && (
        <Card title="پیام برگشت از کارآموز">
          <p className="text-right text-slate-300">{latestRejectionMessage}</p>
        </Card>
      )}

      {showResubmit && (
        <CaseResubmitSection
          caseData={caseData}
          onResubmit={refreshCase}
          isLoading={actionLoading}
          setLoading={setActionLoading}
          setError={setError}
        />
      )}

      <Card title="اطلاعات پرونده">
        <div className="space-y-2 text-right">
          <p>
            <span className="text-slate-500">سطح جرم:</span>{' '}
            {caseData.crime_level_display}
          </p>
          <p>
            <span className="text-slate-500">تعداد رد:</span>{' '}
            {caseData.rejection_count}
          </p>
          {caseData.location && (
            <p>
              <span className="text-slate-500">محل:</span> {caseData.location}
            </p>
          )}
          <p className="mt-4 whitespace-pre-wrap text-slate-300">
            {caseData.description}
          </p>
        </div>
      </Card>

      {showCadetReview && (
        <ReviewActionPanel
          onApprove={handleCadetApprove}
          onReject={handleCadetReject}
          isLoading={actionLoading}
          approveLabel="ارسال به افسر"
          rejectLabel="برگشت به شاکی"
        />
      )}

      {showOfficerReview && (
        <ReviewActionPanel
          onApprove={handleOfficerApprove}
          onReject={handleOfficerReject}
          isLoading={actionLoading}
          approveLabel="تأیید نهایی"
          rejectLabel="برگشت به کارآموز"
        />
      )}

      {caseData.creation_type === 'complaint' && (
        <Card title="شاکیان">
          <ComplainantManager
            complainants={caseData.complainants}
            onReview={handleComplainantReview}
            canReview={isCadet}
            isLoading={actionLoading}
          />
        </Card>
      )}

      <Card title="تاریخچه وضعیت">
        <CaseTimeline statusLogs={caseData.status_logs ?? []} />
      </Card>
    </div>
  );
};
