# Master Task List — AI Interview Practice Platform
### Self-Prep First → Agency Mode → Scale
*Check off items as completed. Phases are mostly sequential; parallel tracks are marked.*

---

## PHASE 0 — Foundation (already built ✅)

- [x] FastAPI + PostgreSQL + ChromaDB backend skeleton
- [x] Next.js 14 frontend skeleton
- [x] Resume upload + parsing (pdfplumber, skill/tech/domain extraction)
- [x] Session state machine (CREATED → PROCESSING_RESUME → CONTEXT_BUILT → RETRIEVING → IN_PROGRESS → COMPLETED → REPORT_READY)
- [x] RAG pipeline: ingestion, chunking, embeddings (all-MiniLM-L6-v2), ChromaDB retrieval
- [x] LLM provider chain (Groq → Gemini → OpenAI → template fallback)
- [x] Question generation with JSON output + retry logic
- [x] Report builder (transcript, topics covered, insights)
- [x] Docker Compose deployment (db, backend, frontend)
- [x] Consent & audio recording infrastructure
  - [x] `Consent`, `Recording`, `AuditLog`, `ConsentPolicyVersion` models
  - [x] Immutable, versioned, server-side consent text + hash
  - [x] `AudioService`: upload, presigned URLs, right-to-erasure, retention purge
  - [x] Mode-aware retention (self_prep 30 days / agency 365 days, overridable)
  - [x] `ConsentModal.tsx`, `useAnswerInput.ts`, `RecordingPlayback.tsx` (frontend)
  - [x] Text-only fallback path (consent never blocks the interview)
- [x] Multi-provider STT/TTS with failover
  - [x] AssemblyAI, ElevenLabs, Sarvam AI provider implementations
  - [x] Failover chains (STT: AssemblyAI → ElevenLabs → Sarvam → mock; TTS: ElevenLabs → Sarvam → mock)
  - [x] Provider usage tracking (`provider_usage` table) + free-tier threshold alerts
  - [x] Dual-path async transcription (15s sync poll + AssemblyAI webhook fallback)
  - [x] Transcript status polling endpoint
- [x] Hybrid role classifier (Phase 2)
  - [x] `role_families` table + seed data (SWE, AI/ML, PM, Design, Sales)
  - [x] Keyword matching (fast path) + LLM fallback (flexible path)
  - [x] No-KB fallback prompt template for unmatched/KB-less families
  - [x] Classification metadata persisted on session (`matched_family_id`, `method`, `confidence`)

### ✅ Phase 0 cleanup — before moving forward, close these open items
- [x] Fix `answer_id` vs `question_id` ambiguity in audio upload route (confirm FK integrity, rename if needed)
- [x] Verify TTS cost tracking uses character count, not duration (ElevenLabs prices per-character)
- [x] Verify `consent_policy_versions` records are genuinely append-only (code review / DB constraint, not just convention)
- [x] Confirm audit log assertions actually check row creation, not just absence of errors
- [x] Run full browser QA matrix (see Phase 1 QA section below) — prior verification only tested the easy path

---

## PHASE 1 — Self-Prep MVP Completion (2–3 weeks) ✅

### 1.1 Database & schema ✅
- [x] Add `sessions.difficulty` (enum: `beginner`, `intermediate`, `advanced`)
- [x] Add `sessions.matched_family_id` indexing for browse-page queries
- [x] Confirm `sessions.resume_id` nullable (resume optional for self-prep)
- [x] Add `answers.transcript_text`, `answers.transcript_provider` (if not already present)

### 1.2 Backend ✅
- [x] Free-text role input accepted on session creation (already scaffolded — verify end-to-end)
- [x] Difficulty parameter threaded into `QuestionGeneratorService` prompt (reuse existing years-of-experience branching logic, make explicit override)
- [x] `GET /role-families` endpoint — returns list of seeded families + difficulty options, for the browse grid
- [x] Voice-activity-detection (VAD) auto-stop on recording (silence timeout ~2s) — backend accepts shorter/auto-terminated clips gracefully

