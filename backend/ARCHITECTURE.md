# Architecture

## Overview
The backend is designed as a modular FastAPI service with explicit boundaries for OCR, parsing, storage, and PDF generation.

## High-Level Components
- API Layer (`app/api`)
  - HTTP contracts and request validation.
  - Dependency injection and route orchestration.
  - Error envelope handling.
- Service Layer (`app/services`)
  - Voucher task workflow and status transitions.
  - OCR adapter orchestration.
  - Deterministic parsing logic.
  - PDF generation and persistence.
- Data Layer (`app/models`, `app/db`)
  - SQLAlchemy models for tasks/pages.
  - Session management.
  - Alembic migration support.
- Utility Layer (`app/utils`)
  - camelCase conversion.
  - filename sanitization and generation.

## Request Flow
1. Client creates task -> `voucher_task` in `draft`.
2. Client uploads pages -> files saved by `StorageService`, metadata in `voucher_page`.
3. Client finishes upload -> task transitions to `uploaded`.
4. Client requests recognize -> OCR first page + parsing + preview filename.
5. Client confirms fields -> backend generates PDF and saves final file.
6. Task transitions to `pdf_generated`, history available via list/detail APIs.

## Key Service Contracts
### StorageService
- Save uploads and generated binaries.
- Read file bytes for OCR and PDF workflows.
- Local implementation now, COS implementation placeholder included.

### OCRService
- `MockOCRService`: default for local development and testing.
- `RapidOCRService`: local Chinese OCR implementation using `rapidocr`
  (no external cloud dependency for MVP/industrial on-prem deployment).

### ParsingService
- Normalize OCR text.
- Extract subject/month/voucher number via deterministic rules.
- Compute confidence and `needsUserReview`.
- Build filename preview.

### PDFService
- Generate one-page-per-image PDF in deterministic order.
- Return bytes for persistence.

## Status Machine
- `draft -> uploaded -> recognized -> confirmed -> pdf_generated`
- Any non-terminal stage may transition to `failed` on unrecoverable errors.

Guard conditions:
- `finish-upload`: at least one page exists.
- `recognize`: task status must be `uploaded`.
- `confirm-generate`: task status must be `recognized` and required fields present.

## Extensibility
- OCR and storage adapters are provider-driven.
- Business flow is isolated in `VoucherTaskService` for easier testing and evolution.
- API remains stable even if OCR/storage internals are swapped.
