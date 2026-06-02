"use client";

import { useState } from "react";
import { useAuth } from "@/lib/auth";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  DropdownMenuSub,
  DropdownMenuSubTrigger,
  DropdownMenuSubContent,
  DropdownMenuPortal,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
} from "@/components/ui/dropdown-menu";
import {
  Brain,
  PanelLeftClose,
  PanelLeftOpen,
  PanelRightClose,
  PanelRightOpen,
  LogOut,
  Menu,
  X,
  Palette,
  Briefcase, 
  ChevronDown
} from "lucide-react";
import { useWorkspaceStore, WORKSPACES, type WorkspaceId } from "@/store/workspace-store";
import { api } from "@/lib/api";
import { useTheme } from "next-themes";

import { useSyncExternalStore } from "react";

interface HeaderProps {
  sidebarOpen: boolean;
  onToggleSidebar: () => void;
  viewerOpen: boolean;
  onToggleViewer: () => void;
  /** Pass DocumentSidebar JSX so the mobile sheet can render it */
  mobileSheetContent?: React.ReactNode;
}

const subscribe = () => () => {};
const getSnapshot = () => true;
const getServerSnapshot = () => false;

export default function Header({
  sidebarOpen,
  onToggleSidebar,
  viewerOpen,
  onToggleViewer,
  mobileSheetContent,
}: HeaderProps) {
  const { user, logout } = useAuth();
  const router = useRouter();
  const { theme, setTheme } = useTheme();
  const mounted = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
  const [sheetOpen, setSheetOpen] = useState(false);
  const [workspaceLoading, setWorkspaceLoading] = useState(false);
  const workspace = useWorkspaceStore((s) => s.workspace);
  const setWorkspace = useWorkspaceStore((s) => s.setWorkspace);

  const currentWorkspaceLabel = WORKSPACES.find((w) => w.id === workspace)?.label ?? workspace;
  const isDark = theme === "dark";
  const toggleTheme = () => setTheme(isDark ? "light" : "dark");

  const handleLogout = () => {
    logout();
    router.replace("/login");
  };

  const fetchDocumentsForWorkspace = async (id: string) => {
    // Placeholder: simulate fetching documents for the selected workspace
    setWorkspaceLoading(true);
    try {
      // Attempt a real API call if available; otherwise this will fail silently
      const res = await api.get(`/api/v1/documents?workspace=${encodeURIComponent(id)}`).catch(() => null);
      console.log("workspace change, fetched documents:", res);
      // Here you would dispatch the results into your document store or context
      // e.g. documentStore.setDocuments(res || [])
    } catch (err) {
      console.warn("Failed to fetch documents for workspace", id, err);
    } finally {
      setWorkspaceLoading(false);
    }
  };

  return (
    <>
      <header className="h-14 flex items-center justify-between px-4 border-b border-border/50 bg-card/50 backdrop-blur-md flex-shrink-0 z-50">
        {/* Left */}
        <div className="flex items-center gap-3">
          {/* Hamburger - mobile only */}
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 md:hidden"
            onClick={() => setSheetOpen(true)}
            title="Open sidebar"
            aria-label="Open document navigation"
            aria-expanded={sheetOpen}
            aria-controls="mobile-document-navigation"
          >
            <Menu className="w-4 h-4" />
          </Button>

          {/* Desktop sidebar toggle - hidden on mobile */}
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 hidden md:inline-flex"
            onClick={onToggleSidebar}
            title={sidebarOpen ? "Close sidebar" : "Open sidebar"}
            aria-label={sidebarOpen ? "Close document sidebar" : "Open document sidebar"}
            aria-pressed={sidebarOpen}
          >
            {sidebarOpen ? (
              <PanelLeftClose className="w-4 h-4" />
            ) : (
              <PanelLeftOpen className="w-4 h-4" />
            )}
          </Button>

          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-primary/15 flex items-center justify-center">
              <Brain className="w-4 h-4 text-primary" />
            </div>
            <span className="font-semibold text-sm hidden sm:inline">Document AI Analyst</span>
          </div>
        </div>

        {/* Right */}
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={onToggleViewer}
            title={viewerOpen ? "Close viewer" : "Open viewer"}
            aria-label={viewerOpen ? "Close PDF viewer" : "Open PDF viewer"}
            aria-pressed={viewerOpen}
          >
            {viewerOpen ? (
              <PanelRightClose className="w-4 h-4" />
            ) : (
              <PanelRightOpen className="w-4 h-4" />
            )}
          </Button>

          {mounted && (
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={toggleTheme}
              title={isDark ? "Light mode" : "Dark mode"}
              aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
            >
              {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </Button>
          )}

          {/* Workspace switcher */}
          <DropdownMenu>
            <DropdownMenuTrigger
              className="flex items-center h-8 gap-2 px-2 rounded-md hover:bg-accent transition-colors cursor-pointer"
              aria-label={`Select workspace. Current workspace: ${currentWorkspaceLabel}`}
              aria-busy={workspaceLoading}
            >
              {workspaceLoading ? (
                <>
                  <Skeleton className="h-4 w-4 rounded-sm" />
                  <Skeleton className="hidden h-4 w-16 sm:block" />
                </>
              ) : (
                <>
                  <Briefcase className="w-4 h-4" />
                  <span className="text-sm hidden sm:inline">{currentWorkspaceLabel}</span>
                  <ChevronDown className="w-3 h-3" />
                </>
              )}
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-40">
              {WORKSPACES.map((w) => (
                <DropdownMenuItem
                  key={w.id}
                  className={`cursor-pointer ${w.id === workspace ? "font-medium" : ""}`}
                  onClick={async () => {
                    setWorkspace(w.id as WorkspaceId);
                    await fetchDocumentsForWorkspace(w.id);
                  }}
                >
                  {w.label}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>

          <DropdownMenu>
            <DropdownMenuTrigger
              className="flex items-center h-8 gap-2 px-2 rounded-md hover:bg-accent transition-colors cursor-pointer"
              aria-label={`Open user menu for ${user?.username ?? "current user"}`}
            >
              <Avatar className="w-6 h-6">
                <AvatarFallback className="text-[10px] bg-primary text-primary-foreground">
                  {user?.username?.slice(0, 2).toUpperCase() || "U"}
                </AvatarFallback>
              </Avatar>
              <span className="text-sm hidden sm:inline">{user?.username}</span>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48">
              <div className="px-3 py-2">
                <p className="text-sm font-medium">{user?.username}</p>
                <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
              </div>
              <DropdownMenuSeparator />
              <DropdownMenuItem className="text-destructive cursor-pointer" onClick={handleLogout}>
                <LogOut className="w-4 h-4 mr-2" />
                Sign out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </header>

      {/* Mobile navigation sheet */}
      {sheetOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm md:hidden"
          onClick={() => setSheetOpen(false)}
          aria-hidden="true"
        />
      )}

      <aside
        id="mobile-document-navigation"
        className={[
          "fixed inset-y-0 left-0 z-50 w-72 flex flex-col",
          "bg-sidebar border-r border-sidebar-border",
          "transform transition-transform duration-300 ease-in-out md:hidden",
          sheetOpen ? "translate-x-0" : "-translate-x-full",
        ].join(" ")}
        aria-label="Mobile navigation"
        aria-hidden={!sheetOpen}
        inert={!sheetOpen ? true : undefined}
      >
        <div className="h-14 flex items-center justify-between px-4 border-b border-sidebar-border flex-shrink-0">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-primary/15 flex items-center justify-center">
              <Brain className="w-4 h-4 text-primary" />
            </div>
            <span className="font-semibold text-sm">Document AI Analyst</span>
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={() => setSheetOpen(false)}
            aria-label="Close navigation"
          >
            <X className="w-4 h-4" />
          </Button>
        </div>

        <div className="flex-1 overflow-hidden">{sheetOpen ? mobileSheetContent : null}</div>
      </aside>
    </>
  );
}
