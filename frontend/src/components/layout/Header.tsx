"use client";

import { useAuth } from "@/lib/auth";
import { useTranslation } from "react-i18next";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Brain,
  PanelLeftClose,
  PanelLeftOpen,
  PanelRightClose,
  PanelRightOpen,
  LogOut,
  Moon,
  Shield,
  Sun,
  Settings,
} from "lucide-react";
import { useSyncExternalStore, useState } from "react";
import { useTheme } from "next-themes";
import ApiKeyManager from "@/components/auth/ApiKeyManager";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useEffect } from "react";


interface HeaderProps {
  sidebarOpen: boolean;
  onToggleSidebar: () => void;
  viewerOpen: boolean;
  onToggleViewer: () => void;
}

const subscribe = () => () => {};
const getSnapshot = () => true;
const getServerSnapshot = () => false;

export default function Header({ sidebarOpen, onToggleSidebar, viewerOpen, onToggleViewer }: HeaderProps) {
  const { user, logout } = useAuth();
  const { t, i18n } = useTranslation();
  const router = useRouter();
  const { theme, setTheme } = useTheme();
  const mounted = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot); // ← replaces useState + useEffect
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [temperature, setTemperature] = useState(0.5);
  useEffect(() => {
    const saved = localStorage.getItem("temperature");
    if (saved) {
      setTemperature(Number(saved));
    }
  }, []);

  useEffect(() => {
    localStorage.setItem("temperature", temperature.toString());
  }, [temperature]);

  const isDark = theme === "dark";
  const toggleTheme = () => setTheme(isDark ? "light" : "dark");

  const handleLogout = () => {
    logout();
    router.replace("/login");
  };

  const languageLabel = (language: string) => {
    switch (language) {
      case "hi":
        return t("common.hindi");
      case "es":
        return t("common.spanish");
      case "fr":
        return t("common.french");
      default:
        return t("common.english");
    }
  };

  return (
    <header className="h-14 flex items-center justify-between px-4 border-b border-border/50 bg-card/50 backdrop-blur-md flex-shrink-0 z-50">
      {/* Left */}
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={onToggleSidebar} title={sidebarOpen ? t("header.closeSidebar") : t("header.openSidebar")}>
          {sidebarOpen ? <PanelLeftClose className="w-4 h-4" /> : <PanelLeftOpen className="w-4 h-4" />}
        </Button>

        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-primary/15 flex items-center justify-center">
            <Brain className="w-4 h-4 text-primary" />
          </div>
          <span className="font-semibold text-sm hidden sm:inline">{t("common.appName")}</span>
        </div>
      </div>

      {/* Right */}
      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={onToggleViewer}
          title={viewerOpen ? "Close Viewer" : "Open Viewer"}
        >
          {viewerOpen ? (
            <PanelRightClose className="w-4 h-4" />
          ) : (
            <PanelRightOpen className="w-4 h-4" />
          )}
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={() => setSettingsOpen(true)}
        >
          <Settings className="w-4 h-4" />
        </Button>

        <DropdownMenu>
          <DropdownMenuTrigger
            render={
              <button className="flex items-center h-8 gap-2 px-2 rounded-md hover:bg-accent transition-colors cursor-pointer">
                <Avatar className="w-6 h-6">
                  <AvatarFallback className="text-[10px] bg-primary/20 text-primary">
                    {user?.username?.slice(0, 2).toUpperCase() || "U"}
                  </AvatarFallback>
                </Avatar>
                <span className="text-sm hidden sm:inline">{user?.username}</span>
              </button>
            }
          />

          <DropdownMenuContent align="end" className="w-56">
            <div className="px-3 py-2">
              <p className="text-sm font-medium">{user?.username}</p>
              <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
            </div>
            <DropdownMenuSeparator />
            {user?.is_admin && (
              <DropdownMenuItem className="cursor-pointer" onClick={() => router.push("/admin")}>
                <Shield className="w-4 h-4 mr-2" />
                Admin metrics
              </DropdownMenuItem>
            )}
            {user?.is_admin && <DropdownMenuSeparator />}
            <DropdownMenuItem className="text-destructive cursor-pointer" onClick={handleLogout}>
              <LogOut className="w-4 h-4 mr-2" />
              {t("header.signOut")}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
      <Dialog
        open={settingsOpen}
        onOpenChange={setSettingsOpen}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              LLM Settings
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-4">
            <label className="text-sm">
              Temperature: {temperature}
            </label>

            <input
              type="range"
              min="0"
              max="1"
              step="0.1"
              value={temperature}
              onChange={(e) =>
                setTemperature(Number(e.target.value))
              }
              className="w-full"
            />
          </div>
        </DialogContent>
      </Dialog>
    </header>
  );
}