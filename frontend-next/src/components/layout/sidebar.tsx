"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  Brain, LayoutDashboard, Users, Briefcase, Trophy, Kanban,
  BarChart3, ChevronLeft, ChevronRight, MessageSquare, Settings,
  LogOut, FlaskConical, Database, ShieldCheck,
} from "lucide-react";
import { useAuthStore } from "@/store/auth";
import { getRoleLabel } from "@/lib/auth";

// Items visible to all roles
const COMMON_NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/candidates", label: "Candidates", icon: Users },
  { href: "/jobs", label: "Jobs", icon: Briefcase },
  { href: "/rankings", label: "Rankings", icon: Trophy },
  { href: "/pipeline", label: "Pipeline", icon: Kanban },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/assistant", label: "AI Assistant", icon: MessageSquare },
  { href: "/settings", label: "Settings", icon: Settings },
];

// Admin-only items
const ADMIN_NAV = [
  { href: "/training", label: "ML Console", icon: FlaskConical },
];

function getNavItems(role?: string) {
  if (role === "admin" || role === "hr_manager") {
    return [
      ...COMMON_NAV.slice(0, 6),
      ...ADMIN_NAV,
      ...COMMON_NAV.slice(6),
    ];
  }
  return COMMON_NAV;
}

export function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuthStore();
  const [collapsed, setCollapsed] = useState(false);

  const isActive = (href: string) =>
    href === "/dashboard" ? pathname === "/dashboard" : pathname.startsWith(href);

  const navItems = getNavItems(user?.role);
  const isAdmin = user?.role === "admin" || user?.role === "hr_manager";

  return (
    <motion.aside
      animate={{ width: collapsed ? 72 : 260 }}
      transition={{ duration: 0.2, ease: "easeInOut" }}
      className="relative flex flex-col h-full bg-slate-900/95 backdrop-blur-xl border-r border-slate-700/50 overflow-hidden flex-shrink-0"
    >
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-5 border-b border-slate-700/50">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-glow flex-shrink-0">
          <Brain className="w-5 h-5 text-white" />
        </div>
        <AnimatePresence>
          {!collapsed && (
            <motion.div
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -10 }}
              transition={{ duration: 0.15 }}
            >
              <div className="font-bold text-white text-lg leading-none">HireIQ</div>
              <div className="text-xs text-slate-500 mt-0.5">
                {isAdmin ? "Admin Console" : "Recruiter View"}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {navItems.map(({ href, label, icon: Icon }) => (
          <Link key={href} href={href}>
            <div
              className={`${isActive(href) ? "sidebar-item-active" : "sidebar-item-inactive"} ${collapsed ? "justify-center" : ""}`}
              title={collapsed ? label : undefined}
            >
              <Icon className={`flex-shrink-0 ${collapsed ? "w-5 h-5" : "w-4 h-4"}`} />
              <AnimatePresence>
                {!collapsed && (
                  <motion.span
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -8 }}
                    transition={{ duration: 0.15 }}
                    className="truncate"
                  >
                    {label}
                  </motion.span>
                )}
              </AnimatePresence>
            </div>
          </Link>
        ))}
      </nav>

      {/* User section */}
      <div className="px-3 py-4 border-t border-slate-700/50">
        {user && (
          <div className={`flex items-center gap-3 px-2 py-2 rounded-xl ${collapsed ? "justify-center" : ""}`}>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-white text-sm font-medium flex-shrink-0 ${
              isAdmin
                ? "bg-gradient-to-br from-amber-400 to-orange-500"
                : "bg-gradient-to-br from-indigo-400 to-violet-500"
            }`}>
              {isAdmin ? <ShieldCheck className="w-4 h-4" /> : (user.full_name?.[0]?.toUpperCase() || "U")}
            </div>
            <AnimatePresence>
              {!collapsed && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="flex-1 min-w-0"
                >
                  <div className="text-sm font-medium text-white truncate">{user.full_name}</div>
                  <div className={`text-xs truncate ${isAdmin ? "text-amber-500" : "text-slate-500"}`}>
                    {getRoleLabel(user.role)}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
            <AnimatePresence>
              {!collapsed && (
                <motion.button
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  onClick={() => logout()}
                  className="text-slate-500 hover:text-red-400 transition-colors flex-shrink-0"
                  title="Logout"
                >
                  <LogOut className="w-4 h-4" />
                </motion.button>
              )}
            </AnimatePresence>
          </div>
        )}
      </div>

      {/* Collapse toggle */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="absolute -right-3 top-1/2 -translate-y-1/2 w-6 h-6 bg-slate-800 border border-slate-600 rounded-full flex items-center justify-center text-slate-400 hover:text-white transition-colors z-10"
      >
        {collapsed ? <ChevronRight className="w-3 h-3" /> : <ChevronLeft className="w-3 h-3" />}
      </button>
    </motion.aside>
  );
}
