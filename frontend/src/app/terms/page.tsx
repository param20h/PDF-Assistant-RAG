
import Link from "next/link";
import {
  ArrowLeft,
  Shield,
  CheckCircle,
  FileText,
  AlertTriangle,
  UserCheck,
  Scale,
  Ban,
  RefreshCw,
  Mail,
} from "lucide-react";

const sections = [
  {
    id: "acceptance",
    icon: CheckCircle,
    title: "1. Acceptance of Terms",
    content: (
      <>
        <p>
          By accessing or using PDF-Assistant-RAG (&ldquo;the Platform&rdquo;), you agree to be
          bound by these Terms of Service (&ldquo;Terms&rdquo;). If you do not agree to all terms,
          you must not use the Platform.
        </p>
        <p>
          These Terms apply to all visitors, users, and contributors to the Platform. By creating
          an account, uploading documents, or interacting with the service in any way, you signify
          your acceptance of these Terms.
        </p>
      </>
    ),
  },
  {
    id: "service-description",
    icon: FileText,
    title: "2. Description of Service",
    content: (
      <>
        <p>
          PDF-Assistant-RAG is an open-source document analysis platform that allows users to upload
          documents (PDF, DOCX, TXT, Markdown) and interact with them through AI-powered semantic
          search and chat, using Retrieval-Augmented Generation (RAG) and open-source large language
          models (LLMs).
        </p>
        <p>The core features include:</p>
        <ul>
          <li>Document upload, storage, and management</li>
          <li>AI-powered question answering and document analysis</li>
          <li>Semantic search across uploaded documents</li>
          <li>Conversation history and context retention</li>
          <li>Multi-language support (English, Hindi, Spanish, French)</li>
        </ul>
        <p>
          The Platform is provided &ldquo;as is&rdquo; and &ldquo;as available&rdquo; for
          educational and productivity purposes. The maintainers make no guarantees about the
          accuracy, completeness, or reliability of AI-generated responses.
        </p>
      </>
    ),
  },
  {
    id: "accounts",
    icon: UserCheck,
    title: "3. User Accounts &amp; Registration",
    content: (
      <>
        <p>To use certain features of the Platform, you must register for an account:</p>
        <ul>
          <li>
            <strong>Accuracy:</strong> You agree to provide accurate, current, and complete
            information during registration and to update it as necessary.
          </li>
          <li>
            <strong>Security:</strong> You are responsible for safeguarding your password and for
            all activities under your account. Notify the maintainers immediately of any
            unauthorized use.
          </li>
          <li>
            <strong>Account types:</strong> The Platform supports email/password registration and
            optional Google OAuth sign-in.
          </li>
          <li>
            <strong>One account per person:</strong> You may not create multiple accounts for the
            same individual unless explicitly permitted.
          </li>
          <li>
            <strong>No shared accounts:</strong> Account sharing with unauthorized users is
            prohibited.
          </li>
        </ul>
      </>
    ),
  },
  {
    id: "acceptable-use",
    icon: Ban,
    title: "4. Acceptable Use",
    content: (
      <>
        <p>You agree to use the Platform only for lawful purposes and in accordance with these Terms. Prohibited activities include:</p>
        <ul>
          <li>
            Uploading malware, viruses, or any malicious code
          </li>
          <li>
            Uploading illegal, obscene, defamatory, or infringing content
          </li>
          <li>
            Attempting to bypass authentication, access other users&apos; data, or exploit the
            system
          </li>
          <li>
            Using the Platform for automated scraping, data mining, or high-volume API abuse
          </li>
          <li>
            Reverse-engineering, decompiling, or attempting to extract the source code of
            proprietary components
          </li>
          <li>
            Interfering with the operation of the Platform or its underlying infrastructure
          </li>
        </ul>
      </>
    ),
  },
  {
    id: "content-data",
    icon: Shield,
    title: "5. Uploaded Content &amp; Data",
    content: (
      <>
        <p>
          You retain full ownership of all documents and content you upload to the Platform
          (&ldquo;Your Content&rdquo;). By uploading, you grant the Platform a limited, temporary
          license to process, store, and analyze Your Content solely for the purpose of providing
          the service.
        </p>
        <h3>Data Handling</h3>
        <ul>
          <li>
            Your documents are processed by open-source LLMs hosted on HuggingFace. Document
            snippets may be sent for inference but are not stored or used for training.
          </li>
          <li>
            Document embeddings are stored in per-user isolated vector collections (ChromaDB).
          </li>
          <li>
            Chat history is stored per session to maintain conversation context.
          </li>
        </ul>
        <h3>Your Responsibilities</h3>
        <ul>
          <li>
            You represent that you own or have the necessary rights to upload and process Your
            Content.
          </li>
          <li>
            You must not upload documents containing sensitive personal information, trade secrets,
            or classified data unless you have the legal right to do so.
          </li>
          <li>
            You are solely responsible for the legality, reliability, and accuracy of Your Content.
          </li>
        </ul>
        <p>
          See our{" "}
          <Link href="/privacy" className="text-primary hover:underline">
            Privacy Policy
          </Link>{" "}
          for more details on how we handle your data.
        </p>
      </>
    ),
  },
  {
    id: "intellectual-property",
    icon: Scale,
    title: "6. Intellectual Property",
    content: (
      <>
        <p>
          The Platform codebase is open-source and licensed under the{" "}
          <a
            href="https://opensource.org/licenses/MIT"
            target="_blank"
            rel="noopener noreferrer"
          >
            MIT License
          </a>. This means:
        </p>
        <ul>
          <li>
            You may freely use, modify, and distribute the source code, subject to the terms of
            the MIT License.
          </li>
          <li>
            The name &ldquo;PDF-Assistant-RAG,&rdquo; its logo, and branding elements may not be
            used without explicit permission.
          </li>
          <li>
            AI-generated responses produced by the Platform are provided without warranty and
            should not be considered professional advice (legal, financial, medical, etc.).
          </li>
        </ul>
      </>
    ),
  },
  {
    id: "liability",
    icon: AlertTriangle,
    title: "7. Limitation of Liability",
    content: (
      <>
        <p>
          The Platform is provided free of charge as an open-source project. To the fullest extent
          permitted by law:
        </p>
        <ul>
          <li>
            The maintainers shall not be liable for any indirect, incidental, special,
            consequential, or punitive damages arising from your use of the Platform.
          </li>
          <li>
            AI-generated content may contain errors, omissions, or inaccuracies. You should
            independently verify critical information.
          </li>
          <li>
            The Platform makes no guarantees about uptime, availability, or data durability,
            though reasonable efforts are made to maintain the service.
          </li>
        </ul>
      </>
    ),
  },
  {
    id: "termination",
    icon: Ban,
    title: "8. Termination",
    content: (
      <>
        <p>
          We reserve the right to suspend or terminate your access to the Platform at any time,
          without prior notice, for:
        </p>
        <ul>
          <li>Violation of these Terms of Service</li>
          <li>Engaging in prohibited or illegal activities</li>
          <li>Extended inactivity of your account</li>
          <li>At your request via account deletion</li>
        </ul>
        <p>
          Upon termination, your access to documents, chat history, and account data will be
          revoked. You may request a data export before account deletion by contacting the
          maintainers.
        </p>
      </>
    ),
  },
  {
    id: "changes-to-terms",
    icon: RefreshCw,
    title: "9. Changes to These Terms",
    content: (
      <>
        <p>
          We may revise these Terms from time to time. The most current version will always be
          posted on this page. Material changes will be communicated via:
        </p>
        <ul>
          <li>A notice on the Platform dashboard</li>
          <li>Email notification to registered users (for significant changes)</li>
        </ul>
        <p>
          Your continued use of the Platform after changes take effect constitutes acceptance of
          the revised Terms.
        </p>
      </>
    ),
  },
  {
    id: "contact",
    icon: Mail,
    title: "10. Contact Us",
    content: (
      <>
        <p>
          If you have any questions about these Terms, please reach out through the project&rsquo;s
          official channels:
        </p>
        <ul>
          <li>
            <strong>GitHub Issues:</strong>{" "}
            <a
              href="https://github.com/param20h/PDF-Assistant-RAG/issues"
              target="_blank"
              rel="noopener noreferrer"
            >
              github.com/param20h/PDF-Assistant-RAG/issues
            </a>
          </li>
          <li>
            <strong>GitHub Discussions:</strong>{" "}
            <a
              href="https://github.com/param20h/PDF-Assistant-RAG/discussions"
              target="_blank"
              rel="noopener noreferrer"
            >
              github.com/param20h/PDF-Assistant-RAG/discussions
            </a>
          </li>
          <li>
            <strong>LinkedIn:</strong>{" "}
            <a
              href="https://www.linkedin.com/in/param20h/"
              target="_blank"
              rel="noopener noreferrer"
            >
              linkedin.com/in/param20h
            </a>
          </li>
        </ul>
      </>
    ),
  },
];

