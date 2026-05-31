with open('leasesight-ui/src/components/LeftPane.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

import_target = "import { AuditSkeleton } from './AuditSkeleton';"
content = content.replace(import_target, "import { AuditSkeleton } from './AuditSkeleton';\nimport { FileUploadStatus } from './FileUploadStatus';")

state_target = "  const [isUploading, setIsUploading] = useState(false);"
content = content.replace(state_target, "  const [isUploading, setIsUploading] = useState(false);\n  const [pipelineStatus, setPipelineStatus] = useState<string | null>(null);\n  const [pipelineError, setPipelineError] = useState<string | undefined>();")

upload_target = """  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setIsUploading(true);
    try {
      const res = await api.upload(file);
      const docsRes = await api.documents();
      setDocuments(docsRes.documents ?? []);
      onSelectDoc(res.file_name ?? '');
    } catch (error) {
      console.error('Upload failed:', error);
      showErrorToast(error, 'Upload Failed');
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };"""

new_upload = """  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setIsUploading(true);
    setPipelineStatus(null);
    setPipelineError(undefined);
    try {
      const res = await api.upload(file);
      const docsRes = await api.documents();
      setDocuments(docsRes.documents ?? []);
      onSelectDoc(res.file_name ?? '');

      if (res.live_evaluation?.status === 'QUEUED') {
        setPipelineStatus('QUEUED');
        const pollInterval = setInterval(async () => {
          try {
            const statusRes = await api.checkLiveEvaluation(res.file_name);
            setPipelineStatus(statusRes.status);
            
            if (statusRes.status === 'COMPLETED') {
              clearInterval(pollInterval);
              const auditData = await api.audit(res.file_name);
              onAuditComplete(auditData);
            } else if (statusRes.status === 'FAILED') {
              clearInterval(pollInterval);
              setPipelineError('Extraction failed.');
            }
          } catch (err) {
            clearInterval(pollInterval);
            setPipelineStatus('FAILED');
          }
        }, 3000);
      }
    } catch (error) {
      console.error('Upload failed:', error);
      showErrorToast(error, 'Upload Failed');
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };"""

content = content.replace(upload_target, new_upload)

jsx_target = """      </div>

      {/* Scrollable Results Area */}"""

new_jsx = """      </div>

      {/* File Upload Status */}
      {pipelineStatus && (
        <div className="px-4 pb-2">
          <FileUploadStatus status={pipelineStatus} error={pipelineError} />
        </div>
      )}

      {/* Scrollable Results Area */}"""

content = content.replace(jsx_target, new_jsx)

with open('leasesight-ui/src/components/LeftPane.tsx', 'w', encoding='utf-8') as f:
    f.write(content)
