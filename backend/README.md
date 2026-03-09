# Voucher Backend (FastAPI)

Backend service for accounting voucher capture workflows used by a WeChat Mini Program.

## What This MVP Does
- Create voucher tasks.
- Upload ordered page images (first page is metadata source).
- Finish upload and trigger OCR + deterministic parsing on first page only.
- Return extracted fields for manual user confirmation.
- Generate final multi-page PDF in upload order.
- Persist and return final PDF URL.
- List task history and task detail.

## Tech Stack
- Python 3.11+
- FastAPI
- Pydantic v2
- SQLAlchemy 2.x
- Alembic
- Pillow
- ReportLab
- pytest

## Project Structure
```text
app/
  api/
    deps.py
    error_handlers.py
    routes/
      downloads.py
      files.py
      health.py
      voucher_tasks.py
    router.py
  core/
    config.py
    exceptions.py
  db/
    base.py
    session.py
  models/
    voucher_task.py
    voucher_page.py
  schemas/
    base.py
    common.py
    voucher_task.py
  services/
    auth/
    ocr/
    parsing/
    pdf/
    storage/
    voucher_task_service.py
  utils/
    casing.py
    filename.py
  main.py
alembic/
tests/
scripts/
```

## Quick Start
### 1. Install dependencies
```bash
conda create -y -n pku-voucher python=3.11 pip
conda activate pku-voucher
python -m pip install -e '.[dev]'
```

### 2. Configure environment
```bash
cp .env.example .env
```

### 3. Run migrations
```bash
alembic upgrade head
```

### 4. Start server
```bash
./scripts/run_dev.sh
```

API docs:
- Swagger UI: `http://localhost:8000/docs`
- Health: `GET /health`

## Core Workflow
1. `POST /voucher-tasks` with body `{ "userId": "user_001" }`
2. `POST /voucher-tasks/{taskId}/pages?userId=user_001`
3. `POST /voucher-tasks/{taskId}/finish-upload?userId=user_001`
4. `POST /voucher-tasks/{taskId}/recognize?userId=user_001`
5. `POST /voucher-tasks/{taskId}/confirm-generate?userId=user_001`
6. `GET /voucher-tasks?userId=user_001`
7. `GET /voucher-tasks/{taskId}?userId=user_001`

## Status Machine
`draft -> uploaded -> recognized -> confirmed -> pdf_generated`

`failed` is a terminal error state for exceptional flows.

## Notes
- Public API fields use camelCase.
- Internal Python code uses snake_case.
- OCR uses local `RapidOCR` by default (no cloud key required).
- Storage defaults to local filesystem under `./data/storage`.
- Voucher task APIs are scoped by explicit `userId`.
- Generated PDFs are downloadable only through temporary `/downloads/{token}` links.
- WeChat Mini integration guide: `WECHAT_MINI_INTEGRATION_README.md`.

## RapidOCR Setup (Chinese OCR)
Install RapidOCR runtime in the project env:

```bash
python -m pip install rapidocr onnxruntime
```

Then configure `.env`:

```bash
OCR_PROVIDER=rapidocr
RAPIDOCR_TEXT_SCORE=0.5
RAPIDOCR_USE_DET=true
RAPIDOCR_USE_CLS=true
RAPIDOCR_USE_REC=true
```
