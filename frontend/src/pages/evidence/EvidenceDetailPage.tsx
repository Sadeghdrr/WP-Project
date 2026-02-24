/**
 * EvidenceDetailPage — full evidence detail with coroner verification,
 * file upload, and chain-of-custody log.
 *
 * Corrected:
 * - Custody log fetched separately via chainOfCustody() (not embedded in detail)
 * - Added EvidenceFileUpload for attaching files (§4.3.1 / §4.3.2)
 * - Passes custodyLog prop to EvidenceCard
 */
import { useState, type ChangeEvent, type FormEvent } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query';
import { Button } from '@/components/ui/Button';
import { Skeleton } from '@/components/ui/Skeleton';
import { Alert } from '@/components/ui/Alert';
import { Select } from '@/components/ui/Select';
import { Input } from '@/components/ui/Input';
import { EvidenceCard } from '@/features/evidence/EvidenceCard';
import { CoronerVerificationForm } from '@/features/evidence/CoronerVerificationForm';
import { PermissionGate } from '@/components/guards/PermissionGate';
import { evidenceApi } from '@/services/api/evidence.api';
import { EvidencePerms } from '@/config/permissions';
import { extractErrorMessage } from '@/utils/errors';
import { useToast } from '@/context/ToastContext';

const FILE_TYPE_OPTIONS = [
  { value: 'image', label: 'Image' },
  { value: 'video', label: 'Video' },
  { value: 'audio', label: 'Audio' },
  { value: 'document', label: 'Document' },
];

export function EvidenceDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const toast = useToast();
  const evidenceId = Number(id);

  /* ── Evidence detail query ──────────────────────────────────── */
  const { data, isLoading, error } = useQuery({
    queryKey: ['evidence', evidenceId],
    queryFn: () => evidenceApi.detail(evidenceId),
    enabled: !Number.isNaN(evidenceId),
  });

  /* ── Chain of custody query ─────────────────────────────────── */
  const { data: custodyLog } = useQuery({
    queryKey: ['evidence', evidenceId, 'custody'],
    queryFn: () => evidenceApi.chainOfCustody(evidenceId),
    enabled: !Number.isNaN(evidenceId),
  });

  /* ── File upload state ──────────────────────────────────────── */
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileType, setFileType] = useState('image');
  const [caption, setCaption] = useState('');
  const [uploadError, setUploadError] = useState('');

  const uploadMutation = useMutation({
    mutationFn: (formData: FormData) => evidenceApi.uploadFile(evidenceId, formData),
    onSuccess: () => {
      setSelectedFile(null);
      setCaption('');
      toast.success('File uploaded successfully');
      queryClient.invalidateQueries({ queryKey: ['evidence', evidenceId] });
    },
    onError: (err) => setUploadError(extractErrorMessage(err)),
  });

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    setSelectedFile(e.target.files?.[0] ?? null);
  };

  const handleUpload = (e: FormEvent) => {
    e.preventDefault();
    if (!selectedFile) { setUploadError('Please select a file'); return; }
    setUploadError('');
    const fd = new FormData();
    fd.append('file', selectedFile);
    fd.append('file_type', fileType);
    fd.append('caption', caption.trim());
    uploadMutation.mutate(fd);
  };

  const handleVerified = () => {
    queryClient.invalidateQueries({ queryKey: ['evidence', evidenceId] });
  };

  /* ── Render ─────────────────────────────────────────────────── */
  if (isLoading) return <Skeleton height={500} />;
  if (error || !data) {
    return (
      <div className="page-evidence-detail">
        <Alert type="error">Failed to load evidence #{id}.</Alert>
        <Button variant="secondary" onClick={() => navigate('/evidence')}>Back</Button>
      </div>
    );
  }

  return (
    <div className="page-evidence-detail">
      <div className="page-header">
        <h1 className="page-header__title">Evidence #{data.id}</h1>
        <Button variant="secondary" onClick={() => navigate('/evidence')}>Back</Button>
      </div>

      <EvidenceCard evidence={data} custodyLog={custodyLog} />

      {/* File upload section — any evidence registrar can upload files */}
      <PermissionGate permissions={[EvidencePerms.ADD_EVIDENCE]}>
        <form className="evidence-upload" onSubmit={handleUpload}>
          <h3>Upload File</h3>
          {uploadError && <Alert type="error" onClose={() => setUploadError('')}>{uploadError}</Alert>}
          <div className="evidence-upload__row">
            <input type="file" onChange={handleFileChange} />
            <Select label="File Type" options={FILE_TYPE_OPTIONS} value={fileType} onChange={(e) => setFileType(e.target.value)} />
            <Input label="Caption" value={caption} onChange={(e) => setCaption(e.target.value)} placeholder="Optional caption…" />
          </div>
          <Button type="submit" variant="secondary" loading={uploadMutation.isPending}>
            Upload
          </Button>
        </form>
      </PermissionGate>

      {/* Coroner verification for biological evidence */}
      {data.evidence_type === 'biological' && !data.is_verified && (
        <PermissionGate permissions={[EvidencePerms.CAN_VERIFY_EVIDENCE]}>
          <CoronerVerificationForm evidenceId={evidenceId} onVerified={handleVerified} />
        </PermissionGate>
      )}
    </div>
  );
}
