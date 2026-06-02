# E2E Testing with Playwright 🎭

This directory contains End-to-End (E2E) tests for the PDF Assistant RAG frontend.

## 🧪 Test Coverage

1.  **Authentication**: Login and Registration flows.
2.  **Document Management**: PDF upload, processing state, and deletion.
3.  **Chat**: Sending messages, receiving streaming responses with markdown support (tables, code blocks), and viewing sources.
4.  **Visual Regression**: Snapshot testing for key pages (Login, Register, Dashboard).

## 🚀 Running Tests

### Prerequisites
Ensure you have installed the dependencies:
```bash
cd frontend
npm install
npx playwright install chromium
```

### Run all tests
```bash
npm run test:e2e
```

### Run tests in UI mode
```bash
npm run test:e2e:ui
```

## 🛠️ Testing Strategy

We use Playwright's `page.route` to mock the backend API. This allows us to test the frontend in isolation, ensuring fast and reliable tests that don't depend on a running database or heavy LLM models.

### Key Patterns
- **Global Auth**: Mapped via `localStorage` injection in `beforeEach` or `addInitScript`.
- **Streaming**: Mocked using `text/event-stream` to verify the chat's real-time feel.
- **Snapshots**: Used to catch unintended UI changes in critical views.
