"use client";

import { useAuth } from "@/lib/auth";
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
import { useState } from "react";

interface HeaderProps {
  sidebarOpen: boolean;
  onToggleSidebar: () => void;
  viewerOpen: boolean;
  onToggleViewer: () => void;
}

export default function Header({ sidebarOpen, onToggleSidebar, viewerOpen, onToggleViewer }: HeaderProps) {
  const { user, logout } = useAuth();
  const router = useRouter();
  const [isDark, setIsDark] = useState(true);

  const toggleTheme = () => {
    const html = document.documentElement;
    if (isDark) {
      html.classList.remove("dark");
      html.classList.add("light");
    } else {
      html.classList.remove("light");
      html.classList.add("dark");
    }
    setIsDark(!isDark);
  };

  const handleLogout = () => {
    logout();
    router.replace("/login");
  };

  return (
    <header className="h-14 flex items-center justify-between px-4 border-b border-border/50 bg-card/50 backdrop-blur-md flex-shrink-0 z-50">
      {/* Left */}
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={onToggleSidebar} title={sidebarOpen ? "Close sidebar" : "Open sidebar"}>
          {sidebarOpen ? <PanelLeftClose className="w-4 h-4" /> : <PanelLeftOpen className="w-4 h-4" />}
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
        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={onToggleViewer} title={viewerOpen ? "Close viewer" : "Open viewer"}>
          {viewerOpen ? <PanelRightClose className="w-4 h-4" /> : <PanelRightOpen className="w-4 h-4" />}
        </Button>

        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={toggleTheme} title={isDark ? "Light mode" : "Dark mode"}>
          {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
        </Button>

        <DropdownMenu>
          <DropdownMenuTrigger className="flex items-center h-8 gap-2 px-2 rounded-md hover:bg-accent transition-colors cursor-pointer">
            <Avatar className="w-6 h-6">
              <AvatarFallback className="text-[10px] bg-primary/20 text-primary">
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
  );
}
