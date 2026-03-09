# MVP Scope

## Product Goal
Enable users to capture voucher pages in WeChat Mini Program and generate one named PDF per voucher task.

## In Scope
- Create voucher task.
- Upload multiple page images in order.
- Distinguish first page (`pageIndex=0`) vs attachment pages.
- Store page metadata and task lifecycle state.
- OCR first page only.
- Deterministic metadata extraction:
  - Subject / Entity
  - Month (`YYYY-MM`)
  - Voucher number
- Return extraction result for manual user confirmation.
- Generate multi-page PDF in page order.
- Build final filename:
  - `{Subject}-{YYYY-MM}-{VoucherNo}.pdf`
- List task history and view task detail.

## Out of Scope
- OpenCV perspective correction.
- Direct COS upload from WeChat Mini Program.
- LLM-first extraction.
- Batch export and advanced archive search.
- Complex permission system.
- Automated attachment page classification beyond first-page rule.
- Advanced retries/workflow orchestration.

## Non-Negotiable Decisions
1. FastAPI is the backend core.
2. First-page-only OCR parsing.
3. OCR + deterministic parsing as primary extraction strategy.
4. Manual confirmation before final PDF generation.
5. Backend-mediated upload in MVP.

## MVP Acceptance Criteria
- End-to-end API flow works for one voucher task.
- Extracted fields are returned with confidence and review flag.
- User-confirmed values can override recognized values.
- Generated PDF preserves upload order and returns URL/path.