### 1.3 Frontend ✅
- [x] Home page (`/`): free-text role input + optional resume upload + difficulty selector
- [x] `/browse` page: grid of role families × 3 difficulty levels, links into session creation (styled after edesy.in's browse-by-technology layout)
- [x] Interview page: Consent → question loop → audio/text answer → submit (already scaffolded — verify integration)
- [x] VAD-based auto-stop in `useAnswerInput.ts` (stop recording after N seconds of silence, no manual click required)
- [x] Summary page: transcript + placeholder delivery metrics cards

### 1.4 Delivery metrics (Phase 3 from earlier roadmap — now folded into Phase 1) ✅
- [x] `answer_metrics` table: `wpm`, `pause_count`, `avg_pause_duration`, `filler_word_count`, `clarity_score`
- [x] `AudioMetricsJob`: runs after transcription completes
  - [x] WPM calculation (word count ÷ audio duration)
  - [x] Pause detection (librosa or equivalent — silence gaps > 0.5s)
  - [x] Filler word regex detection (um, uh, like, you know, basically)
  - [x] (Optional, later) Whisper/AssemblyAI word-confidence-based clarity score
- [x] Summary page: "Delivery insights" card rendering the above metrics with plain-language framing (e.g. "ideal WPM: 120–160")

### 1.5 QA — full test matrix (do NOT skip; prior verification only covered one branch) ✅
- [x] Keyword-match role (e.g. "Backend Engineer") × text-only × full 8-question completion → report
- [x] Keyword-match role × voice-allowed × real STT transcription → report
- [x] LLM-fallback role (e.g. "Growth Marketer") × text-only → verify `classification_method == "llm"`, sensible questions
- [x] Unclassified role (e.g. "Ayurvedic Practitioner") × text-only → verify no-KB fallback prompt fires, no errors
- [x] Voice path: mic permission denied mid-session → graceful fallback to text, no stuck UI
- [x] Delivery metrics render correctly for a fast talker, a slow talker, and a filler-word-heavy answer
- [x] Candidate-initiated recording deletion (right-to-erasure) removes S3 object + DB row + invalidates presigned URL
- [x] Consent decline → interview still completes fully, report still generates

### ✅ Phase 1 exit criteria
- [x] All QA matrix items pass
- [x] Free self-prep flow works end-to-end with zero required signup friction (optional resume, no forced account creation for first session)
- [x] Provider usage dashboard shows real call counts across all 3 STT/TTS providers

---

## PHASE 2 — Self-Prep Beta Launch (1–2 weeks)

### 2.1 Pre-launch polish
- [x] Landing page copy + design pass (take structural cues from edesy.in: clear feature grid, technology/role browse, instant feedback framing — NOT Parakeet's real-time/undetectable positioning)
- [x] Basic analytics: session started, session completed, drop-off point tracking
- [x] In-app feedback prompt: "Was this question realistic? Was the delivery feedback useful?" (1–5 stars + optional text)
- [x] Error monitoring (Sentry or equivalent) wired into backend + frontend
- [x] Legal: Scaffolding created at `/legal/retention-policy` (page exists, no 404, copy accurately represents current system data/deletion behaviors)
- [ ] Legal: Review policy page copy with real legal input prior to public beta launch

### 2.2 Beta rollout
- [ ] Recruit 50–100 beta users (personal network, relevant subreddits/communities, LinkedIn)
- [ ] Track per-session: completion rate, classification accuracy (manual review of 20 samples), STT accuracy (spot-check 10 transcripts), metric usefulness (survey responses)
- [ ] Weekly review of provider usage/cost vs free tier limits — decide when to move to paid tiers
- [ ] Collect a running list of role titles users typed that hit "unclassified" — this becomes your Phase 3 prioritization list for new KB families

### 🔲 Phase 2 exit criteria
- [ ] ≥60% session completion rate (started → reached summary page)
- [ ] Classification review shows reasonable accuracy (no systematic misroutes for common tech roles)
- [ ] Delivery metrics rated useful by a majority of surveyed users
- [ ] No unresolved P0/P1 bugs from beta feedback

---

## PHASE 3 — Iterate & Expand Role Coverage (ongoing, 2–4 weeks per cycle)

- [ ] Prioritize 2–3 new role families based on beta "unclassified" list + user demand
- [ ] For each new family: decide RAG-backed (source + ingest real content) vs LLM-only (just add to seed list)
- [ ] Tune delivery metrics thresholds per role type if beta feedback shows WPM/pause norms vary by role (e.g. technical vs sales pacing expectations)
- [ ] A/B test question style variations if retention data suggests specific phrasing patterns work better
- [ ] Add difficulty-level content depth checks (are "advanced" questions actually harder, or just longer?)

---

## PHASE 4 — Monetization (self-prep) (2–3 weeks)

- [ ] Define free tier limits (e.g. 3 free sessions/month, or N questions/month)
- [ ] Payment integration (Stripe recommended — subscription + one-time credit packs)
- [ ] Pricing tiers: Free / Pro (unlimited sessions, all role families, priority STT) / decide if a one-time "resume review + mock interview bundle" makes sense
- [ ] Usage gating logic (block session creation past free tier limit, prompt upgrade)
- [ ] Referral or credit system (optional — inspired by structures like Parakeet's, but built independently, no shared code/positioning)
- [ ] Billing dashboard (view usage, manage subscription, invoices)

### 🔲 Phase 4 exit criteria
- [ ] At least 1% of beta users convert to paid when gating goes live (early signal, not a hard bar)
- [ ] Billing edge cases tested (failed payment, downgrade mid-cycle, refund request)

---

## PHASE 5 — Recruiting Agency Mode Reactivation (3–4 weeks)

*(Your `sessions.mode` field and agency-specific retention/consent logic already exist from Phase 0 — this phase is about building the actual agency-facing product surface.)*

- [ ] Agency account/org model — multi-user, seat-based, separate from self-prep candidate accounts
- [ ] Agency dashboard: create screening links, view candidate sessions, review reports
- [ ] `RecordingPlayback.tsx` integration into agency dashboard (already built — wire up to real agency auth)
- [ ] White-label branding options (logo, colors) per agency org
- [ ] Bulk candidate invite flow (CSV upload or ATS integration stub)
- [ ] Agency-specific retention override UI (contractually agreed windows, per earlier compliance design)
- [ ] DPA / subprocessor agreements finalized with AssemblyAI, ElevenLabs, Sarvam (or whichever providers are in production use by then)
- [ ] Export report as PDF/branded document for agency's own client delivery

### 🔲 Phase 5 exit criteria
- [ ] At least 1 pilot agency running real candidate screenings
- [ ] Agency-specific compliance requirements (retention, DPA, audit access logs) reviewed and signed off

---

## PHASE 6 — Compliance Hardening (parallel with Phase 5, ongoing)

- [ ] SOC 2 Type II process kicked off (once agency revenue justifies it — not before)
- [ ] Customer-managed encryption keys (KMS) as enterprise upsell option
- [ ] Formal data processing agreements with all active third-party providers
- [ ] Access audit trail review — confirm every presigned URL generation/playback is logged per tenant
- [ ] Data minimization review — confirm raw audio retention window is genuinely as short as viable, transcript-only default where audio isn't specifically needed

---

## PHASE 7 — Scale & Polish (ongoing)

- [ ] Move off free-tier STT/TTS providers to paid production tiers with SLAs
- [ ] Performance: async ingestion pipeline parallelization for new KB content (currently single-process, 5–15 min for 7 textbooks)
- [ ] Consider dedicated vector DB (Weaviate/Pinecone/Qdrant) if corpus grows past ~500k chunks
- [ ] Mobile-responsive polish / potential native app evaluation
- [ ] Internationalization (Sarvam already gives you a path into Indian-language markets — decide if/when to build this out)
- [ ] Ongoing: expand role family library based on demand signals from both self-prep and agency usage

---

## Running "Do Not Build" List
*(Explicit boundary, revisit only if circumstances genuinely change — not a backlog item)*
- ❌ Real-time, in-call assistance that feeds answers to a candidate during an actual live interview or exam
- ❌ Any "undetectable" / anti-proctoring / screen-share-evasion feature
- ❌ Anything designed to help a candidate misrepresent their real-time knowledge to an evaluator

---

## How to use this list
- Phases 0–2 are your critical path to a working, testable self-prep product — don't skip the QA matrix in 1.5, it's catching real bugs.
- Phases 3–4 can interleave once beta feedback starts coming in.
- Phase 5 (agency) should not start until self-prep has real usage data — you built the compliance plumbing early, which is good, but the product surface for agencies is a separate, later investment.
- Update this file directly as you complete items; treat unchecked items older than a few weeks as a signal to re-scope, not just a backlog.
