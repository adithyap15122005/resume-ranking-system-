"use client";

import { usePathname } from "next/navigation";
import { Bell, Moon, Sun, Search, ChevronDown } from "lucide-react";
import { useTheme } from "next-themes";
import { useAuthStore } from "@/store/auth";
import { useState } from "react";

const BREADCRUMBS: Record<string, string> = {
  "/dashboard": "Dashboard",
  "/candidates": "Candidates",
  "/jobs": "Jobs",
  "/rankings": "Rankings",
  "/pipeline": "Pipeline",
  "/analytics": "Analytics",
  "/training": "AI Training",
  "/assistant": "AI Assistant",
  "/settings": "Settings",
};

export function Topbar() {
  const pathname = usePathname();
  const { theme, setTheme } = useTheme();
  const { user, logout } = useAuthStore();
  const [showUserMenu, setShowUserMenu] = useState(false);

  const pageTitle = BREADCRUMBS[pathname] || "HireIQ";

  return (
    <header className="h-16 border-b border-slate-700/50 bg-slate-900/80 backdrop-blur-sm flex items-center px-6 gap-4 flex-shrink-0">
      {/* Breadcrumb */}
      <div className="flex-1">
        <div className="flex items-center gap-2 text-sm">
          <span className="text-slate-500">HireIQ</span>
          <span className="text-slate-600">/</span>
          <span className="text-white font-medium">{pageTitle}</span>
        </div>
      </div>

      {/* Search */}
      <div className="hidden md:flex items-center gap-2 bg-white/5 border border-white/10 rounded-xl px-3 py-2 w-64">
        <Search className="w-4 h-4 text-slate-500" />
        <input
          placeholder="Search... (⌘K)"
          className="bg-transparent text-sm text-slate-300 placeholder-slate-500 outline-none flex-1 w-full"
        />
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2">
        {/* Theme toggle */}
        <button
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          className="w-9 h-9 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 flex items-center justify-center text-slate-400 hover:text-white transition-all"
        >
          {theme === "dark" ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
        </button>

        {/* Notifications */}
        <button className="relative w-9 h-9 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 flex items-center justify-center text-slate-400 hover:text-white transition-all">
          <Bell className="w-4 h-4" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-indigo-500 rounded-full" />
        </button>

        {/* User dropdown */}
        <div className="relative">
          <button
            onClick={() => setShowUserMenu(!showUserMenu)}
            className="flex items-center gap-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl px-3 py-2 transition-all"
          >
            <div className="w-6 h-6 rounded-full bg-gradient-to-br from-indigo-400 to-violet-500 flex items-center justify-center text-white text-xs font-medium">
              {user?.full_name?.[0]?.toUpperCase() || "U"}
            </div>
            <span className="text-sm text-slate-300 hidden sm:block">{user?.full_name?.split(" ")[0]}</span>
            <ChevronDown className="w-3 h-3 text-slate-500" />
          </button>

          {showUserMenu && (
            <div className="absolute right-0 top-full mt-2 w-48 bg-slate-900 border border-slate-700 rounded-xl shadow-xl z-50 overflow-hidden">
              <div className="px-4 py-3 border-b border-slate-700">
                <div className="text-sm font-medium text-white">{user?.full_name}</div>
                <div className="text-xs text-slate-500 truncate">{user?.email}</div>
              </div>
              <div className="p-1">
                <button className="w-full text-left px-3 py-2 text-sm text-slate-300 hover:bg-white/5 rounded-lg transition-colors" onClick={() => setShowUserMenu(false)}>
                  Profile Settings
                </button>
                <button
                  onClick={() => { setShowUserMenu(false); logout(); }}
                  className="w-full text-left px-3 py-2 text-sm text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                >
                  Sign out
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
