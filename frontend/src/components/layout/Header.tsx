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
  Sun,
} from "lucide-react";
import { useSyncExternalStore } from "react";
import { useTheme } from "next-themes";
import ApiKeyManager from "@/components/auth/ApiKeyManager";


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
        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={onToggleViewer} title={viewerOpen ? t("header.closeViewer") : t("header.openViewer")}>
          {viewerOpen ? <PanelRightClose className="w-4 h-4" /> : <PanelRightOpen className="w-4 h-4" />}
        </Button>

        {mounted && (
          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={toggleTheme} title={isDark ? t("header.lightMode") : t("header.darkMode")}>
            {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </Button>
        )}

        <select
          aria-label={t("common.language")}
          value={i18n.resolvedLanguage || "en"}
          onChange={(e) => void i18n.changeLanguage(e.target.value)}
          className="h-8 rounded-md border border-border bg-background px-2 text-xs text-foreground"
        >
          <option value="en">{languageLabel("en")}</option>
          <option value="hi">{languageLabel("hi")}</option>
          <option value="es">{languageLabel("es")}</option>
          <option value="fr">{languageLabel("fr")}</option>
        </select>

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
            <ApiKeyManager />
            <DropdownMenuSeparator />
            <DropdownMenuItem className="text-destructive cursor-pointer" onClick={handleLogout}>
              <LogOut className="w-4 h-4 mr-2" />
              {t("header.signOut")}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}