import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft, Shield, Brain, FileText, Database, Cookie, UserCheck, Mail } from "lucide-react";

export const metadata: Metadata = {
  title: "Privacy Policy — Document AI Analyst",
  description:
    "How PDF-Assistant-RAG collects, uses, and protects your data. Learn about our privacy practices for document uploads, AI processing, and account information.",
  openGraph: {
    title: "Privacy Policy — Document AI Analyst",
    description:
      "How PDF-Assistant-RAG collects, uses, and protects your data.",
  },
};

const sections = [
  {
    id: "information-we-collect",
    icon: FileText,
    title: "1. Information We Collect",
    content: (
      <>
        <p>
          When you use PDF-Assistant-RAG, we collect the following categories of information
          to provide and improve our service:
        </p>
        <h3>Account Information</h3>
        <ul>
          <li>
            <strong>Registration data:</strong> username, email address, and a securely hashed
            password when you create an account.
          </li>
          <li>
            <strong>Profile information:</strong> any optional details you choose to provide.
          </li>
        </ul>
        <h3>Document Data</h3>
        <ul>
          <li>
            <strong>Uploaded files:</strong> PDFs, DOCX, TXT, Markdown, and other documents you
            upload for analysis.
          </li>
          <li>
            <strong>Extracted content:</strong> text, embeddings, and metadata extracted from your
            documents to enable semantic search and AI-powered question answering.
          </li>
          <li>
            <strong>Chat history:</strong> questions you ask and the AI-generated responses, stored
            to maintain conversation context.
          </li>
        </ul>
        <h3>Usage Data</h3>
        <ul>
          <li>
            <strong>Technical metadata:</strong> page views, feature interactions, query timestamps,
            and performance metrics to improve the platform.
          </li>
          <li>
            <strong>Device &amp; browser info:</strong> browser type, operating system, and basic
            device information for compatibility optimization.
          </li>
        </ul>
      </>
    ),
  },
  {
    id: "how-we-use-data",
    icon: Brain,
    title: "2. How We Use Your Data",
    content: (
      <>
        <p>Your data is used solely for the core functionality of the platform:</p>
        <ul>
          <li>
            <strong>AI-powered document analysis:</strong> Your documents are processed by
            open-source large language models (LLMs) hosted on HuggingFace to generate insights,
            summaries, and answers to your questions.
          </li>
          <li>
            <strong>Semantic search &amp; retrieval:</strong> Document embeddings are stored in
            vector databases (ChromaDB) to enable fast, accurate retrieval of relevant content.
          </li>
          <li>
            <strong>Conversation continuity:</strong> Chat history is stored per session so you
            can refer back to previous interactions.
          </li>
          <li>
            <strong>Service improvement:</strong> Aggregated, anonymized usage patterns help us
            identify bugs, optimize performance, and prioritize features.
          </li>
        </ul>
        <p>
          We <strong>do not</strong> use your uploaded documents or chat data to train or fine-tune
          any AI models. Your content remains private to your account.
        </p>
      </>
    ),
  },
  {
    id: "data-storage-security",
    icon: Shield,
    title: "3. Data Storage &amp; Security",
    content: (
      <>
        <p>We take data protection seriously and implement multiple layers of security:</p>
        <h3>Encryption</h3>
        <ul>
          <li>
            <strong>In transit:</strong> All communications between your browser and our servers
            are encrypted using TLS 1.3.
          </li>
          <li>
            <strong>At rest:</strong> Document files, embeddings, and user data are stored in
            encrypted storage volumes.
          </li>
          <li>
            <strong>Passwords:</strong> Never stored in plain text — we use bcrypt hashing with
            per-user salts.
          </li>
        </ul>
        <h3>Data Isolation</h3>
        <ul>
          <li>
            Each user&apos;s documents and embeddings are stored in isolated vector collections.
          </li>
          <li>
            Authentication is enforced at every API endpoint — users can only access their own
            data.
          </li>
          <li>
            JWT tokens with short expiration and refresh token rotation prevent unauthorized
            access.
          </li>
        </ul>
        <h3>Infrastructure</h3>
        <ul>
          <li>
            Servers are hosted on secure cloud infrastructure with strict access controls.
          </li>
          <li>
            Regular security audits and dependency updates are performed.
          </li>
        </ul>
      </>
    ),
  },
  {
    id: "data-retention",
    icon: Database,
    title: "4. Data Retention",
    content: (
      <>
        <p>We retain your data only as long as necessary to provide the service:</p>
        <ul>
          <li>
            <strong>Account data:</strong> Retained until you delete your account. You can request
            account deletion at any time.
          </li>
          <li>
            <strong>Uploaded documents &amp; embeddings:</strong> Retained until you delete them
            or close your account. Documents can be removed individually from the dashboard.
          </li>
          <li>
            <strong>Chat history:</strong> Retained per conversation. You can clear individual
            chats or your entire history from the settings page.
          </li>
          <li>
            <strong>Logs &amp; analytics:</strong> Aggregated usage data may be retained longer
            in anonymized form for service improvement.
          </li>
        </ul>
        <p>
          When you delete your account, all associated documents, embeddings, chat histories, and
          personal information are permanently deleted within 30 days.
        </p>
      </>
    ),
  },
  {
    id: "third-party-services",
    icon: Database,
    title: "5. Third-Party Services",
    content: (
      <>
        <p>
          PDF-Assistant-RAG integrates with the following third-party services to deliver its
          functionality:
        </p>
        <ul>
          <li>
            <strong>HuggingFace Inference API:</strong> Used to run open-source LLMs for document
            analysis. Document snippets may be sent to HuggingFace for inference; they are not
            stored or used for training. See{" "}
            <a
              href="https://huggingface.co/privacy"
              target="_blank"
              rel="noopener noreferrer"
            >
              HuggingFace&apos;s Privacy Policy
            </a>.
          </li>
          <li>
            <strong>Google OAuth (optional):</strong> If you choose to sign in with Google, we
            receive only your name and email address from your Google profile. See{" "}
            <a
              href="https://policies.google.com/privacy"
              target="_blank"
              rel="noopener noreferrer"
            >
              Google&apos;s Privacy Policy
            </a>.
          </li>
        </ul>
        <p>
          We do not sell your personal information or document data to any third party.
        </p>
      </>
    ),
  },
  {
    id: "cookies",
    icon: Cookie,
    title: "6. Cookies",
    content: (
      <>
        <p>We use only essential cookies required for the platform to function:</p>
        <ul>
          <li>
            <strong>Authentication cookies:</strong> JWT refresh tokens stored securely as
            HTTP-only cookies to maintain your login session.
          </li>
          <li>
            <strong>Local storage:</strong> Access tokens and UI preferences (theme, language)
            are stored in your browser&apos;s local storage. No tracking or advertising cookies
            are used.
          </li>
        </ul>
        <p>
          You can clear these at any time via your browser settings. Note that clearing
          authentication data will sign you out of your session.
        </p>
      </>
    ),
  },
  {
    id: "your-rights",
    icon: UserCheck,
    title: "7. Your Rights",
    content: (
      <>
        <p>You have the following rights regarding your data:</p>
        <ul>
          <li>
            <strong>Access:</strong> View all documents and data associated with your account at
            any time from your dashboard.
          </li>
          <li>
            <strong>Deletion:</strong> Delete individual documents or your entire account and
            associated data.
          </li>
          <li>
            <strong>Export:</strong> Request a copy of your data in a machine-readable format.
          </li>
          <li>
            <strong>Correction:</strong> Update your account information (username, email) from
            your profile settings.
          </li>
          <li>
            <strong>Withdraw consent:</strong> Stop using the service and delete your account at
            any time.
          </li>
        </ul>
        <p>
          To exercise any of these rights, please contact us using the information in the
          &ldquo;Contact&rdquo; section below.
        </p>
      </>
    ),
  },
  {
    id: "changes",
    icon: Shield,
    title: "8. Changes to This Policy",
    content: (
      <>
        <p>
          We may update this Privacy Policy from time to time. Changes will be communicated by:
        </p>
        <ul>
          <li>Posting the updated policy on this page with a new &ldquo;Last updated&rdquo; date.</li>
          <li>
            Sending a notification to your registered email address for material changes.
          </li>
        </ul>
        <p>
          Your continued use of the platform after changes constitutes acceptance of the updated
          policy. We encourage you to review this page periodically.
        </p>
      </>
    ),
  },
  {
    id: "contact",
    icon: Mail,
    title: "9. Contact Us",
    content: (
      <>
        <p>
          If you have any questions, concerns, or requests regarding this Privacy Policy or your
          data, please reach out through the project&rsquo;s official channels:
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

export default function PrivacyPage() {
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
              <Shield className="w-4 h-4 text-primary" />
            </div>
            <span className="font-semibold text-sm">Privacy Policy</span>
          </div>
        </div>
      </header>

      {/* ── Hero ──────────────────────────────────────── */}
      <section className="border-b border-border/50">
        <div className="mx-auto max-w-4xl px-6 py-16 sm:py-20 text-center">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-primary/10 border border-primary/20 text-sm text-primary mb-6">
            <Shield className="w-4 h-4" />
            Your data matters
          </div>
          <h1 className="text-4xl sm:text-5xl font-bold tracking-tight mb-4">
            Privacy Policy
          </h1>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            How we collect, use, and protect your data when you use PDF-Assistant-RAG.
          </p>
          <p className="mt-4 text-sm text-muted-foreground">
            <em>Last updated: May 30, 2026</em>
          </p>
        </div>
      </section>

      {/* ── Content ───────────────────────────────────── */}
      <div className="mx-auto max-w-4xl px-6 py-12 sm:py-16">
        {/* Table of Contents */}
        <nav className="mb-12 p-6 rounded-xl border border-border/50 bg-card/30" aria-label="Table of contents">
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
        Built with FastAPI • LangChain • ChromaDB • HuggingFace • Next.js
      </footer>
    </div>
  );
}
