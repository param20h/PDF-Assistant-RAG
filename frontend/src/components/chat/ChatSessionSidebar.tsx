"use client";

import { useState, useEffect } from "react";
import { Plus, Edit2, Trash2, MessageSquare, ChevronLeft } from "lucide-react";
import { useChatStore, type ChatSession } from "@/store/chat-store";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

export default function ChatSessionSidebar() {
  const sessions = useChatStore((state) => state.sessions);
  const activeSessionId = useChatStore((state) => state.activeSessionId);
  const fetchSessions = useChatStore((state) => state.fetchSessions);
  const createSession = useChatStore((state) => state.createSession);
  const renameSession = useChatStore((state) => state.renameSession);
  const deleteSession = useChatStore((state) => state.deleteSession);
  const setActiveSessionId = useChatStore((state) => state.setActiveSessionId);
  const fetchSessionHistory = useChatStore((state) => state.fetchSessionHistory);

  const [isOpen, setIsOpen] = useState(true);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [creating, setCreating] = useState(false);

  // Load sessions on mount
  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  const handleCreate = async () => {
    if (creating) return;
    setCreating(true);
    try {
      const defaultTitle = `Chat ${sessions.length + 1}`;
      const newId = await createSession(defaultTitle);
      setEditingId(newId);
      setEditTitle(defaultTitle);
    } catch (err) {
      console.error(err);
    } finally {
      setCreating(false);
    }
  };

  const handleStartRename = (session: ChatSession, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingId(session.id);
    setEditTitle(session.title);
  };

  const handleSaveRename = async (id: string, e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!editTitle.trim()) {
      setEditingId(null);
      return;
    }
    try {
      await renameSession(id, editTitle.trim());
    } catch (err) {
      console.error(err);
    } finally {
      setEditingId(null);
    }
  };

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirm("Are you sure you want to delete this chat session?")) {
      try {
        await deleteSession(id);
      } catch (err) {
        console.error(err);
      }
    }
  };

  const handleSelectSession = async (id: string) => {
    setActiveSessionId(id);
    await fetchSessionHistory(id);
  };

  const handleSessionKeyDown = (session: ChatSession, e: React.KeyboardEvent) => {
    if (editingId === session.id) return;
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      void handleSelectSession(session.id);
    }
  };

  return (
    <div className={cn("relative flex h-full border-r border-border/50 bg-card/20 select-none transition-all duration-300", isOpen ? "w-64" : "w-0")}>
      <div className={cn("flex flex-col h-full w-full overflow-hidden transition-opacity duration-200", isOpen ? "opacity-100" : "opacity-0 pointer-events-none")}>
        {/* Sidebar Header */}
        <div className="flex items-center justify-between p-3 border-b border-border/50 shrink-0 bg-card/45">
          <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Chat Sessions</span>
          <Button
            onClick={handleCreate}
            variant="outline"
            size="icon"
            className="h-7 w-7 bg-background/50 hover:bg-accent hover:text-accent-foreground"
            disabled={creating}
            aria-label="Create new chat session"
          >
            <Plus className="w-4 h-4" />
          </Button>
        </div>

        {/* Sessions List */}
        <div className="flex-1 overflow-y-auto p-2 space-y-1 scrollbar-thin">
          {sessions.length === 0 ? (
            <div className="text-center py-8 px-4">
              <p className="text-xs text-muted-foreground">No chat sessions. Click &quot;+&quot; to start a new chat.</p>
            </div>
          ) : (
            sessions.map((session) => {
              const isActive = session.id === activeSessionId;
              const isEditing = session.id === editingId;

              return (
                <div
                  key={session.id}
                  role="button"
                  tabIndex={isEditing ? -1 : 0}
                  aria-current={isActive ? "true" : undefined}
                  aria-label={`Open chat session ${session.title}`}
                  onClick={() => !isEditing && handleSelectSession(session.id)}
                  onKeyDown={(e) => handleSessionKeyDown(session, e)}
                  className={cn(
                    "group flex items-center justify-between rounded-lg px-3 py-2 text-sm transition-all duration-200 cursor-pointer border focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                    isActive
                      ? "bg-accent/80 border-accent text-accent-foreground shadow-sm"
                      : "border-transparent hover:bg-card/60 hover:text-foreground text-muted-foreground"
                  )}
                >
                  <div className="flex items-center gap-2 min-w-0 flex-1">
                    <MessageSquare className={cn("w-4 h-4 shrink-0", isActive ? "text-primary" : "text-muted-foreground")} />
                    
                    {isEditing ? (
                      <form
                        onSubmit={(e) => handleSaveRename(session.id, e)}
                        className="flex items-center gap-1 w-full"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <Input
                          value={editTitle}
                          onChange={(e) => setEditTitle(e.target.value)}
                          className="h-6 text-xs px-1 py-0 bg-background/50 border-input w-full"
                          autoFocus
                          onBlur={() => handleSaveRename(session.id)}
                          aria-label={`Rename chat session ${session.title}`}
                        />
                      </form>
                    ) : (
                      <span className="truncate text-xs font-medium">{session.title}</span>
                    )}
                  </div>

                  {!isEditing && (
                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 transition-opacity duration-150 shrink-0 ml-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-5 w-5 rounded-md hover:bg-background/80"
                        onClick={(e) => handleStartRename(session, e)}
                        aria-label={`Rename chat session ${session.title}`}
                      >
                        <Edit2 className="w-3 h-3" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-5 w-5 rounded-md hover:bg-destructive/10 hover:text-destructive"
                        onClick={(e) => handleDelete(session.id, e)}
                        aria-label={`Delete chat session ${session.title}`}
                      >
                        <Trash2 className="w-3 h-3" />
                      </Button>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Collapse Toggle Button */}
      <Button
        onClick={() => setIsOpen(!isOpen)}
        variant="ghost"
        size="icon"
        className={cn(
          "absolute -right-3 top-1/2 -translate-y-1/2 z-40 h-6 w-6 rounded-full border border-border bg-background shadow-md hover:bg-accent hover:text-accent-foreground",
          !isOpen && "right-auto -left-3 rotate-180"
        )}
        aria-label={isOpen ? "Collapse chat sessions sidebar" : "Expand chat sessions sidebar"}
        aria-expanded={isOpen}
      >
        <ChevronLeft className="w-3.5 h-3.5" />
      </Button>
    </div>
  );
}
