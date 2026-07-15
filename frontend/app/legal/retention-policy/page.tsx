import Link from "next/link";

export default function LegalRetentionPolicyPage() {
  return (
    <div style={{ maxWidth: 760, margin: "2rem auto", padding: "0 1.25rem" }}>
      {/* Back button */}
      <Link
        href="/"
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: "0.375rem",
          fontSize: "0.875rem",
          color: "#6366f1",
          textDecoration: "none",
          marginBottom: "1.5rem",
          fontWeight: 500,
        }}
      >
        ← Back to Practice Home
      </Link>

      <h1 style={{ fontSize: "2rem", fontWeight: 800, color: "#f8fafc", marginBottom: "1.5rem", letterSpacing: "-0.02em" }}>
        Data Retention & Compliance Policy
      </h1>
      <p style={{ fontSize: "0.9375rem", color: "#94a3b8", lineHeight: 1.6, marginBottom: "2rem" }}>
        Last updated: July 2026 (Version 1.0)
      </p>

      <div style={{ display: "flex", flexDirection: "column", gap: "2rem" }}>
        {/* Section 1 */}
        <section>
          <h2 style={{ fontSize: "1.25rem", fontWeight: 700, color: "#e2e8f0", marginBottom: "0.75rem" }}>
            1. Consent and Voice Recording
          </h2>
          <p style={{ fontSize: "0.9375rem", color: "#94a3b8", lineHeight: 1.6 }}>
            Using voice features is entirely optional. When creating an interview session, candidates can explicitly consent to or decline audio recording. If declined, the platform falls back to text-only mode where answers are typed. Decline of voice consent never restricts access to the technical interview questions or report feedback.
          </p>
        </section>

        {/* Section 2 */}
        <section>
          <h2 style={{ fontSize: "1.25rem", fontWeight: 700, color: "#e2e8f0", marginBottom: "0.75rem" }}>
            2. Audio Data Retention Windows
          </h2>
          <p style={{ fontSize: "0.9375rem", color: "#94a3b8", lineHeight: 1.6, marginBottom: "0.75rem" }}>
            To minimize stored personal data, our platform enforces automated compliance routines:
          </p>
          <ul style={{ paddingLeft: "1.5rem", color: "#94a3b8", display: "flex", flexDirection: "column", gap: "0.5rem", fontSize: "0.9375rem", lineHeight: 1.6 }}>
            <li>
              <strong>Self-Prep Candidates:</strong> All audio recordings are automatically and permanently deleted <strong>30 days</strong> after upload.
            </li>
            <li>
              <strong>Agency Screening:</strong> Sessions initiated via organization links retain recording objects for <strong>365 days</strong> for recruitment evaluations, unless overridden by the organization's custom retention policies.
            </li>
          </ul>
        </section>

        {/* Section 3 */}
        <section>
          <h2 style={{ fontSize: "1.25rem", fontWeight: 700, color: "#e2e8f0", marginBottom: "0.75rem" }}>
            3. Right-to-Erasure (Immediate Candidate Deletion)
          </h2>
          <p style={{ fontSize: "0.9375rem", color: "#94a3b8", lineHeight: 1.6 }}>
            In compliance with global data privacy regulations (such as GDPR), candidates maintain full ownership of their voice data. At any time, you can view your mock interview summary page and click the <strong>Delete Recording</strong> icon. This triggers an immediate server-side deletion that unlinks the physical audio object from storage (S3 or local disk), nullifies the database reference, and renders playback URLs inactive.
          </p>
        </section>

        {/* Section 4 */}
        <section>
          <h2 style={{ fontSize: "1.25rem", fontWeight: 700, color: "#e2e8f0", marginBottom: "0.75rem" }}>
            4. Third-Party Sub-processors
          </h2>
          <p style={{ fontSize: "0.9375rem", color: "#94a3b8", lineHeight: 1.6 }}>
            Audio recordings are processed securely via encrypted channels using industry-leading providers:
          </p>
          <ul style={{ paddingLeft: "1.5rem", color: "#94a3b8", display: "flex", flexDirection: "column", gap: "0.5rem", fontSize: "0.9375rem", lineHeight: 1.6, marginTop: "0.5rem" }}>
            <li><strong>AssemblyAI:</strong> Used for transcribing audio to text.</li>
            <li><strong>ElevenLabs & Sarvam AI:</strong> Used to synthesize AI voice feedback.</li>
          </ul>
        </section>

        {/* Section 5 */}
        <section style={{ borderTop: "1px solid rgba(255,255,255,0.06)", paddingTop: "1.5rem" }}>
          <h2 style={{ fontSize: "1.1rem", fontWeight: 700, color: "#cbd5e1", marginBottom: "0.5rem" }}>
            Append-Only Auditing Policy
          </h2>
          <p style={{ fontSize: "0.875rem", color: "#64748b", lineHeight: 1.5 }}>
            Any consent updates or policy adjustments are stamped dynamically under immutable versions. Past agreements cannot be overridden or modified retroactively, ensuring a secure compliance trail for every user.
          </p>
        </section>
      </div>
    </div>
  );
}
