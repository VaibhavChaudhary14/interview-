"use client";

import { useState, useRef, useCallback } from "react";

interface ExtractedData {
  skills: string[];
  technologies: string[];
  domains: string[];
  years_experience_estimate: number;
}

interface Props {
  onUploaded: (resumeId: string, extracted?: ExtractedData) => void;
}

export default function ResumeUpload({ onUploaded }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploaded, setUploaded] = useState(false);
  const [error, setError] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const [extracted, setExtracted] = useState<ExtractedData | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const validate = (f: File): string => {
    if (f.size > 5 * 1024 * 1024) return "File must be under 5 MB.";
    if (!f.name.match(/\.(pdf|txt)$/i)) return "Only PDF and .txt files are accepted.";
    return "";
  };

  const handleFileChange = (f: File) => {
    const err = validate(f);
    if (err) { setError(err); return; }
    setFile(f);
    setError("");
    setUploaded(false);
    setExtracted(null);
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) handleFileChange(f);
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFileChange(f);
  }, []);

  const handleDragOver = (e: React.DragEvent) => { e.preventDefault(); setDragOver(true); };
  const handleDragLeave = () => setDragOver(false);

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setError("");
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch("/api/v1/resume", { method: "POST", body: formData });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail?.message || err.message || "Upload failed");
      }
      const data = await res.json();
      setExtracted(data.extracted);
      setUploaded(true);
      onUploaded(data.resume_id, data.extracted);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setUploading(false);
    }
  };

  const zoneClass = [
    "drop-zone",
    dragOver ? "drag-over" : "",
    uploaded ? "file-selected" : "",
  ].filter(Boolean).join(" ");

  return (
    <div className="card animate-fade-in" style={{ animationDelay: "0.1s" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: "0.625rem", marginBottom: "1.25rem" }}>
        <div style={{
          width: 36, height: 36, borderRadius: 10,
          background: "rgba(99,102,241,0.15)",
          display: "flex", alignItems: "center", justifyContent: "center",
        }}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" stroke="#818cf8" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            <polyline points="14 2 14 8 20 8" stroke="#818cf8" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            <line x1="16" y1="13" x2="8" y2="13" stroke="#818cf8" strokeWidth="2" strokeLinecap="round" />
            <line x1="16" y1="17" x2="8" y2="17" stroke="#818cf8" strokeWidth="2" strokeLinecap="round" />
            <polyline points="10 9 9 9 8 9" stroke="#818cf8" strokeWidth="2" strokeLinecap="round" />
          </svg>
        </div>
        <div>
          <h2 style={{ fontSize: "1rem", fontWeight: 700, color: "#e2e8f0" }}>Upload Resume</h2>
          <p style={{ fontSize: "0.75rem", color: "#64748b" }}>PDF or TXT · max 5 MB</p>
        </div>
        {uploaded && (
          <span className="badge badge-success" style={{ marginLeft: "auto" }}>
            ✓ Parsed
          </span>
        )}
      </div>

      {/* Drop Zone */}
      <div
        className={zoneClass}
        onClick={() => !uploaded && inputRef.current?.click()}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        style={{ cursor: uploaded ? "default" : "pointer" }}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.txt"
          onChange={handleInputChange}
          style={{ display: "none" }}
          id="resume-file-input"
        />

        {uploaded && file ? (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "0.5rem" }}>
            <div style={{
              width: 48, height: 48, borderRadius: 12,
              background: "rgba(34,197,94,0.15)",
              display: "flex", alignItems: "center", justifyContent: "center",
            }}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                <path d="M20 6L9 17l-5-5" stroke="#4ade80" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <p style={{ fontSize: "0.9375rem", fontWeight: 600, color: "#86efac" }}>{file.name}</p>
            <p style={{ fontSize: "0.75rem", color: "#64748b" }}>
              {(file.size / 1024).toFixed(1)} KB · successfully parsed
            </p>
            <button
              onClick={(e) => { e.stopPropagation(); setFile(null); setUploaded(false); setExtracted(null); }}
              className="btn-secondary"
              style={{ marginTop: "0.5rem", width: "auto", padding: "0.375rem 1rem", fontSize: "0.8125rem" }}
            >
              Change file
            </button>
          </div>
        ) : file ? (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "0.5rem" }}>
            <div style={{
              width: 48, height: 48, borderRadius: 12,
              background: "rgba(99,102,241,0.15)",
              display: "flex", alignItems: "center", justifyContent: "center",
            }}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" stroke="#818cf8" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                <polyline points="14 2 14 8 20 8" stroke="#818cf8" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <p style={{ fontSize: "0.9375rem", fontWeight: 600, color: "#e2e8f0" }}>{file.name}</p>
            <p style={{ fontSize: "0.75rem", color: "#64748b" }}>{(file.size / 1024).toFixed(1)} KB</p>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "0.75rem" }}>
            <div style={{
              width: 56, height: 56, borderRadius: 16,
              background: "rgba(99,102,241,0.1)",
              display: "flex", alignItems: "center", justifyContent: "center",
            }}>
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
                <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" stroke="#6366f1" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                <polyline points="17 8 12 3 7 8" stroke="#6366f1" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                <line x1="12" y1="3" x2="12" y2="15" stroke="#6366f1" strokeWidth="2" strokeLinecap="round" />
              </svg>
            </div>
            <div>
              <p style={{ fontSize: "0.9375rem", fontWeight: 600, color: "#c7d2fe" }}>
                Drop your resume here
              </p>
              <p style={{ fontSize: "0.8125rem", color: "#64748b", marginTop: "0.25rem" }}>
                or click to browse · PDF or TXT
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="alert-error" style={{ marginTop: "0.75rem" }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" style={{ flexShrink: 0, marginTop: 1 }}>
            <circle cx="12" cy="12" r="10" stroke="#f87171" strokeWidth="2" />
            <line x1="12" y1="8" x2="12" y2="12" stroke="#f87171" strokeWidth="2" strokeLinecap="round" />
            <line x1="12" y1="16" x2="12.01" y2="16" stroke="#f87171" strokeWidth="2" strokeLinecap="round" />
          </svg>
          {error}
        </div>
      )}

      {/* Upload button */}
      {file && !uploaded && (
        <button
          id="upload-parse-btn"
          onClick={handleUpload}
          disabled={uploading}
          className="btn-primary"
          style={{ marginTop: "1rem" }}
        >
          {uploading ? (
            <><span className="spinner" style={{ width: 16, height: 16 }} /> Parsing resume...</>
          ) : (
            <>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                <polyline points="17 8 12 3 7 8" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                <line x1="12" y1="3" x2="12" y2="15" stroke="white" strokeWidth="2" strokeLinecap="round" />
              </svg>
              Upload &amp; Parse Resume
            </>
          )}
        </button>
      )}

      {/* Extracted skills preview */}
      {extracted && (
        <div className="animate-fade-in-scale" style={{ marginTop: "1.25rem" }}>
          <p style={{ fontSize: "0.75rem", fontWeight: 600, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.625rem" }}>
            Extracted Signals
          </p>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.375rem", marginBottom: "0.625rem" }}>
            {extracted.skills.slice(0, 12).map((s) => (
              <span key={s} className="skill-chip">{s}</span>
            ))}
            {extracted.technologies.slice(0, 6).map((t) => (
              <span key={t} className="badge badge-accent" style={{ fontSize: "0.7rem" }}>{t}</span>
            ))}
          </div>
          {extracted.years_experience_estimate > 0 && (
            <p style={{ fontSize: "0.8125rem", color: "#94a3b8" }}>
              ~{extracted.years_experience_estimate} years experience estimated
            </p>
          )}
        </div>
      )}
    </div>
  );
}
