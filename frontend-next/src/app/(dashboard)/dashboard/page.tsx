"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  Users, Briefcase, Trophy, TrendingUp, Brain, Zap,
  ArrowUpRight, ArrowDownRight, Target, ChevronRight,
  Star, Clock,
} from "lucide-react";
import { analyticsApi } from "@/lib/api";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, Legend, LineChart, Line,
} from "recharts";
import Link from "next/link";
import { useAuthStore } from "@/store/auth";
import toast from "react-hot-toast";

const COLORS = ["#6366f1", "#8b5cf6", "#a78bfa", "#c4b5fd", "#ddd6fe"];

interface DashboardData {
  total_resumes: number;
  total_jobs: number;
  total_rankings: number;
  avg_match_score: number;
  pipeline_stages: Record<string, number>;
  top_skills: Array<{ skill: string; count: number }>;
  score_distribution: Record<string, number>;
  shortlisted_count: number;
  hired_count: number;
  offer_extended: number;
}

function StatCard({
  title, value, subtitle, icon: Icon, color, trend, link,
}: {
  title: string;
  value: string | number;
  subtitle: string;
  icon: React.ElementType;
  color: string;
  trend?: { value: number; positive: boolean };
  link?: string;
}) {
  const card = (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -2 }}
      className="bg-slate-900/80 border border-slate-700/50 rounded-2xl p-5 hover:border-slate-600/50 transition-all cursor-pointer"
    >
      <div className="flex items-start justify-between">
        <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${color} flex items-center justify-center`}>
          <Icon className="w-5 h-5 text-white" />
        </div>
        {trend && (
          <div className={`flex items-center gap-1 text-xs font-medium ${trend.positive ? "text-emerald-400" : "text-red-400"}`}>
            {trend.positive ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
            {Math.abs(trend.value)}%
          </div>
        )}
      </div>
      <div className="mt-4">
        <div className="text-2xl font-bold text-white">{value}</div>
        <div className="text-sm font-medium text-slate-400 mt-0.5">{title}</div>
        <div className="text-xs text-slate-600 mt-1">{subtitle}</div>
      </div>
    </motion.div>
  );
  return link ? <Link href={link}>{card}</Link> : card;
}

export default function DashboardPage() {
  const { user } = useAuthStore();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    analyticsApi
      .dashboard()
      .then(setData)
      .catch(() => toast.error("Failed to load dashboard"))
      .finally(() => setLoading(false));
  }, []);

  const scoreDistData = data
    ? [
        { name: "Excellent", value: data.score_distribution.excellent, color: "#10b981" },
        { name: "Strong", value: data.score_distribution.strong, color: "#6366f1" },
        { name: "Suitable", value: data.score_distribution.suitable, color: "#f59e0b" },
        { name: "Average", value: data.score_distribution.average, color: "#f97316" },
        { name: "Weak", value: data.score_distribution.not_recommended, color: "#ef4444" },
      ]
    : [];

  const pipelineData = data
    ? Object.entries(data.pipeline_stages).map(([stage, count]) => ({
        stage: stage.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase()),
        count,
      }))
    : [];

  return (
    <div className="space-y-6 max-w-7xl">
      {/* Welcome banner */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="relative overflow-hidden bg-gradient-to-r from-indigo-600 via-violet-600 to-purple-600 rounded-2xl p-6 text-white"
      >
        <div className="absolute inset-0 bg-grid opacity-10" />
        <div className="relative z-10 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">
              Good {new Date().getHours() < 12 ? "morning" : new Date().getHours() < 17 ? "afternoon" : "evening"},
              {" "}{user?.full_name?.split(" ")[0] || "Recruiter"} 👋
            </h1>
            <p className="text-indigo-200 mt-1 text-sm">
              Here&apos;s what&apos;s happening with your hiring pipeline today.
            </p>
          </div>
          <div className="hidden md:flex items-center gap-3">
            <Link
              href="/candidates"
              className="bg-white/20 hover:bg-white/30 border border-white/20 rounded-xl px-4 py-2 text-sm font-medium transition-all flex items-center gap-2"
            >
              <Users className="w-4 h-4" />
              Upload Resumes
            </Link>
            <Link
              href="/jobs"
              className="bg-white text-indigo-700 hover:bg-indigo-50 rounded-xl px-4 py-2 text-sm font-medium transition-all flex items-center gap-2"
            >
              <Briefcase className="w-4 h-4" />
              Post a Job
            </Link>
          </div>
        </div>
        <div className="absolute -right-8 -top-8 w-32 h-32 bg-white/5 rounded-full" />
        <div className="absolute -right-4 -bottom-4 w-20 h-20 bg-white/5 rounded-full" />
      </motion.div>

      {/* Stat cards */}
      {loading ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="bg-slate-900/80 border border-slate-700/50 rounded-2xl p-5 h-32 shimmer" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            title="Total Resumes"
            value={data?.total_resumes ?? 0}
            subtitle="Candidates in database"
            icon={Users}
            color="from-indigo-500 to-indigo-600"
            trend={{ value: 12, positive: true }}
            link="/candidates"
          />
          <StatCard
            title="Active Jobs"
            value={data?.total_jobs ?? 0}
            subtitle="Open positions"
            icon={Briefcase}
            color="from-violet-500 to-violet-600"
            trend={{ value: 5, positive: true }}
            link="/jobs"
          />
          <StatCard
            title="Ranking Sessions"
            value={data?.total_rankings ?? 0}
            subtitle="Candidates ranked"
            icon={Trophy}
            color="from-amber-500 to-orange-500"
            link="/rankings"
          />
          <StatCard
            title="Avg Match Score"
            value={`${(data?.avg_match_score ?? 0).toFixed(1)}%`}
            subtitle="Across all rankings"
            icon={Target}
            color="from-emerald-500 to-teal-500"
            trend={{ value: 3, positive: true }}
          />
        </div>
      )}

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Score distribution pie */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-slate-900/80 border border-slate-700/50 rounded-2xl p-5"
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-white">Score Distribution</h3>
            <span className="text-xs text-slate-500 bg-slate-800 px-2 py-1 rounded-lg">All candidates</span>
          </div>
          {scoreDistData.some((d) => d.value > 0) ? (
            <ResponsiveContainer width="100%" height={240}>
              <PieChart>
                <Pie
                  data={scoreDistData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={3}
                  dataKey="value"
                >
                  {scoreDistData.map((entry, i) => (
                    <Cell key={i} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip formatter={(v) => [`${v} candidates`, ""]} />
                <Legend iconType="circle" iconSize={8} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-60 text-slate-500">
              <div className="text-center">
                <Brain className="w-10 h-10 mx-auto mb-2 opacity-30" />
                <p className="text-sm">No ranking data yet</p>
                <Link href="/jobs" className="text-xs text-indigo-400 hover:text-indigo-300 mt-1 block">
                  Rank candidates →
                </Link>
              </div>
            </div>
          )}
        </motion.div>

        {/* Pipeline stages bar */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.3 }}
          className="bg-slate-900/80 border border-slate-700/50 rounded-2xl p-5"
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-white">Hiring Pipeline</h3>
            <Link href="/pipeline" className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1">
              View Kanban <ChevronRight className="w-3 h-3" />
            </Link>
          </div>
          {pipelineData.some((d) => d.count > 0) ? (
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={pipelineData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="stage" tick={{ fontSize: 10, fill: "#64748b" }} />
                <YAxis tick={{ fontSize: 10, fill: "#64748b" }} />
                <Tooltip
                  contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 8, fontSize: 12 }}
                  labelStyle={{ color: "#94a3b8" }}
                />
                <Bar dataKey="count" fill="#6366f1" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-60 text-slate-500">
              <div className="text-center">
                <Trophy className="w-10 h-10 mx-auto mb-2 opacity-30" />
                <p className="text-sm">No pipeline data yet</p>
              </div>
            </div>
          )}
        </motion.div>
      </div>

      {/* Top skills + Quick actions */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Top skills */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="lg:col-span-2 bg-slate-900/80 border border-slate-700/50 rounded-2xl p-5"
        >
          <h3 className="font-semibold text-white mb-4">Top Skills in Talent Pool</h3>
          <div className="space-y-3">
            {(data?.top_skills ?? []).slice(0, 8).map((item, i) => {
              const max = data?.top_skills?.[0]?.count ?? 1;
              const pct = Math.round((item.count / max) * 100);
              return (
                <div key={item.skill} className="flex items-center gap-3">
                  <span className="text-xs text-slate-500 w-4">{i + 1}</span>
                  <span className="text-sm text-slate-300 w-28 truncate">{item.skill}</span>
                  <div className="flex-1 h-2 bg-slate-800 rounded-full overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${pct}%` }}
                      transition={{ delay: 0.5 + i * 0.05, duration: 0.6 }}
                      className="h-full bg-gradient-to-r from-indigo-500 to-violet-500 rounded-full"
                    />
                  </div>
                  <span className="text-xs text-slate-500 w-8 text-right">{item.count}</span>
                </div>
              );
            })}
            {!data?.top_skills?.length && (
              <div className="text-center py-8 text-slate-500">
                <p className="text-sm">Upload resumes to see skill analytics</p>
              </div>
            )}
          </div>
        </motion.div>

        {/* Quick actions */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="bg-slate-900/80 border border-slate-700/50 rounded-2xl p-5 space-y-3"
        >
          <h3 className="font-semibold text-white mb-1">Quick Actions</h3>
          {[
            { label: "Upload Resumes", icon: Users, href: "/candidates", color: "from-indigo-500 to-indigo-600" },
            { label: "Post New Job", icon: Briefcase, href: "/jobs", color: "from-violet-500 to-violet-600" },
            { label: "Run AI Ranking", icon: Zap, href: "/rankings", color: "from-amber-500 to-orange-500" },
            { label: "AI Assistant", icon: Brain, href: "/assistant", color: "from-emerald-500 to-teal-500" },
            { label: "View Analytics", icon: TrendingUp, href: "/analytics", color: "from-pink-500 to-rose-500" },
          ].map(({ label, icon: Icon, href, color }) => (
            <Link key={href} href={href}>
              <div className="flex items-center gap-3 p-3 rounded-xl bg-slate-800/50 hover:bg-slate-800 border border-slate-700/50 hover:border-slate-600 transition-all group">
                <div className={`w-8 h-8 rounded-lg bg-gradient-to-br ${color} flex items-center justify-center`}>
                  <Icon className="w-4 h-4 text-white" />
                </div>
                <span className="text-sm text-slate-300 group-hover:text-white transition-colors">{label}</span>
                <ChevronRight className="w-4 h-4 text-slate-600 group-hover:text-slate-400 ml-auto transition-colors" />
              </div>
            </Link>
          ))}
        </motion.div>
      </div>
    </div>
  );
}
