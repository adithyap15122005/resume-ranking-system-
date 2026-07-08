"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  TrendingUp, Users, Briefcase, Target, BarChart2,
  PieChartIcon, Activity, Cpu,
} from "lucide-react";
import { analyticsApi } from "@/lib/api";
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, PieChart, Pie, Cell, Legend, LineChart, Line, AreaChart, Area,
} from "recharts";
import toast from "react-hot-toast";

const COLORS = ["#6366f1", "#8b5cf6", "#ec4899", "#f59e0b", "#10b981", "#3b82f6"];

interface DashboardStats {
  total_resumes: number;
  total_jobs: number;
  total_rankings: number;
  avg_match_score: number;
  pipeline_stages: Record<string, number>;
  top_skills: Array<{ skill: string; count: number }>;
  score_distribution: Record<string, number>;
  shortlisted_count: number;
}

interface SkillDemand {
  skill: string;
  jobs_requiring: number;
  candidates_having: number;
  demand_score: number;
}

export default function AnalyticsPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [funnel, setFunnel] = useState<Array<{ stage: string; count: number; conversion: number }>>([]);
  const [skillDemand, setSkillDemand] = useState<SkillDemand[]>([]);
  const [modelPerf, setModelPerf] = useState<{ accuracy?: number; f1?: number; models?: string[] } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      analyticsApi.dashboard(),
      analyticsApi.hiringFunnel().catch(() => []),
      analyticsApi.skillDemand().catch(() => []),
      analyticsApi.modelPerformance().catch(() => null),
    ])
      .then(([d, f, sd, mp]) => {
        setStats(d);
        setFunnel(Array.isArray(f) ? f : []);
        setSkillDemand(Array.isArray(sd) ? sd : []);
        setModelPerf(mp);
      })
      .catch(() => toast.error("Failed to load analytics"))
      .finally(() => setLoading(false));
  }, []);

  const scoreDistData = stats
    ? [
        { name: "Excellent (90+)", value: stats.score_distribution?.excellent || 0, color: "#10b981" },
        { name: "Strong (75–90)", value: stats.score_distribution?.strong || 0, color: "#6366f1" },
        { name: "Suitable (60–75)", value: stats.score_distribution?.suitable || 0, color: "#f59e0b" },
        { name: "Average (45–60)", value: stats.score_distribution?.average || 0, color: "#f97316" },
        { name: "Weak (<45)", value: stats.score_distribution?.not_recommended || 0, color: "#ef4444" },
      ]
    : [];

  const pipelineData = stats
    ? Object.entries(stats.pipeline_stages || {}).map(([stage, count]) => ({
        stage: stage.replace(/_/g, " "),
        count,
      }))
    : [];

  const StatCard = ({ title, value, sub, icon: Icon, color }: {
    title: string; value: string | number; sub: string;
    icon: React.ElementType; color: string;
  }) => (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-slate-900/80 border border-slate-700/50 rounded-2xl p-5"
    >
      <div className="flex items-center gap-3 mb-3">
        <div className={`w-9 h-9 rounded-xl bg-gradient-to-br ${color} flex items-center justify-center`}>
          <Icon className="w-4.5 h-4.5 text-white" />
        </div>
        <span className="text-sm text-slate-400">{title}</span>
      </div>
      <div className="text-3xl font-bold text-white">{value}</div>
      <div className="text-xs text-slate-500 mt-1">{sub}</div>
    </motion.div>
  );

  return (
    <div className="space-y-6 max-w-7xl">
      <div>
        <h1 className="text-2xl font-bold text-white">Analytics</h1>
        <p className="text-slate-400 text-sm mt-0.5">Comprehensive hiring intelligence insights</p>
      </div>

      {loading ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="bg-slate-900/80 border border-slate-700/50 rounded-2xl p-5 h-28 shimmer" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard title="Total Resumes" value={stats?.total_resumes ?? 0} sub="In talent pool" icon={Users} color="from-indigo-500 to-indigo-600" />
          <StatCard title="Open Jobs" value={stats?.total_jobs ?? 0} sub="Active positions" icon={Briefcase} color="from-violet-500 to-violet-600" />
          <StatCard title="Shortlisted" value={stats?.shortlisted_count ?? 0} sub="Ready for interview" icon={Target} color="from-emerald-500 to-teal-500" />
          <StatCard title="Avg Match Score" value={`${(stats?.avg_match_score ?? 0).toFixed(1)}%`} sub="Across all rankings" icon={TrendingUp} color="from-amber-500 to-orange-500" />
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Score Distribution */}
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2 }}
          className="bg-slate-900/80 border border-slate-700/50 rounded-2xl p-5">
          <div className="flex items-center gap-2 mb-4">
            <PieChartIcon className="w-4 h-4 text-indigo-400" />
            <h3 className="font-semibold text-white">Score Distribution</h3>
          </div>
          {scoreDistData.some((d) => d.value > 0) ? (
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie data={scoreDistData} cx="50%" cy="50%" outerRadius={100} innerRadius={55} paddingAngle={2} dataKey="value">
                  {scoreDistData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                </Pie>
                <Tooltip formatter={(v) => [`${v}`, "candidates"]}
                  contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 8, fontSize: 12 }} />
                <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 11 }} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-64 text-slate-600">
              <div className="text-center">
                <PieChartIcon className="w-12 h-12 mx-auto mb-2 opacity-30" />
                <p className="text-sm">No ranking data yet</p>
              </div>
            </div>
          )}
        </motion.div>

        {/* Pipeline Distribution */}
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 }}
          className="bg-slate-900/80 border border-slate-700/50 rounded-2xl p-5">
          <div className="flex items-center gap-2 mb-4">
            <BarChart2 className="w-4 h-4 text-violet-400" />
            <h3 className="font-semibold text-white">Pipeline Stages</h3>
          </div>
          {pipelineData.some((d) => d.count > 0) ? (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={pipelineData} margin={{ left: -20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="stage" tick={{ fontSize: 10, fill: "#64748b" }} />
                <YAxis tick={{ fontSize: 10, fill: "#64748b" }} allowDecimals={false} />
                <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 8, fontSize: 12 }}
                  labelStyle={{ color: "#94a3b8" }} />
                <Bar dataKey="count" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-64 text-slate-600">
              <div className="text-center">
                <BarChart2 className="w-12 h-12 mx-auto mb-2 opacity-30" />
                <p className="text-sm">No pipeline data yet</p>
              </div>
            </div>
          )}
        </motion.div>
      </div>

      {/* Hiring Funnel */}
      {funnel.length > 0 && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 }}
          className="bg-slate-900/80 border border-slate-700/50 rounded-2xl p-5">
          <div className="flex items-center gap-2 mb-4">
            <Activity className="w-4 h-4 text-emerald-400" />
            <h3 className="font-semibold text-white">Hiring Funnel</h3>
          </div>
          <div className="space-y-3">
            {funnel.map((item, i) => {
              const maxCount = funnel[0]?.count || 1;
              const pct = Math.round((item.count / maxCount) * 100);
              return (
                <div key={item.stage} className="flex items-center gap-4">
                  <span className="text-sm text-slate-400 w-28 flex-shrink-0 capitalize">
                    {item.stage.replace(/_/g, " ")}
                  </span>
                  <div className="flex-1 h-6 bg-slate-800 rounded-lg overflow-hidden relative">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${pct}%` }}
                      transition={{ delay: 0.5 + i * 0.05, duration: 0.6 }}
                      className="h-full rounded-lg"
                      style={{ background: `hsl(${240 - i * 25}, 70%, 60%)` }}
                    />
                    <span className="absolute inset-0 flex items-center justify-center text-xs font-medium text-white">
                      {item.count} ({item.conversion?.toFixed(0)}%)
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </motion.div>
      )}

      {/* Skill Demand */}
      {skillDemand.length > 0 && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }}
          className="bg-slate-900/80 border border-slate-700/50 rounded-2xl p-5">
          <div className="flex items-center gap-2 mb-4">
            <Cpu className="w-4 h-4 text-pink-400" />
            <h3 className="font-semibold text-white">Skill Demand vs Supply</h3>
          </div>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={skillDemand.slice(0, 10)} margin={{ left: -10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="skill" tick={{ fontSize: 10, fill: "#64748b" }} />
              <YAxis tick={{ fontSize: 10, fill: "#64748b" }} />
              <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 8, fontSize: 12 }} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Bar name="Jobs Requiring" dataKey="jobs_requiring" fill="#6366f1" radius={[3, 3, 0, 0]} />
              <Bar name="Candidates Having" dataKey="candidates_having" fill="#10b981" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </motion.div>
      )}

      {/* Top skills from pool */}
      {(stats?.top_skills?.length ?? 0) > 0 && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.6 }}
          className="bg-slate-900/80 border border-slate-700/50 rounded-2xl p-5">
          <h3 className="font-semibold text-white mb-4">Most Common Skills in Talent Pool</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
            {(stats?.top_skills ?? []).slice(0, 12).map((item, i) => {
              const max = stats!.top_skills[0].count;
              const pct = Math.round((item.count / max) * 100);
              return (
                <div key={item.skill} className="bg-slate-800/60 rounded-xl p-3">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-sm text-slate-300 truncate">{item.skill}</span>
                    <span className="text-xs text-slate-500 ml-1">{item.count}</span>
                  </div>
                  <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${pct}%` }}
                      transition={{ delay: 0.7 + i * 0.03, duration: 0.5 }}
                      className="h-full rounded-full"
                      style={{ background: COLORS[i % COLORS.length] }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </motion.div>
      )}

      {/* Model Performance */}
      {modelPerf && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.7 }}
          className="bg-slate-900/80 border border-slate-700/50 rounded-2xl p-5">
          <h3 className="font-semibold text-white mb-4">ML Model Performance</h3>
          <div className="grid grid-cols-2 gap-4">
            {modelPerf.accuracy !== undefined && (
              <div className="bg-slate-800/60 rounded-xl p-4 text-center">
                <div className="text-3xl font-bold text-indigo-400">{(modelPerf.accuracy * 100).toFixed(1)}%</div>
                <div className="text-sm text-slate-500 mt-1">Accuracy</div>
              </div>
            )}
            {modelPerf.f1 !== undefined && (
              <div className="bg-slate-800/60 rounded-xl p-4 text-center">
                <div className="text-3xl font-bold text-violet-400">{(modelPerf.f1 * 100).toFixed(1)}%</div>
                <div className="text-sm text-slate-500 mt-1">F1 Score</div>
              </div>
            )}
          </div>
          {modelPerf.models && (
            <div className="mt-3 text-xs text-slate-500">
              Models trained: {modelPerf.models.join(", ")}
            </div>
          )}
        </motion.div>
      )}
    </div>
  );
}
