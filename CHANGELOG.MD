# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.0] - 2026-05-16
### Added
- Configured GSSOC contributor workflow on the `dev` branch.

### Fixed
- Resolved React Hook linting errors (`react-hooks/set-state-in-effect`) in CI pipelines by lazy-initializing the loading state to prevent `setLoading(false)` execution inside the effect body.
- Fixed chat scroll component tracking using a `bottomRef` sentinel and `scrollIntoView` mechanism to replace the broken `scrollRef` on the ScrollArea wrapper.

### Documentation
- Extensively overhauled `README.md` to add full project documentation, an explicit RAG pipeline architectural diagram, comprehensive API reference, and GSSOC contribution guides.

## [0.3.0] - 2026-04-15
### Added
- Implemented a brand new UI and upgraded internal RAG model architectures.
- Configured native Hugging Face Spaces Docker deployment handling non-root user execution, model pre-download caching, and custom keep-alive timeouts.

### Changed
- Switched default open-source inference engine to `Qwen2.5-72B-Instruct` to leverage Hugging Face free-tier hardware.

### Fixed
- Patched critical `list index out of range` runtime crash by explicitly handling empty choice selections from LLM responses.
- Adjusted production API routing to enforce same-origin API calls and added native `HEAD` method support to satisfy Next.js route prefetching rules.
- Upgraded text chunking modules to use `langchain_text_splitters` to ensure compatibility with LangChain v0.3+.
- Removed bulky compiled binary assets before pushing to Hugging Face Spaces storage layers.

## [0.2.0] - 2026-02-26
### Added
- Implemented an alternative lightweight RAG pipeline utilizing a Pinecone vector database index, Gemini embeddings, and Render hosting deployment profiles.
- Integrated automated Google Cloud Run continuous deployment (CD) workflows via Google Cloud Platform (GCP).
- Added `ProxyFix` middleware support to securely preserve OAuth authentication headers behind Render's reverse proxy structure.

### Fixed
- Cleaned hardcoded testing credentials and placeholder URIs flagged during automated GitHub secret scanning routines.

## [0.1.0] - 2024-06-25
### Added
- Initialized core repository, licensing infrastructure, and baseline documentation assets.
- Built initial RAG application architecture featuring file ingestion systems parsing raw `.txt`, `.docx`, and `.md` formats.
- Implemented native Google Authentication security layers.

[unreleased]: https://github.com/param20h/PDF-Assistant-RAG/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/param20h/PDF-Assistant-RAG/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/param20h/PDF-Assistant-RAG/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/param20h/PDF-Assistant-RAG/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/param20h/PDF-Assistant-RAG/commits/dev