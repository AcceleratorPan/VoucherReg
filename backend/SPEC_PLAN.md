# SPEC_PLAN.md

## 1. Objective
Bootstrap a production-oriented FastAPI backend skeleton and collaboration-ready documentation for voucher image capture, first-page OCR metadata extraction, and final multi-page PDF generation with deterministic filename rules.

Primary output:
- ready-to-continue code structure
- explicit API/DB/architecture contracts
- MVP-constrained implementation plan

## 2. Scope
### In Scope (MVP)
- Create voucher task.
- Upload ordered page images through backend.
- Store page metadata and task state.
- Run OCR on first page only.
- Deterministically parse `subject`, `month`, `voucherNo`.
- Return review payload and filename preview.
- Accept user-confirmed fields and generate final PDF.
- Persist and return PDF URL/path.
- List tasks and fetch task detail.
- Provide mock-friendly interfaces for parallel frontend/backend work.

### Out of Scope (MVP)
- OpenCV perspective correction.
- Direct COS upload from mini program.
- LLM-first extraction.
- Batch export.
- Complex permissions and archive search.
- Advanced retry/workflow orchestration.

## 3. Assumptions
- Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic.
- Storage starts as local or backend-managed object storage abstraction.
- OCR provider abstraction supports mock and local Chinese OCR implementation (RapidOCR).
- Frontend performs manual confirmation before final PDF generation.
- API external fields are camelCase.

## 4. Architecture Plan
### Layered modules
- API layer (`app/api`): request validation and response mapping.
- Domain/service layer (`app/services`): task workflow, parsing, OCR orchestration, PDF orchestration.
- Persistence layer (`app/models`, `app/db`): SQLAlchemy models, sessions, migrations.
- Integration layer: storage and OCR adapters.
- Utility layer (`app/utils`): normalization, filename sanitization, error helpers.

### Core contracts
- `StorageService` -> save/read images and generated PDFs.
- `OCRService` -> OCR text extraction from first page image.
- `ParsingService` -> deterministic metadata extraction and confidence.
- `PDFService` -> ordered page-to-PDF generation and persistence.

## 5. Data Design Plan
### `voucher_task`
- Identity and ownership: `id`, `user_id`.
- Extracted fields: `subject`, `voucher_month`, `voucher_no`.
- Output: `file_name`, `pdf_url`.
- Runtime: `status`, `page_count`, `raw_ocr_text`, `confidence`.
- Audit: `created_at`, `updated_at`.

### `voucher_page`
- Identity: `id`, `task_id`.
- Ordering and role: `page_index`, `is_first_page`.
- File refs: `image_url`, `thumb_url`.
- Metadata: `width`, `height`.
- Audit: `created_at`, `updated_at`.

### Optional `voucher_recognition_log`
- Request/response and parsing snapshots for troubleshooting.

## 6. API Plan
Endpoints:
1. `POST /voucher-tasks`
2. `POST /voucher-tasks/{task_id}/pages`
3. `POST /voucher-tasks/{task_id}/finish-upload`
4. `POST /voucher-tasks/{task_id}/recognize`
5. `POST /voucher-tasks/{task_id}/confirm-generate`
6. `GET /voucher-tasks`
7. `GET /voucher-tasks/{task_id}`
8. `GET /health`

Standard error envelope:
```json
{
  "code": "OCR_FAILED",
  "message": "OCR recognition failed",
  "detail": {}
}
```

Recognize response target:
```json
{
  "taskId": "vt_123",
  "subject": "海南百迈科医疗科技股份有限公司",
  "month": "2022-07",
  "voucherNo": "记470",
  "fileNamePreview": "海南百迈科医疗科技股份有限公司-2022-07-记470.pdf",
  "confidence": 0.93,
  "needsUserReview": true
}
```

## 7. Status Flow Plan
States:
- `draft`
- `uploaded`
- `recognized`
- `confirmed`
- `pdf_generated`
- `failed`

