import subprocess
import time

issues = [
    # 15 Frontend & UI/UX Issues
    {
        "title": "feat(ui): Implement custom markdown renderer with syntax highlighting for chat responses",
        "body": "Description\\nCurrently, chat responses containing code snippets are displayed in plain text blocks. We should implement a markdown renderer with syntax highlighting (e.g., using prismjs or highlight.js) to make code blocks highly readable.\\n\\nRequirements\\nIntegrate a markdown parser with syntax highlighting.\\nSupport styling for common programming languages (Python, JavaScript, TypeScript, Bash, SQL, etc.).\\nEnsure the markdown container matches our modern UI theme.",
        "labels": "gssoc,level:intermediate,type:frontend"
    },
    {
        "title": "feat(ui): Add a copy-to-clipboard button for each AI chat message bubble",
        "body": "Description\\nAllow users to quickly copy the response text of any AI chat bubble with a single click. A small clipboard icon should appear on hover or next to the message bubble.\\n\\nRequirements\\nAdd a Copy button/icon to chat bubbles.\\nUse the navigator.clipboard API to copy response content.\\nShow a temporary Copied! tooltip or success micro-animation after copying.",
        "labels": "gssoc,level:beginner,type:frontend"
    },
    {
        "title": "feat(ui): Add Zoom in/out and Rotate features to the PDF Viewer panel",
        "body": "Description\\nTo improve readability of complex/small document text, add Zoom In, Zoom Out, and Rotation controls directly above the PDF viewer.\\n\\nRequirements\\nAdd zoom (in/out) control buttons to PDF viewer toolbar.\\nAdd clockwise rotation button.\\nMaintain viewer canvas crispness during zoom scaling.",
        "labels": "gssoc,level:intermediate,type:frontend"
    },
    {
        "title": "feat(ui): Add a full-screen toggle for the PDF Viewer panel",
        "body": "Description\\nWhen reviewing long documents alongside chat, users need a way to focus solely on the document. Implement a full-screen toggle that expands the PDF viewer to take up the full viewport.\\n\\nRequirements\\nAdd a Full Screen button in the PDF Viewer toolbar.\\nLeverage browser Fullscreen API or CSS overlays to expand the viewer.\\nSupport escape key to exit fullscreen mode.",
        "labels": "gssoc,level:beginner,type:frontend"
    },
    {
        "title": "feat(ui): Implement drag-and-drop file upload zone with hover animations",
        "body": "Description\\nProvide a better upload experience by allowing users to drag and drop PDF/txt files anywhere into the upload zone with clear visual animations.\\n\\nRequirements\\nCreate drop zone overlay on file hover.\\nImplement drag-over animations and transitions.\\nHandle multiple file drop events and trigger the upload pipeline.",
        "labels": "gssoc,level:intermediate,type:frontend"
    },
    {
        "title": "feat(ui): Add file size and format validation feedback before upload",
        "body": "Description\\nAvoid unnecessary backend calls and 500 errors by validating file size (max 50MB) and formats (.pdf, .txt) on the client side before uploading.\\n\\nRequirements\\nHook into file input select/drop events.\\nShow a clear warning banner/toast if a file is too large or unsupported.\\nDisable the upload trigger if file validation fails.",
        "labels": "gssoc,level:beginner,type:frontend"
    },
    {
        "title": "feat(ui): Add user initials avatar fallback when profile picture is missing",
        "body": "Description\\nIf a user doesn't upload an avatar image, show a styled colored circle containing their initials (e.g., PS for Paramjit Singh) instead of a generic placeholder icon.\\n\\nRequirements\\nParse user's display name or email to extract initials.\\nGenerate a deterministic background color based on user's name.\\nRender clean CSS circle avatar fallback.",
        "labels": "gssoc,level:beginner,type:design,type:frontend"
    },
    {
        "title": "feat(ui): Add customizable keyboard shortcuts cheat-sheet modal",
        "body": "Description\\nMake power-user keyboard shortcuts discoverable by adding a Keyboard Shortcuts cheat-sheet modal that can be opened from the footer/settings.\\n\\nRequirements\\nCreate a responsive help modal showing list of shortcuts (e.g., cmd+K to clear, esc to close modals).\\nAllow opening the modal via keypress (e.g., ?).",
        "labels": "gssoc,level:beginner,type:frontend"
    },
    {
        "title": "feat(ui): Add tooltips to all icon-only buttons in the chat panel",
        "body": "Description\\nImprove usability by adding tooltips (e.g., Copy text, Upload document, Text to speech) on hover for all icon-only actions.\\n\\nRequirements\\nIntegrate accessible tooltip components (e.g., Radix Tooltip).\\nEnforce short hover delay (e.g., 300ms) before showing tooltip.",
        "labels": "gssoc,level:beginner,type:accessibility,type:frontend"
    },
    {
        "title": "feat(ui): Implement multi-select soft deletion and restoration of documents",
        "body": "Description\\nAllow users to clean up their workspaces faster by selecting multiple documents to delete at once, and provide an option to restore them.\\n\\nRequirements\\nAdd checkboxes next to document names in the sidebar.\\nImplement a bulk delete action bar.\\nProvide a Recycle Bin view to restore soft-deleted documents.",
        "labels": "gssoc,level:intermediate,type:frontend"
    },
    {
        "title": "feat(ui): Implement scroll-to-bottom button in chat when scrolled up",
        "body": "Description\\nWhen users scroll up in chat to review previous messages, they should be able to jump back to the bottom instantly via a floating scroll-to-bottom button.\\n\\nRequirements\\nShow a floating arrow button when the user scrolls up past a certain threshold.\\nTrigger smooth scroll behavior back to the bottom when clicked.\\nHide the button once the scroll reaches the bottom.",
        "labels": "gssoc,level:beginner,type:frontend"
    },
    {
        "title": "feat(ui): Add a search bar inside the PDF Viewer to search text",
        "body": "Description\\nEnable users to find specific terms inside the PDF Viewer by building a search input that highlights matching occurrences.\\n\\nRequirements\\nIntegrate text search functionality (e.g., using react-pdf search hooks).\\nHighlight all search results in the document viewer.\\nAdd Next/Prev match navigation controls.",
        "labels": "gssoc,level:advanced,type:frontend"
    },
    {
        "title": "feat(ui): Add customizable font sizes for the chat interface in settings",
        "body": "Description\\nImprove accessibility for users with vision difficulties by providing options to scale font sizes for the chat bubbles in settings.\\n\\nRequirements\\nAdd font size selectors (Small, Medium, Large) in settings.\\nStore configuration in Zustand / localStorage.\\nDynamically adjust font sizes of message list elements.",
        "labels": "gssoc,level:beginner,type:accessibility,type:frontend"
    },
    {
        "title": "feat(ui): Add download transcript feature for chat sessions",
        "body": "Description\\nEnable users to export/download their complete chat transcript as a Markdown or PDF document.\\n\\nRequirements\\nAdd an Export button to the chat header.\\nFormat the conversation history (User and Assistant turns) into clean Markdown.\\nGenerate and trigger browser download for the file.",
        "labels": "gssoc,level:intermediate,type:frontend"
    },
    {
        "title": "feat(ui): Add dynamic page number jump input in the PDF Viewer",
        "body": "Description\\nFor long documents, scrolling through pages is tedious. Add a page number input in the viewer toolbar so users can type a page number and jump there instantly.\\n\\nRequirements\\nAdd a page jump text input (Page X of Y).\\nValidate that input is within range [1, total_pages].\\nNavigate viewer directly to target page on enter keypress.",
        "labels": "gssoc,level:beginner,type:frontend"
    },

    # 15 Backend & DB Issues
    {
        "title": "feat(api): Add pagination and search filters to documents list endpoint",
        "body": "Description\\nAs workspaces grow, loading all documents at once will degrade performance. We need to support offset pagination and keyword filtering on the /documents list API.\\n\\nRequirements\\nUpdate the document query function to accept page, limit, and query parameters.\\nPerform search filtering on document names in the database.\\nReturn pagination metadata (total, limit, page, total_pages).",
        "labels": "gssoc,level:intermediate,type:backend"
    },
    {
        "title": "feat(db): Add database indexes on document filename and user_id fields",
        "body": "Description\\nOptimize querying speeds for document listings and authorization checks by adding indexes on frequently queried foreign keys and string columns.\\n\\nRequirements\\nDefine SQLModel/SQLAlchemy indexes on documents.user_id and documents.filename fields.\\nVerify index creations in migration scripts.",
        "labels": "gssoc,level:beginner,type:backend"
    },
    {
        "title": "feat(api): Implement user password change endpoint with old password validation",
        "body": "Description\\nAdd an endpoint to support secure password rotation. The endpoint must validate that the user's current password matches before updating it.\\n\\nRequirements\\nAdd a POST /auth/change-password endpoint.\\nValidate current password hash.\\nUpdate with new securely hashed password.",
        "labels": "gssoc,level:beginner,type:backend,type:security"
    },
    {
        "title": "feat(api): Build system health/status endpoint checking DB, Celery, and Redis status",
        "body": "Description\\nBuild a deep health check endpoint /health/status that verifies connection statuses of PostgreSQL, Celery workers, and Redis broker instead of just returning 200.\\n\\nRequirements\\nAdd health check ping to SQLite/Postgres.\\nPing Redis client.\\nVerify celery worker availability via inspect API.",
        "labels": "gssoc,level:intermediate,type:backend"
    },
    {
        "title": "feat(rag): Add support for multi-column PDF layouts in chunker",
        "body": "Description\\nCurrently, the chunker parses text row-by-row, which mixes text columns in multi-column layouts (like academic papers). Implement layout-aware text extraction.\\n\\nRequirements\\nIntegrate layout parsers or configure pdfplumber to parse columns in reading order.\\nEnsure text lines are separated correctly before generating semantic chunks.",
        "labels": "gssoc,level:advanced,type:backend"
    },
    {
        "title": "feat(rag): Add customizable chunk_size and chunk_overlap query params to upload API",
        "body": "Description\\nAllow advanced users to customize chunking settings during file upload by exposing chunk_size and chunk_overlap parameters on the upload route.\\n\\nRequirements\\nExpose optional chunk_size and chunk_overlap inputs on document upload schema.\\nValidate input ranges (e.g., chunk_size <= 2000).\\nPass these options to the chunker process.",
        "labels": "gssoc,level:intermediate,type:backend"
    },
    {
        "title": "feat(api): Support renaming chat sessions",
        "body": "Description\\nEnable users to customize chat titles instead of relying on default placeholders. Implement a route to update chat session metadata.\\n\\nRequirements\\nCreate PATCH /chat/sessions/{session_id} route.\\nUpdate chat session title in the database.\\nAdd authorization check to make sure the user owns the session.",
        "labels": "gssoc,level:beginner,type:backend"
    },
    {
        "title": "feat(api): Add batch document upload endpoint",
        "body": "Description\\nAllow users to select and upload multiple PDF files simultaneously. The backend should handle ingestion tasks efficiently without blocking.\\n\\nRequirements\\nAdd POST /documents/upload/batch accepting List[UploadFile].\\nEnqueue parallel Celery tasks for parsing each document.\\nReturn list of created documents and task references.",
        "labels": "gssoc,level:intermediate,type:backend"
    },
    {
        "title": "feat(api): Add support for soft deleting chat sessions",
        "body": "Description\\nInstead of permanently deleting chat history, support soft deleting sessions, giving users a way to recover them later.\\n\\nRequirements\\nAdd is_deleted column to chat sessions table.\\nFilter active chat session queries to exclude deleted sessions.\\nBuild a session restore endpoint.",
        "labels": "gssoc,level:beginner,type:backend"
    },
    {
        "title": "feat(api): Export database backup as JSON/SQL files via admin route",
        "body": "Description\\nFor administrators, provide a secure route to export database tables for offsite backups.\\n\\nRequirements\\nCreate an admin-only GET endpoint /admin/export-db.\\nDump database records into a JSON or SQL script format.\\nAdd security headers and strict admin role checks.",
        "labels": "gssoc,level:advanced,type:backend,type:security"
    },
    {
        "title": "feat(rag): Add support for extracting and indexing image captions from PDFs",
        "body": "Description\\nMany diagrams and charts contain critical information. Capture image descriptions/captions and index them alongside vector contexts.\\n\\nRequirements\\nParse figures and captions from PDFs during ingestion.\\nEmbed captions and index them with metadata matching the parent document.",
        "labels": "gssoc,level:advanced,type:backend"
    },
    {
        "title": "feat(rag): Implement caching layer for embeddings to skip regenerations",
        "body": "Description\\nGenerating text embeddings via HuggingFace is computation-heavy. Cache embeddings of identical text chunks to save compute and API limits.\\n\\nRequirements\\nCreate an embeddings cache table or Redis cache layer.\\nCheck cache by hashing text chunks before sending them to the embedding model.",
        "labels": "gssoc,level:intermediate,type:backend,type:performance"
    },
    {
        "title": "feat(rag): Add hybrid search merging vector and BM25 scores via RRF",
        "body": "Description\\nCombine lexical (BM25) and semantic (Vector) search using Reciprocal Rank Fusion (RRF) to significantly improve retrieval accuracy.\\n\\nRequirements\\nRetrieve top results from vector database and BM25.\\nCalculate RRF formula on merged rankings.\\nReturn top unified chunks.",
        "labels": "gssoc,level:advanced,type:backend"
    },
    {
        "title": "feat(api): Implement automated PDF link and URL extraction in document metadata",
        "body": "Description\\nIdentify URLs and links inside PDFs during parsing to expose them in document details and metadata API.\\n\\nRequirements\\nParse PDF link annotations during extraction.\\nStore extracted URLs in a structured list under document metadata column.",
        "labels": "gssoc,level:intermediate,type:backend"
    },
    {
        "title": "feat(api): Implement email notifications for workspace invites",
        "body": "Description\\nWhen a user is invited to a workspace, notify them immediately by sending an invitation email containing the acceptance link.\\n\\nRequirements\\nAdd workspace invite dispatch logic to the email service.\\nFormat HTML invitation emails with details of workspace and link.",
        "labels": "gssoc,level:intermediate,type:backend"
    },

    # 10 Testing & Code Quality Issues
    {
        "title": "test(frontend): Write unit tests for auth-store (Zustand state)",
        "body": "Description\\nAdd test coverage for frontend state management by writing tests to verify Zustand auth-store state updates.\\n\\nRequirements\\nWrite unit tests for auth-store.ts using Vitest.\\nVerify login/logout, state clearing, and token saving behavior.",
        "labels": "gssoc,level:intermediate,type:testing"
    },
    {
        "title": "test(frontend): Set up Playwright visual regression tests for Landing Page",
        "body": "Description\\nEnsure visual styles don't break during future updates by setting up visual snapshot tests for the landing page.\\n\\nRequirements\\nWrite Playwright E2E visual regression tests.\\nSet up snapshot mismatch threshold and configurations in CI.",
        "labels": "gssoc,level:intermediate,type:testing"
    },
    {
        "title": "test(backend): Add unit tests for rate limiting middleware",
        "body": "Description\\nVerify that our rate limiting middleware correctly blocks calls exceeding limits and returns 429 status code.\\n\\nRequirements\\nWrite pytest test cases for the SlowAPI rate limiter.\\nVerify correct IP and user ID fallback resolutions.",
        "labels": "gssoc,level:intermediate,type:testing"
    },
    {
        "title": "test(backend): Add unit tests for database schema migrations",
        "body": "Description\\nWrite tests to ensure that database migrations run smoothly without corrupting current tables or dropping columns.\\n\\nRequirements\\nTest mock database initializations using older schemas.\\nVerify migration scripts execute cleanly and add missing columns.",
        "labels": "gssoc,level:intermediate,type:testing"
    },
    {
        "title": "test(backend): Mock HuggingFace Inference API in agent tests",
        "body": "Description\\nIsolate our agent unit tests from the live network by mocking HuggingFace client responses in pytest.\\n\\nRequirements\\nMock InferenceClient response formatting.\\nAssert that test suites run completely offline without relying on HF.",
        "labels": "gssoc,level:beginner,type:testing"
    },
    {
        "title": "test(backend): Add integration tests for Celery document ingestion tasks",
        "body": "Description\\nTest Celery ingestion pipelines end-to-end to confirm document parsing, chunking, and indexing run smoothly as async tasks.\\n\\nRequirements\\nRun integration test suites using mock celery task calls.\\nAssert that document status transitions cleanly from pending to ready.",
        "labels": "gssoc,level:advanced,type:testing"
    },
    {
        "title": "test(backend): Add boundary unit tests for validation schemas",
        "body": "Description\\nValidate the limits of input boundaries on schema models (e.g. invalid string sizes, username regex, invalid emails).\\n\\nRequirements\\nAdd unit tests for schemas.py boundary states.\\nAssert that pydantic validation throws expected errors.",
        "labels": "gssoc,level:beginner,type:testing"
    },
    {
        "title": "test(frontend): Add unit tests for API client helper functions",
        "body": "Description\\nWrite unit tests for the frontend api.ts wrapper functions to verify headers, parameters, and error handlers.\\n\\nRequirements\\nMock fetch API requests.\\nVerify proper formatting of headers (like Authorization tokens).",
        "labels": "gssoc,level:beginner,type:testing"
    },
    {
        "title": "test(backend): Add unit tests for PDF Chunker tables parsing",
        "body": "Description\\nVerify that our chunker's table detection works reliably under various test PDFs.\\n\\nRequirements\\nAdd tests in test_chunker.py using dummy PDFs containing tables.\\nAssert markdown output representations are parsed correctly.",
        "labels": "gssoc,level:intermediate,type:testing"
    },
    {
        "title": "test(ci): Add test-coverage report upload in GitHub actions",
        "body": "Description\\nConfigure GitHub CI to automatically generate and upload test coverage reports to coverage trackers.\\n\\nRequirements\\nAdd step in .github/workflows/ci.yml to generate xml coverage.\\nUpload report via codecov action.",
        "labels": "gssoc,level:beginner,type:devops,type:testing"
    },

    # 5 DevOps & CI/CD Issues
    {
        "title": "chore(docker): Add multi-stage Docker build for frontend Next.js app",
        "body": "Description\\nOur current Docker builds run both frontend and backend. Optimize the frontend footprint by containerizing the Next.js production build using multi-stage builds.\\n\\nRequirements\\nCreate a Dockerfile specifically optimized for the Next.js standalone build.\\nEliminate node_modules and dev dependencies from the final image stage.",
        "labels": "gssoc,level:intermediate,type:devops"
    },
    {
        "title": "chore(ci): Add linting check for Python imports order (isort) to CI",
        "body": "Description\\nKeep imports organized by running a strict imports linter in our GitHub actions pipeline.\\n\\nRequirements\\nIntegrate isort check in CI config.\\nEnforce consistent python formatting styles across PR checks.",
        "labels": "gssoc,level:beginner,type:devops"
    },
    {
        "title": "chore(ci): Add Prettier formatting validation to frontend PRs",
        "body": "Description\\nPrevent style inconsistencies in frontend submissions by checking formatting styles on incoming pull requests.\\n\\nRequirements\\nIntegrate Prettier formatting checks in GitHub workflows.\\nValidate TSX, TS, CSS, and Markdown structures.",
        "labels": "gssoc,level:beginner,type:devops"
    },
    {
        "title": "chore(docker): Setup Docker Compose profiles for running RAG with or without GPU",
        "body": "Description\\nAllow contributors without local GPUs to easily spin up CPU-only models by setting up Docker Compose profiles.\\n\\nRequirements\\nDefine compose profiles cpu and gpu in docker-compose.yml.\\nToggle models and configurations dynamically.",
        "labels": "gssoc,level:intermediate,type:devops"
    },
    {
        "title": "feat(devops): Add log rotation configuration for backend Docker containers",
        "body": "Description\\nPrevent docker logs from consuming excessive disk space over time. Configure default log rotations for containers.\\n\\nRequirements\\nAdd logging driver configuration in compose setup.\\nLimit file sizes and keep a max count of rotated logs.",
        "labels": "gssoc,level:beginner,type:devops"
    },

    # 5 Documentation Issues
    {
        "title": "docs: Document API authentication and authorization mechanisms in API_AUTH.md",
        "body": "Description\\nWrite a dedicated documentation file outlining our JWT authorization flow and API key setups for programmatic usage.\\n\\nRequirements\\nCreate docs/API_AUTH.md.\\nInclude details on header configurations, tokens expiry, and refresh scopes.",
        "labels": "gssoc,level:beginner,type:docs"
    },
    {
        "title": "docs: Add a comprehensive RAG Evaluation Guide",
        "body": "Description\\nHelp developers configure RAGAS datasets and evaluations by publishing a detailed guide.\\n\\nRequirements\\nCreate docs/RAG_EVALUATION.md.\\nExplain how to prepare sample question sheets and run evaluation pipelines.",
        "labels": "gssoc,level:beginner,type:docs"
    },
    {
        "title": "docs: Document setup and config for running background workers",
        "body": "Description\\nWrite instructions explaining how to configure Redis, Celery, and background workers locally for document extraction tests.\\n\\nRequirements\\nAdd docs/CELERY_SETUP.md with step-by-step setup guides.\\nDocument common troubleshooting states (like connection failures).",
        "labels": "gssoc,level:beginner,type:docs"
    },
    {
        "title": "docs: Create a tutorial on customizing LLM prompting and system rules",
        "body": "Description\\nProvide a guide explaining how to adjust prompts, agent personalities, and system rules in prompt files.\\n\\nRequirements\\nCreate docs/PROMPT_CUSTOMIZATION.md.\\nInclude examples of updating ReAct frameworks and systems prompts.",
        "labels": "gssoc,level:beginner,type:docs"
    },
    {
        "title": "docs: Document database schema diagram and relationships in DATABASE.md",
        "body": "Description\\nWrite database schema documentation detailing SQLModel definitions and relationships between Workspaces, Documents, Users, and Chat logs.\\n\\nRequirements\\nCreate docs/DATABASE.md.\\nDesign a database ER diagram using Mermaid.js layout.",
        "labels": "gssoc,level:beginner,type:docs"
    }
]

print(f"Loaded {len(issues)} issues to create.")
for i, issue in enumerate(issues, 1):
    title = issue["title"]
    body = issue["body"]
    labels = issue["labels"]
    
    print(f"Creating issue [{i}/50]: {title}...")
    
    # Pre-create labels if they don't exist
    for label in labels.split(','):
        subprocess.run(["gh", "label", "create", label.strip()], capture_output=True)
        
    # Create the issue
    res = subprocess.run([
        "gh", "issue", "create",
        "--title", title,
        "--body", body,
        "--label", labels
    ], capture_output=True, text=True)
    
    if res.returncode != 0:
        print(f"Error creating issue: {res.stderr}")
    else:
        print(f"Created: {res.stdout.strip()}")
        
    # Sleep to stay within API limit and avoid abusing the endpoint
    time.sleep(3)

print("Finished creating all 50 issues successfully!")
