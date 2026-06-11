# TODO - Issue #428 Pagination + Search for GET /documents

- [ ] Inspect current `GET /documents` route implementation and response schemas.
- [ ] Update `backend/app/routes/documents.py` to accept query params: `page`, `limit`, `q`.
- [ ] Implement SQLAlchemy filters for `q` (case-insensitive on `original_name`) and apply offset pagination.
- [ ] Execute count query using the same active filters to compute `total` and `total_pages`.
- [ ] Restructure response payload to `{ data, meta: { total, limit, page, total_pages } }`.
- [ ] Update `backend/app/schemas.py` models accordingly.
- [ ] Update/extend `backend/tests/test_documents.py` (and other tests if needed).
- [ ] Run backend tests to validate behavior.

