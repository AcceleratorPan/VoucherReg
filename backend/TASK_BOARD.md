# TASK_BOARD

## Milestone 1: Bootstrap
- [x] Create FastAPI project structure.
- [x] Add config, app factory, health endpoint, router registration.
- [x] Add dependency manifest and local run script.

## Milestone 2: Data Layer
- [x] Define SQLAlchemy models: `voucher_task`, `voucher_page`.
- [x] Add DB session management.
- [x] Add Alembic scaffold and initial migration.

## Milestone 3: Core Services
- [x] Storage service abstraction + local implementation.
- [x] OCR abstraction + mock provider + RapidOCR local provider.
- [x] Deterministic parsing service.
- [x] PDF generation service.

## Milestone 4: Voucher Workflow APIs
- [x] `POST /voucher-tasks`
- [x] `POST /voucher-tasks/{task_id}/pages`
- [x] `POST /voucher-tasks/{task_id}/finish-upload`
- [x] `POST /voucher-tasks/{task_id}/recognize`
- [x] `POST /voucher-tasks/{task_id}/confirm-generate`
- [x] `GET /voucher-tasks`
- [x] `GET /voucher-tasks/{task_id}`

## Milestone 5: Docs and Contracts
- [x] `README.md`
- [x] `MVP_SCOPE.md`
- [x] `ARCHITECTURE.md`
- [x] `API_CONTRACT.md`
- [x] `DB_SCHEMA.md`
- [x] `.env.example`

## Milestone 6: Testing
- [x] Add unit tests for parser and filename sanitization.
- [x] Add integration test skeleton for full task flow.
- [x] Run test suite and fix failing cases.