export default function TermsPage() {
  return (
    <div className="min-h-screen bg-background">
      {/* ── Header ────────────────────────────────────── */}
      <header className="sticky top-0 z-50 border-b border-border/50 bg-card/50 backdrop-blur-md">
        <div className="mx-auto max-w-4xl flex items-center justify-between px-6 h-14">
          <Link
            href="/"
            className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Home
          </Link>
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-primary/15 flex items-center justify-center">
              <Scale className="w-4 h-4 text-primary" />
            </div>
            <span className="font-semibold text-sm">Terms of Service</span>
          </div>
        </div>
      </header>

      {/* ── Hero ──────────────────────────────────────── */}
      <section className="border-b border-border/50">
        <div className="mx-auto max-w-4xl px-6 py-16 sm:py-20 text-center">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-primary/10 border border-primary/20 text-sm text-primary mb-6">
            <Scale className="w-4 h-4" />
            Know your rights
          </div>
          <h1 className="text-4xl sm:text-5xl font-bold tracking-tight mb-4">
            Terms of Service
          </h1>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            The rules and guidelines for using PDF-Assistant-RAG, our open-source document
            analysis platform.
          </p>
          <p className="mt-4 text-sm text-muted-foreground">
            <em>Last updated: May 30, 2026</em>
          </p>
        </div>
      </section>

      {/* ── Content ───────────────────────────────────── */}
      <div className="mx-auto max-w-4xl px-6 py-12 sm:py-16">
        {/* Table of Contents */}
        <nav
          className="mb-12 p-6 rounded-xl border border-border/50 bg-card/30"
          aria-label="Table of contents"
        >
          <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-4">
            On this page
          </h2>
          <ul className="space-y-2">
            {sections.map((section) => (
              <li key={section.id}>
                <a
                  href={`#${section.id}`}
                  className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
                >
                  <section.icon className="w-3.5 h-3.5 shrink-0 text-primary" />
                  {section.title}
                </a>
              </li>
            ))}
          </ul>
        </nav>

        {/* Sections */}
        <div className="prose prose-sm sm:prose-base dark:prose-invert max-w-none prose-headings:font-semibold prose-headings:tracking-tight prose-h2:text-foreground prose-h3:text-foreground prose-p:text-muted-foreground prose-p:leading-relaxed prose-a:text-primary prose-a:no-underline hover:prose-a:underline prose-strong:text-foreground prose-li:text-muted-foreground prose-li:marker:text-primary/60">
          {sections.map((section) => (
            <section key={section.id} id={section.id} className="mb-12 scroll-mt-20">
              <div className="flex items-center gap-3 mb-6">
                <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                  <section.icon className="w-4 h-4 text-primary" />
                </div>
                <h2 className="text-xl sm:text-2xl !my-0">{section.title}</h2>
              </div>
              {section.content}
              <hr className="mt-8 border-border/30" />
            </section>
          ))}
        </div>

        {/* Footer note */}
        <div className="mt-8 text-center">
          <p className="text-sm text-muted-foreground">
            Have questions?{" "}
            <a
              href="https://github.com/param20h/PDF-Assistant-RAG/discussions"
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary hover:underline"
            >
              Start a discussion
            </a>
          </p>
        </div>
      </div>

      {/* ── Footer ────────────────────────────────── */}
      <footer className="text-center py-6 text-xs text-muted-foreground border-t border-border/50">
        Built with FastAPI &bull; LangChain &bull; ChromaDB &bull; HuggingFace &bull; Next.js
      </footer>
    </div>
  );
}
