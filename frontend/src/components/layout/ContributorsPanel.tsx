"use client";

import { useState, useEffect } from "react";
import { GitBranch, Star, GitPullRequest, Users, X, Trophy, ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";

interface Contributor {
  login: string;
  avatar_url: string;
  html_url: string;
  contributions: number;
}

interface RepoStats {
  stargazers_count: number;
  forks_count: number;
  open_issues_count: number;
}

export default function ContributorsPanel({ onClose }: { onClose: () => void }) {
  const [contributors, setContributors] = useState<Contributor[]>([]);
  const [stats, setStats] = useState<RepoStats | null>(null);
  const [loading, setLoading] = useState(true);

  const REPO = "param20h/PDF-Assistant-RAG";

  useEffect(() => {
    Promise.all([
      fetch(`https://api.github.com/repos/${REPO}/contributors?per_page=30`).then((r) => r.json()),
      fetch(`https://api.github.com/repos/${REPO}`).then((r) => r.json()),
    ])
      .then(([contribs, repo]) => {
        setContributors(Array.isArray(contribs) ? contribs : []);
        setStats(repo);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const medals = ["🥇", "🥈", "🥉"];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-background/80 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Panel */}
      <div className="relative w-full max-w-2xl max-h-[85vh] flex flex-col rounded-2xl border border-border/60 bg-card shadow-2xl overflow-hidden animate-fade-in-up">

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border/50 bg-gradient-to-r from-primary/10 to-transparent flex-shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-primary/15 flex items-center justify-center">
              <Trophy className="w-5 h-5 text-primary" />
            </div>
            <div>
              <h2 className="font-bold text-base">Hall of Fame</h2>
              <p className="text-xs text-muted-foreground">GSSOC Contributors — thank you! 🎉</p>
            </div>
          </div>
          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={onClose}>
            <X className="w-4 h-4" />
          </Button>
        </div>

        {/* Stats bar */}
        {stats && (
          <div className="flex items-center gap-6 px-6 py-3 bg-muted/30 border-b border-border/30 flex-shrink-0">
            <a
              href={`https://github.com/${REPO}`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 text-sm hover:text-primary transition-colors"
            >
              <Star className="w-4 h-4 text-yellow-500" />
              <span className="font-semibold">{stats.stargazers_count}</span>
              <span className="text-muted-foreground">stars</span>
            </a>
            <div className="flex items-center gap-1.5 text-sm">
              <GitPullRequest className="w-4 h-4 text-green-500" />
              <span className="font-semibold">{stats.forks_count}</span>
              <span className="text-muted-foreground">forks</span>
            </div>
            <div className="flex items-center gap-1.5 text-sm">
              <Users className="w-4 h-4 text-primary" />
              <span className="font-semibold">{contributors.length}</span>
              <span className="text-muted-foreground">contributors</span>
            </div>
          </div>
        )}

        {/* Contributors grid */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="grid grid-cols-3 sm:grid-cols-4 gap-4">
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="flex flex-col items-center gap-2 animate-pulse">
                  <div className="w-14 h-14 rounded-full bg-muted" />
                  <div className="h-3 w-16 rounded bg-muted" />
                  <div className="h-2 w-10 rounded bg-muted" />
                </div>
              ))}
            </div>
          ) : contributors.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
              <Users className="w-12 h-12 mb-3 opacity-30" />
              <p className="text-sm">No contributors yet — be the first!</p>
            </div>
          ) : (
            <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-5">
              {contributors.map((c, i) => (
                <a
                  key={c.login}
                  href={c.html_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="group flex flex-col items-center gap-2 rounded-xl p-3 hover:bg-accent/50 transition-all duration-200"
                >
                  <div className="relative">
                    {/* Medal for top 3 */}
                    {i < 3 && (
                      <span className="absolute -top-1.5 -right-1.5 text-base leading-none">
                        {medals[i]}
                      </span>
                    )}
                    <img
                      src={c.avatar_url}
                      alt={c.login}
                      width={56}
                      height={56}
                      className="w-14 h-14 rounded-full border-2 border-border/50 group-hover:border-primary/50 transition-colors object-cover"
                    />
                  </div>
                  <span className="text-xs font-medium text-center leading-tight truncate w-full text-center group-hover:text-primary transition-colors">
                    {c.login}
                  </span>
                  <span className="text-[10px] text-muted-foreground">
                    {c.contributions} commit{c.contributions !== 1 ? "s" : ""}
                  </span>
                </a>
              ))}
            </div>
          )}
        </div>

        {/* Footer CTA */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-border/50 bg-muted/20 flex-shrink-0">
          <p className="text-xs text-muted-foreground">
            Want to see your name here?{" "}
            <a
              href={`https://github.com/${REPO}/issues?q=label%3A%22good+first+issue%22`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary underline underline-offset-2 hover:no-underline"
            >
              Pick an issue
            </a>{" "}
            and open a PR to <code className="text-[10px] bg-muted px-1 py-0.5 rounded">dev</code>!
          </p>
          <a
            href={`https://github.com/${REPO}`}
            target="_blank"
            rel="noopener noreferrer"
          >
            <Button variant="outline" size="sm" className="h-7 text-xs gap-1.5">
              <GitBranch className="w-3.5 h-3.5" />
              View on GitHub
              <ExternalLink className="w-3 h-3" />
            </Button>
          </a>
        </div>
      </div>
    </div>
  );
}
