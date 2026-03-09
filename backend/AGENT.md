# AGENT.md

## Purpose
This document defines how an implementation agent should execute the FastAPI + WeChat Mini Program backend bootstrap described in `fastapi_wechat_codex_bootstrap_prompt.md`.

The target is a production-oriented MVP skeleton and collaboration-grade documentation, not a toy demo.

## Product Summary
- Domain: Accounting voucher capture and PDF generation.
- Frontend: WeChat Mini Program (separately implemented).
- Backend: FastAPI (core orchestration and business logic).
- OCR: RapidOCR (local Chinese OCR) via abstraction.
- Storage: Backend-mediated upload (MVP), pluggable for COS later.
- Output: One voucher task -> one named PDF.

## Non-Negotiable Constraints
1. FastAPI is the core backend.
2. Parse metadata from the first page only.
3. Primary extraction strategy is OCR + deterministic rules.
4. LLM is optional future fallback only.
5. Frontend must be able to review/confirm extracted fields before final PDF generation.
6. MVP favors reliability and cost control over premature optimization.
7. Public API fields use `camelCase`; Python internals use `snake_case`.

## Required Workflow
1. Create voucher task.
2. Upload ordered page images.
3. Finish upload.
4. Recognize metadata from first page.
5. Return extracted fields + confidence + filename preview + `needsUserReview`.
6. Accept user confirmation/corrections.
7. Generate final multi-page PDF.
8. Persist and return final PDF URL/path.
9. Provide list and detail views.

## Required Status Machine
- `draft` -> `uploaded` -> `recognized` -> `confirmed` -> `pdf_generated`
- Any stage may move to `failed` on terminal error.

Validation rules:
- `finish-upload` requires at least 1 page.
- `recognize` requires `uploaded`.
- `confirm-generate` requires recognized data and user confirmation payload.
- `pdf_generated` is immutable except read-only fetch/list operations.

## Required API Endpoints
- `POST /voucher-tasks`
- `POST /voucher-tasks/{task_id}/pages`
- `POST /voucher-tasks/{task_id}/finish-upload`
- `POST /voucher-tasks/{task_id}/recognize`
- `POST /voucher-tasks/{task_id}/confirm-generate`
- `GET /voucher-tasks`
- `GET /voucher-tasks/{task_id}`
- `GET /health`

All APIs must define:
- success schema
- error envelope: `{ "code": "...", "message": "...", "detail": {} }`
- status-code mapping for validation/runtime failures

## Required Data Entities
Minimum tables/models:
- `voucher_task`
- `voucher_page`

Optional:
- `voucher_recognition_log`

Mandatory `voucher_task` fields:
- `id`, `user_id`, `subject`, `voucher_month`, `voucher_no`, `file_name`, `pdf_url`, `status`, `page_count`, `raw_ocr_text`, `confidence`, `created_at`, `updated_at`

Mandatory `voucher_page` fields:
- `id`, `task_id`, `page_index`, `image_url`, `thumb_url`, `is_first_page`, `width`, `height`, `created_at`, `updated_at`

## Service Boundaries
Keep core business logic modular and mockable.

- `StorageService`
  - `LocalStorageService`
  - optional `COSStorageService` placeholder
- `OCRService`
  - `MockOCRService`
  - `RapidOCRService`
- `ParsingService`
  - normalize OCR text
  - extract subject/month/voucher number
  - confidence estimation
  - filename build/sanitize
- `PDFService`
  - merge ordered task pages into single PDF
  - save PDF via storage service

## Parsing Rules (MVP)
- Subject labels priority: `核算单位`, `单位名称`, `公司名称`.
- Month normalization target: `YYYY-MM`.
- Voucher number normalization examples:
  - `记-470`, `记470`, `记—470` -> `记470`
- Filename format:
  - `{Subject}-{YYYY-MM}-{VoucherNo}.pdf`
- Sanitization:
  - remove illegal filename chars
  - trim whitespace
  - truncate long subject safely
  - fallback placeholders when fields missing

## Required Repository Structure
At minimum:
- `app/api/`
- `app/core/`
- `app/db/`
- `app/models/`
- `app/schemas/`
- `app/services/`
- `app/utils/`
- `tests/`
- `scripts/`
- `README.md`
- `MVP_SCOPE.md`
- `ARCHITECTURE.md`
- `API_CONTRACT.md`
- `DB_SCHEMA.md`
- `TASK_BOARD.md`
- `.env.example`

Suggested additions:
- `pyproject.toml`
- `Dockerfile`
- `docker-compose.yml`
- `alembic.ini`
- `alembic/` migration scaffolding

## Engineering Standards
- Python 3.11+
- FastAPI + Pydantic v2
- SQLAlchemy 2.x + Alembic
- `httpx` for external OCR calls
- `Pillow` for image validation/metadata
- `PyMuPDF` or `ReportLab` for PDF generation
- `pytest` for tests

## Testing Expectations
Unit tests:
- text normalization
- subject extraction
- month extraction
- voucher number extraction
- filename sanitization

Integration tests:
- create task
- upload pages
- finish upload
- recognize
- confirm generate
- query detail/list

## Delivery Standard
Outputs must be implementation-ready:
- clear contracts
- explicit assumptions
- practical module responsibilities
- deterministic core logic
- frontend-backend parallel development support

Avoid:
- over-engineering
- hidden assumptions
- placeholder-only docs

## Local Environment (Conda + pip)
Use an isolated Conda environment, then install project dependencies only with pip inside that environment.

### Create environment
```bash
conda create -y -n pku-voucher python=3.11 pip
```

### Activate environment
```bash
conda activate pku-voucher
```

### Install project dependencies (pip only)
```bash
python -m pip install -e '.[dev]'
```

### Validate setup
```bash
pytest
```

### Non-interactive alternatives
```bash
conda run -n pku-voucher python -m pip install -e '.[dev]'
conda run -n pku-voucher pytest
```
