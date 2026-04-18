import React, { useCallback, useRef, useState } from 'react';
import DashboardLayout from '@/components/DashboardLayout';
import { ACCEPTED_FILE_EXTENSIONS, MAX_UPLOAD_SIZE_BYTES } from '@/utils/constants';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type UploadStatus = 'idle' | 'uploading' | 'success' | 'error';

// ---------------------------------------------------------------------------
// Upload page
// ---------------------------------------------------------------------------

export default function UploadPage() {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadStatus, setUploadStatus] = useState<UploadStatus>('idle');
  const [errorMessage, setErrorMessage] = useState<string>('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Validate the chosen file
  const validateFile = (file: File): string | null => {
    const ext = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!ACCEPTED_FILE_EXTENSIONS.includes(ext as never)) {
      return `Unsupported file type "${ext}". Please upload a source code file.`;
    }
    if (file.size > MAX_UPLOAD_SIZE_BYTES) {
      return `File is too large (${(file.size / 1024 / 1024).toFixed(1)} MB). Maximum allowed size is 10 MB.`;
    }
    return null;
  };

  const handleFile = (file: File) => {
    const validationError = validateFile(file);
    if (validationError) {
      setErrorMessage(validationError);
      setSelectedFile(null);
      return;
    }
    setErrorMessage('');
    setSelectedFile(file);
    setUploadStatus('idle');
  };

  // Drag-and-drop handlers
  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(e.type === 'dragenter' || e.type === 'dragover');
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };

  // Simulate an upload (replace with real API call once backend is ready)
  const handleUpload = async () => {
    if (!selectedFile) return;

    setUploadStatus('uploading');
    try {
      // TODO: replace with real API call
      // const result = await uploadCode(selectedFile);
      await new Promise((resolve) => setTimeout(resolve, 1500)); // simulate network
      setUploadStatus('success');
    } catch {
      setUploadStatus('error');
      setErrorMessage('Upload failed. Please try again.');
    }
  };

  const handleReset = () => {
    setSelectedFile(null);
    setUploadStatus('idle');
    setErrorMessage('');
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  return (
    <DashboardLayout pageTitle="Upload Code">
      <div className="max-w-2xl mx-auto space-y-6">
        {/* Page heading */}
        <div>
          <h2 className="text-xl font-semibold text-gray-900">Upload Code</h2>
          <p className="text-sm text-gray-500 mt-1">
            Upload a source file to run an AI-powered security analysis.
          </p>
        </div>

        {/* Drop zone */}
        <div
          onDragEnter={handleDrag}
          onDragOver={handleDrag}
          onDragLeave={handleDrag}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`relative flex flex-col items-center justify-center gap-4 rounded-xl border-2 border-dashed p-10 cursor-pointer transition-colors duration-200 ${
            dragActive
              ? 'border-blue-500 bg-blue-50'
              : 'border-gray-300 bg-white hover:border-blue-400 hover:bg-gray-50'
          }`}
          aria-label="File upload drop zone"
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') fileInputRef.current?.click();
          }}
        >
          <input
            ref={fileInputRef}
            type="file"
            className="sr-only"
            accept={ACCEPTED_FILE_EXTENSIONS.join(',')}
            onChange={handleInputChange}
            aria-label="Select a code file to upload"
          />

          <div className="flex items-center justify-center w-16 h-16 rounded-full bg-blue-100">
            <svg
              className="w-8 h-8 text-blue-600"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.6}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"
              />
            </svg>
          </div>

          <div className="text-center">
            <p className="text-sm font-medium text-gray-700">
              {dragActive ? 'Drop your file here' : 'Drag & drop your file here'}
            </p>
            <p className="text-xs text-gray-400 mt-1">
              or click to browse &mdash; max 10 MB
            </p>
          </div>

          <p className="text-xs text-gray-400">
            Supported: {ACCEPTED_FILE_EXTENSIONS.join(', ')}
          </p>
        </div>

        {/* Error message */}
        {errorMessage && (
          <div className="flex items-start gap-2 p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
            <svg className="w-4 h-4 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            {errorMessage}
          </div>
        )}

        {/* Selected file info */}
        {selectedFile && uploadStatus !== 'success' && (
          <div className="card flex items-center gap-4">
            <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-gray-100 flex-shrink-0">
              <svg className="w-5 h-5 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">
                {selectedFile.name}
              </p>
              <p className="text-xs text-gray-400">
                {(selectedFile.size / 1024).toFixed(1)} KB
              </p>
            </div>
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); handleReset(); }}
              className="text-gray-400 hover:text-gray-600 transition-colors"
              aria-label="Remove selected file"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        )}

        {/* Success state */}
        {uploadStatus === 'success' && (
          <div className="card flex flex-col items-center gap-3 text-center">
            <div className="flex items-center justify-center w-14 h-14 rounded-full bg-green-100">
              <svg className="w-7 h-7 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div>
              <p className="font-semibold text-gray-900">Upload successful!</p>
              <p className="text-sm text-gray-500 mt-0.5">
                Your file is being analyzed. Results will appear in Reports.
              </p>
            </div>
            <button type="button" onClick={handleReset} className="btn-secondary mt-1">
              Upload another file
            </button>
          </div>
        )}

        {/* Upload button */}
        {selectedFile && uploadStatus !== 'success' && (
          <button
            type="button"
            onClick={handleUpload}
            disabled={uploadStatus === 'uploading'}
            className="btn-primary w-full py-3"
          >
            {uploadStatus === 'uploading' ? (
              <span className="flex items-center gap-2">
                <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Uploading…
              </span>
            ) : (
              'Upload & Scan'
            )}
          </button>
        )}
      </div>
    </DashboardLayout>
  );
}