Allowed transitions:
- `draft -> uploaded`
- `uploaded -> recognized`
- `recognized -> confirmed`
- `confirmed -> pdf_generated`
- any non-terminal state -> `failed`

Guard conditions:
- `finish-upload`: at least 1 page exists.
- `recognize`: first page exists and task in `uploaded`.
- `confirm-generate`: task in `recognized` with confirmation payload.

## 8. Implementation Milestones
### Milestone 1: Repository Bootstrap
Deliverables:
- Project folder layout.
- FastAPI app startup (`main.py`), router registration, `/health`.
- Base settings and environment loading.
- Base exception + error envelope scaffolding.

Exit criteria:
- App starts and health endpoint responds.

### Milestone 2: Persistence Foundation
Deliverables:
- SQLAlchemy models for `voucher_task`, `voucher_page`.
- DB session/engine setup.
- Alembic init + first migration.
- Repository helpers for CRUD skeleton.

Exit criteria:
- Migration applies cleanly and task/page records persist.

### Milestone 3: Upload Workflow
Deliverables:
- `POST /voucher-tasks`.
- `POST /voucher-tasks/{task_id}/pages` with image validation and ordering.
- `POST /voucher-tasks/{task_id}/finish-upload`.
- Local storage adapter implemented.

Exit criteria:
- End-to-end upload flow reaches `uploaded` state.

### Milestone 4: OCR + Parsing
Deliverables:
- OCR interface and mock implementation.
- RapidOCR adapter implementation (local, no cloud dependency).
- Parsing service for subject/month/voucherNo normalization.
- Recognize endpoint returning preview and confidence.

Exit criteria:
- `recognize` returns deterministic fields from sample OCR text.

### Milestone 5: Confirm + PDF Generation
Deliverables:
- Confirm endpoint accepting user-edited fields.
- PDF service generates one PDF page per image in page order.
- Filename sanitization and canonical output naming.
- Save PDF and update task to `pdf_generated`.

Exit criteria:
- Confirm flow returns final `pdfUrl` and stored `fileName`.

### Milestone 6: Read APIs + Documentation Finalization
Deliverables:
- List/detail endpoints.
- README, architecture, API, DB schema, scope, task board docs.
- `.env.example` and local run instructions.

Exit criteria:
- Frontend developer can integrate against docs without backend source deep-dive.

### Milestone 7: Test Skeleton
Deliverables:
- Unit tests for parsing + filename utils.
- Integration test skeleton for full workflow.
- Mock OCR/storage fixtures for deterministic tests.

Exit criteria:
- Test suite runs and validates critical happy paths.

## 9. Documentation Deliverables Checklist
- `README.md`
- `MVP_SCOPE.md`
- `ARCHITECTURE.md`
- `API_CONTRACT.md`
- `DB_SCHEMA.md`
- `TASK_BOARD.md`
- `.env.example`

Quality gates:
- explicit heading structure
- concrete fields and examples
- clear state machine
- explicit in/out-of-scope boundaries
- endpoint request/response and failures

## 10. Risks and Mitigations
- OCR variability risk: mitigate with deterministic parser fallbacks and user confirmation.
- Filename invalid characters: central sanitize utility with tests.
- State inconsistency risk: enforce transition guards in service layer.
- Coupling to storage provider: use storage interface and adapters.
- Frontend/backend mismatch: enforce API contract docs early and keep camelCase external schema.

## 11. Acceptance Criteria
- Required endpoints exist with defined schemas and error envelopes.
- Status transitions follow documented machine.
- First-page-only OCR policy enforced by implementation.
- Confirmed metadata controls final filename.
- PDF generation preserves upload order.
- Docs are complete enough for parallel frontend integration.
- Unit + integration test scaffolding included.

## 12. Immediate Next Build Order
1. Create base project tree and dependency manifest.
2. Implement FastAPI app shell + health + config.
3. Add DB models and migration.
4. Implement task/page upload pipeline.
5. Add OCR/parsing + recognize endpoint.
6. Add confirm-generate + PDF creation.
7. Add list/detail APIs.
8. Finalize docs and tests.
