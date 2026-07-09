"use client";

import { useCallback, useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Trophy, Search, Zap, CheckCircle, XCircle, AlertCircle,
  Brain, TrendingUp, Award, Loader2, ChevronDown, Target,
  Sparkles, SlidersHorizontal,
} from "lucide-react";
import { jobApi } from "@/lib/api";
import toast from "react-hot-toast";

// Matches backend RankingOut exactly
interface RankingResult {
  id: string;
  rank: number;
  resume_id: string;
  job_id: string;
  // 0–100
  similarity_score: number;
  // 0–1 component scores
  semantic_score: number;
  skill_score: number;
  experience_score: number;
  hiring_probability: number;
  technical_score: number;
  experience_contribution: number;
  pipeline_stage: string;
  is_shortlisted: boolean;
  recommendation?: string;
  matched_skills: string[];
  missing_skills: string[];
  extra_skills: string[];
  shap_values?: {
    semantic_match?: number;
    skill_match?: number;
    experience?: number;
    skills?: Record<string, number>;
    ranking_mode?: string;
    feature_shap?: Record<string, number>;
  };
  ai_interview_questions?: string[];
  candidate_name?: string;
  candidate_email?: string;
  candidate_skills: string[];
}

interface Job {
  id: string;
  title: string;
  status: string;
  required_skills: string[];
}

function pct(value: number | undefined | null): string {
  const v = typeof value === "number" && isFinite(value) ? value : 0;
  return `${Math.round(v * 100)}%`;
}

function pct100(value: number | undefined | null): string {
  const v = typeof value === "number" && isFinite(value) ? value : 0;
  return `${Math.round(v)}%`;
}

function safeWidth(value: number | undefined | null): string {
  const v = typeof value === "number" && isFinite(value) ? Math.min(Math.max(value, 0), 1) : 0;
  return `${v * 100}%`;
}

function ScoreColor(score100: number) {
  if (score100 >= 85) return "text-emerald-400";
  if (score100 >= 70) return "text-indigo-400";
  if (score100 >= 55) return "text-amber-400";
  return "text-red-400";
}

function RankBadge({ rank }: { rank: number }) {
  if (rank === 1) return <span className="font-bold text-sm">🥇</span>;
  if (rank === 2) return <span className="font-bold text-sm">🥈</span>;
  if (rank === 3) return <span className="font-bold text-sm">🥉</span>;
  return <span className="text-slate-500 text-xs font-medium">#{rank}</span>;
}

function ScoreBar({
  label, value, color,
}: { label: string; value: number; color: string }) {
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-slate-500">{label}</span>
        <span className="text-slate-300 font-medium">{pct(value)}</span>
      </div>
      <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: safeWidth(value) }}
          transition={{ duration: 0.6, ease: "easeOut" }}
          className={`h-full rounded-full ${color}`}
        />
      </div>
    </div>
  );
}

export default function RankingsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selectedJob, setSelectedJob] = useState<string>("");
  const [rankings, setRankings] = useState<RankingResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [ranking, setRanking] = useState(false);
  const [search, setSearch] = useState("");
  const [detailId, setDetailId] = useState<string | null>(null);
  const [jobsLoading, setJobsLoading] = useState(true);
  const [rankingMode, setRankingMode] = useState<"traditional" | "semantic" | "ml" | "hybrid">("hybrid");

  // Threshold state
  const [threshold, setThreshold] = useState<number>(70);
  const [showThreshold, setShowThreshold] = useState<boolean>(false);
  const [applyingThreshold, setApplyingThreshold] = useState(false);

  useEffect(() => {
    jobApi.list()
      .then((data) => {
        const list = Array.isArray(data) ? data : [];
        setJobs(list);
        if (list.length > 0) setSelectedJob(list[0].id);
      })
      .catch(() => toast.error("Failed to load jobs"))
      .finally(() => setJobsLoading(false));
  }, []);

  const fetchRankings = useCallback(async (jobId: string) => {
    if (!jobId) return;
    setLoading(true);
    try {
      const data = await jobApi.getRankings(jobId);
      setRankings(Array.isArray(data) ? data : []);
    } catch {
      toast.error("Failed to load rankings");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selectedJob) fetchRankings(selectedJob);
  }, [selectedJob, fetchRankings]);

  // Auto-shortlist candidates above threshold
  const applyThresholdShortlist = async (
    results: RankingResult[],
    jobId: string,
    thresh: number
  ) => {
    const eligible = results.filter(
      (r) =>
        (r.similarity_score || 0) >= thresh &&
        !r.is_shortlisted &&
        r.pipeline_stage !== "rejected"
    );
    if (eligible.length === 0) return 0;
    await Promise.all(
      eligible.map((r) =>
        jobApi.movePipeline(jobId, r.resume_id, "shortlisted").catch(() => {})
      )
    );
    return eligible.length;
  };

  const handleRun = async () => {
    if (!selectedJob) return;
    setRanking(true);
    try {
      const results: RankingResult[] = await jobApi.rank(selectedJob, 0, rankingMode);
      toast.success(`AI ranked ${results.length} candidates!`);

      // Auto-shortlist above threshold
      const count = await applyThresholdShortlist(results, selectedJob, threshold);
      if (count > 0) {
        toast.success(
          `Auto-shortlisted ${count} candidate${count !== 1 ? "s" : ""} scoring ≥ ${threshold}%`,
          { icon: "✅", duration: 4000 }
        );
      }

      await fetchRankings(selectedJob);
    } catch {
      toast.error("Ranking failed");
    } finally {
      setRanking(false);
    }
  };

  // Apply threshold to already-loaded rankings (without re-ranking)
  const handleApplyThreshold = async () => {
    if (!selectedJob || rankings.length === 0) return;
    setApplyingThreshold(true);
    try {
      const count = await applyThresholdShortlist(rankings, selectedJob, threshold);
      if (count > 0) {
        toast.success(
          `Auto-shortlisted ${count} candidate${count !== 1 ? "s" : ""} scoring ≥ ${threshold}%`,
          { icon: "✅" }
        );
        await fetchRankings(selectedJob);
      } else {
        toast(`No unshortlisted candidates above ${threshold}%`, { icon: "ℹ️" });
      }
    } catch {
      toast.error("Failed to apply threshold");
    } finally {
      setApplyingThreshold(false);
    }
  };

  const handleShortlist = async (resultId: string, resumeId: string) => {
    try {
      await jobApi.movePipeline(selectedJob, resumeId, "shortlisted");
      setRankings((prev) =>
        prev.map((r) =>
          r.id === resultId ? { ...r, pipeline_stage: "shortlisted", is_shortlisted: true } : r
        )
      );
      toast.success("Candidate shortlisted!");
    } catch { toast.error("Failed"); }
  };

  const handleReject = async (resultId: string, resumeId: string) => {
    try {
      await jobApi.movePipeline(selectedJob, resumeId, "rejected");
      setRankings((prev) =>
        prev.map((r) =>
          r.id === resultId ? { ...r, pipeline_stage: "rejected" } : r
        )
      );
      toast.success("Candidate rejected");
    } catch { toast.error("Failed"); }
  };

  const filtered = rankings.filter((r) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      (r.candidate_name || "").toLowerCase().includes(q) ||
      (r.candidate_email || "").toLowerCase().includes(q)
    );
  });

  const avgScore =
    rankings.length > 0
      ? rankings.reduce((a, r) => a + (r.similarity_score || 0), 0) / rankings.length
      : 0;

  const aboveThresholdCount = rankings.filter(
    (r) => (r.similarity_score || 0) >= threshold
  ).length;

  return (
    <div className="space-y-6 max-w-7xl">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">AI Rankings</h1>
          <p className="text-slate-400 text-sm mt-0.5">
            {rankings.length > 0 ? `${rankings.length} candidates ranked` : "Run AI to rank candidates"}
          </p>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          {/* Ranking mode selector */}
          <div className="flex items-center bg-slate-900/80 border border-slate-700/50 rounded-xl p-1 gap-1">
            {(["traditional", "semantic", "ml", "hybrid"] as const).map((mode) => {
              const labels: Record<string, string> = {
                traditional: "Traditional",
                semantic: "Semantic",
                ml: "ML Only",
                hybrid: "Hybrid AI",
              };
              return (
                <button
                  key={mode}
                  onClick={() => setRankingMode(mode)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                    rankingMode === mode
                      ? "bg-indigo-600 text-white shadow"
                      : "text-slate-400 hover:text-white hover:bg-white/5"
                  }`}
                >
                  {labels[mode]}
                </button>
              );
            })}
          </div>

          {/* Threshold toggle button */}
          <button
            onClick={() => setShowThreshold((v) => !v)}
            className={`flex items-center gap-2 px-3 py-2.5 rounded-xl text-xs font-medium border transition-all ${
              showThreshold
                ? "bg-amber-500/15 border-amber-500/40 text-amber-400"
                : "bg-slate-900/80 border-slate-700/50 text-slate-400 hover:text-white hover:bg-white/5"
            }`}
            title="Configure auto-select threshold"
          >
            <Target className="w-4 h-4" />
            <span>Threshold</span>
            {rankings.length > 0 && (
              <span className="bg-amber-500/20 text-amber-300 px-1.5 rounded text-xs">
                {threshold}%
              </span>
            )}
          </button>

          <div className="relative">
            <select
              value={selectedJob}
              onChange={(e) => setSelectedJob(e.target.value)}
              className="bg-slate-900/80 border border-slate-700/50 rounded-xl pl-4 pr-8 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 appearance-none"
            >
              {jobsLoading ? (
                <option>Loading jobs...</option>
              ) : jobs.length === 0 ? (
                <option value="">No jobs — create one first</option>
              ) : (
                jobs.map((j) => <option key={j.id} value={j.id}>{j.title}</option>)
              )}
            </select>
            <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
          </div>

          <button
            onClick={handleRun}
            disabled={ranking || !selectedJob}
            className="flex items-center gap-2 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white px-4 py-2.5 rounded-xl text-sm font-medium transition-all shadow-glow disabled:opacity-60"
          >
            {ranking ? <Loader2 className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
            {ranking ? "Ranking..." : "Run AI Ranking"}
          </button>
        </div>
      </div>

      {/* Threshold panel */}
      <AnimatePresence>
        {showThreshold && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <div className="bg-slate-900/80 border border-amber-500/25 rounded-2xl p-5">
              <div className="flex items-start justify-between flex-wrap gap-4">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl bg-amber-500/15 flex items-center justify-center flex-shrink-0">
                    <Target className="w-5 h-5 text-amber-400" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                      Auto-Select Threshold
                      <span className="text-xs font-normal text-slate-500">
                        — candidates scoring at or above this are automatically shortlisted
                      </span>
                    </h3>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Applied when you click <strong className="text-slate-400">Run AI Ranking</strong> or{" "}
                      <strong className="text-slate-400">Apply Now</strong>.
                    </p>
                  </div>
                </div>

                {/* Threshold value display */}
                <div className="flex items-center gap-3">
                  <div className="text-center">
                    <div className="text-3xl font-bold text-amber-400 tabular-nums leading-none">
                      {threshold}
                      <span className="text-lg">%</span>
                    </div>
                    <div className="text-xs text-slate-500 mt-1">
                      {rankings.length > 0
                        ? `${aboveThresholdCount} of ${rankings.length} qualify`
                        : "threshold"}
                    </div>
                  </div>
                </div>
              </div>

              {/* Slider */}
              <div className="mt-4 space-y-2">
                <div className="flex justify-between text-xs text-slate-600">
                  <span>0% (everyone)</span>
                  <span>50% (half)</span>
                  <span>100% (perfect only)</span>
                </div>
                <div className="relative">
                  <input
                    type="range"
                    min={0}
                    max={100}
                    step={5}
                    value={threshold}
                    onChange={(e) => setThreshold(Number(e.target.value))}
                    className="w-full h-2 rounded-full appearance-none cursor-pointer"
                    style={{
                      background: `linear-gradient(to right, #f59e0b ${threshold}%, #1e293b ${threshold}%)`,
                    }}
                  />
                </div>

                {/* Preset quick-picks */}
                <div className="flex items-center gap-2 flex-wrap pt-1">
                  <span className="text-xs text-slate-500">Quick pick:</span>
                  {[50, 60, 70, 75, 80, 85, 90].map((v) => (
                    <button
                      key={v}
                      onClick={() => setThreshold(v)}
                      className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all border ${
                        threshold === v
                          ? "bg-amber-500/20 border-amber-500/50 text-amber-300"
                          : "border-slate-700 text-slate-500 hover:text-white hover:border-slate-500"
                      }`}
                    >
                      {v}%
                    </button>
                  ))}
                </div>
              </div>

              {/* Info band + Apply button */}
              <div className="mt-4 flex items-center justify-between gap-4 flex-wrap">
                <div className="flex items-start gap-2 text-xs text-slate-400">
                  <Sparkles className="w-3.5 h-3.5 text-amber-400 mt-0.5 flex-shrink-0" />
                  <span>
                    Candidates scoring <strong className="text-amber-300">≥ {threshold}%</strong> will be
                    moved to <strong className="text-emerald-300">Shortlisted</strong> automatically.
                    Already-rejected candidates are skipped.
                  </span>
                </div>

                <button
                  onClick={handleApplyThreshold}
                  disabled={applyingThreshold || rankings.length === 0}
                  className="flex items-center gap-2 bg-amber-600 hover:bg-amber-500 disabled:opacity-50 text-white px-4 py-2 rounded-xl text-sm font-medium transition-colors whitespace-nowrap"
                >
                  {applyingThreshold
                    ? <Loader2 className="w-4 h-4 animate-spin" />
                    : <SlidersHorizontal className="w-4 h-4" />}
                  {applyingThreshold ? "Applying..." : "Apply Now"}
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Stats strip */}
      {rankings.length > 0 && (
        <div className="grid grid-cols-4 gap-3">
          {[
            { label: "Total Ranked",   value: rankings.length,                               icon: Trophy,      color: "text-indigo-400" },
            { label: "Shortlisted",    value: rankings.filter((r) => r.is_shortlisted).length, icon: CheckCircle, color: "text-emerald-400" },
            { label: "Avg Score",      value: pct100(avgScore),                              icon: TrendingUp,  color: "text-amber-400" },
            {
              label: `Above ${threshold}%`,
              value: aboveThresholdCount,
              icon: Target,
              color: aboveThresholdCount > 0 ? "text-amber-400" : "text-slate-600",
            },
          ].map(({ label, value, icon: Icon, color }) => (
            <div key={label} className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-4 flex items-center gap-3">
              <Icon className={`w-5 h-5 ${color}`} />
              <div>
                <div className="text-lg font-bold text-white">{value}</div>
                <div className="text-xs text-slate-500">{label}</div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Search */}
      {rankings.length > 0 && (
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Filter candidates..."
            className="w-full bg-slate-900/80 border border-slate-700/50 rounded-xl pl-10 pr-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 text-sm"
          />
        </div>
      )}

      {/* Rankings list */}
      {loading ? (
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="bg-slate-900/80 border border-slate-700/50 rounded-2xl p-5 h-20 shimmer" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <Trophy className="w-16 h-16 text-slate-700 mb-4" />
          <h3 className="text-lg font-semibold text-slate-400">
            {jobs.length === 0 ? "Create a job first" : "No rankings yet"}
          </h3>
          <p className="text-slate-500 text-sm mt-1 mb-6">
            {jobs.length === 0
              ? "Go to Jobs and post your first position"
              : "Click 'Run AI Ranking' to analyze candidates for this job"}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          <AnimatePresence>
            {filtered.map((result, i) => {
              const isRejected = result.pipeline_stage === "rejected";
              const isShortlisted = result.is_shortlisted;
              const score = result.similarity_score || 0;
              const meetsThreshold = score >= threshold && !isShortlisted && !isRejected;

              return (
                <motion.div
                  key={result.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.03 }}
                  className={`bg-slate-900/80 border rounded-2xl p-5 hover:border-slate-600/50 transition-all cursor-pointer ${
                    isRejected
                      ? "border-red-500/20 opacity-60"
                      : isShortlisted
                      ? "border-emerald-500/30"
                      : meetsThreshold
                      ? "border-amber-500/30"
                      : "border-slate-700/50"
                  }`}
                  onClick={() => setDetailId(result.id === detailId ? null : result.id)}
                >
                  <div className="flex items-center gap-4">
                    {/* Rank */}
                    <div className="w-8 flex-shrink-0 text-center">
                      <RankBadge rank={result.rank} />
                    </div>

                    {/* Avatar */}
                    <div className={`w-9 h-9 rounded-full flex items-center justify-center text-white font-semibold text-sm flex-shrink-0 bg-gradient-to-br ${
                      meetsThreshold
                        ? "from-amber-500 to-orange-500"
                        : "from-indigo-500 to-violet-600"
                    }`}>
                      {result.candidate_name?.[0]?.toUpperCase() || "?"}
                    </div>

                    {/* Name + email */}
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-white text-sm truncate flex items-center gap-2">
                        {result.candidate_name || "Unknown"}
                        {meetsThreshold && (
                          <span className="inline-flex items-center gap-1 text-xs bg-amber-500/15 text-amber-400 border border-amber-500/25 px-1.5 py-0.5 rounded-md font-medium">
                            <Target className="w-2.5 h-2.5" />
                            Above threshold
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-slate-500 truncate">{result.candidate_email}</div>
                    </div>

                    {/* Component score bars */}
                    <div className="hidden lg:flex items-center gap-6 flex-shrink-0">
                      {[
                        { label: "Semantic", val: result.semantic_score,    color: "bg-indigo-500" },
                        { label: "Skills",   val: result.skill_score,       color: "bg-violet-500" },
                        { label: "Exp.",     val: result.experience_score,  color: "bg-amber-500" },
                      ].map(({ label, val, color }) => (
                        <div key={label} className="text-center w-16">
                          <div className="text-xs text-slate-500 mb-1">{label}</div>
                          <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
                            <div
                              className={`h-full ${color} rounded-full`}
                              style={{ width: safeWidth(val) }}
                            />
                          </div>
                          <div className="text-xs text-slate-400 mt-1">{pct(val)}</div>
                        </div>
                      ))}
                    </div>

                    {/* Total score (0–100) */}
                    <div className="flex-shrink-0 text-right w-16">
                      <div className={`text-xl font-bold ${ScoreColor(score)}`}>
                        {pct100(score)}
                      </div>
                      <div className="text-xs text-slate-500">match</div>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2 flex-shrink-0">
                      {!isRejected && !isShortlisted && (
                        <>
                          <button
                            onClick={(e) => { e.stopPropagation(); handleShortlist(result.id, result.resume_id); }}
                            className="p-1.5 rounded-lg text-slate-500 hover:text-emerald-400 hover:bg-emerald-400/10 transition-colors"
                            title="Shortlist"
                          >
                            <CheckCircle className="w-4 h-4" />
                          </button>
                          <button
                            onClick={(e) => { e.stopPropagation(); handleReject(result.id, result.resume_id); }}
                            className="p-1.5 rounded-lg text-slate-500 hover:text-red-400 hover:bg-red-400/10 transition-colors"
                            title="Reject"
                          >
                            <XCircle className="w-4 h-4" />
                          </button>
                        </>
                      )}
                      {isShortlisted && (
                        <span className="text-xs text-emerald-400 bg-emerald-400/10 px-2 py-1 rounded-lg">Shortlisted</span>
                      )}
                      {isRejected && (
                        <span className="text-xs text-red-400 bg-red-400/10 px-2 py-1 rounded-lg">Rejected</span>
                      )}
                    </div>
                  </div>

                  {/* Expanded detail */}
                  <AnimatePresence>
                    {detailId === result.id && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        className="overflow-hidden"
                      >
                        <div className="mt-5 pt-5 border-t border-slate-700/50 grid grid-cols-1 lg:grid-cols-3 gap-6">
                          {/* AI score breakdown */}
                          <div className="space-y-3">
                            <div className="text-xs text-slate-500 uppercase tracking-wide flex items-center gap-2">
                              <Brain className="w-3.5 h-3.5" />
                              {result.shap_values?.ranking_mode === "ml" || result.shap_values?.ranking_mode === "hybrid"
                                ? "ML Score Breakdown"
                                : "AI Score Breakdown"}
                            </div>

                            {result.shap_values?.feature_shap &&
                              Object.keys(result.shap_values.feature_shap).length > 0 ? (
                              <div className="space-y-1.5">
                                <div className="text-xs text-slate-500 mb-1">Feature Contributions</div>
                                {Object.entries(result.shap_values.feature_shap)
                                  .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))
                                  .slice(0, 8)
                                  .map(([name, val]) => {
                                    const absVal = Math.abs(val);
                                    const isPositive = val >= 0;
                                    return (
                                      <div key={name} className="space-y-0.5">
                                        <div className="flex justify-between text-xs">
                                          <span className="text-slate-400 capitalize">
                                            {name.replace(/_/g, " ")}
                                          </span>
                                          <span className={isPositive ? "text-emerald-400" : "text-red-400"}>
                                            {isPositive ? "+" : ""}{(val * 100).toFixed(1)}%
                                          </span>
                                        </div>
                                        <div className="h-1 bg-slate-800 rounded-full overflow-hidden">
                                          <motion.div
                                            initial={{ width: 0 }}
                                            animate={{ width: `${Math.min(absVal * 500, 100)}%` }}
                                            transition={{ duration: 0.5 }}
                                            className={`h-full rounded-full ${isPositive ? "bg-emerald-500" : "bg-red-500"}`}
                                          />
                                        </div>
                                      </div>
                                    );
                                  })}
                              </div>
                            ) : (
                              <>
                                <ScoreBar label="Semantic Match (35%)" value={result.semantic_score} color="bg-indigo-500" />
                                <ScoreBar label="Skill Overlap (45%)" value={result.skill_score} color="bg-violet-500" />
                                <ScoreBar label="Experience (20%)" value={result.experience_score} color="bg-amber-500" />
                              </>
                            )}

                            <div className="mt-2 pt-2 border-t border-slate-800">
                              <div className="flex justify-between text-xs">
                                <span className="text-slate-500">
                                  {result.shap_values?.ranking_mode === "ml" || result.shap_values?.ranking_mode === "hybrid"
                                    ? "ML Hire Probability"
                                    : "AI Score"}
                                </span>
                                <span className="text-emerald-400 font-bold">{pct(result.hiring_probability)}</span>
                              </div>
                              {result.shap_values?.ranking_mode && (
                                <div className="flex justify-between text-xs mt-1">
                                  <span className="text-slate-600">Mode</span>
                                  <span className="text-indigo-400 capitalize">{result.shap_values.ranking_mode}</span>
                                </div>
                              )}
                              <div className="flex justify-between text-xs mt-1">
                                <span className="text-slate-600">Threshold</span>
                                <span className={score >= threshold ? "text-amber-400" : "text-slate-500"}>
                                  {score >= threshold ? `≥ ${threshold}% ✓` : `< ${threshold}%`}
                                </span>
                              </div>
                            </div>
                            {result.recommendation && (
                              <div className="text-xs text-slate-400 italic">{result.recommendation}</div>
                            )}
                          </div>

                          {/* Skill analysis */}
                          <div className="space-y-3">
                            <div className="text-xs text-slate-500 uppercase tracking-wide">Skill Analysis</div>
                            {(result.matched_skills?.length ?? 0) > 0 && (
                              <div>
                                <div className="text-xs text-emerald-400 mb-1.5 flex items-center gap-1">
                                  <CheckCircle className="w-3 h-3" /> Matched ({result.matched_skills.length})
                                </div>
                                <div className="flex flex-wrap gap-1">
                                  {result.matched_skills.map((s) => (
                                    <span key={s} className="skill-matched text-xs">{s}</span>
                                  ))}
                                </div>
                              </div>
                            )}
                            {(result.missing_skills?.length ?? 0) > 0 && (
                              <div>
                                <div className="text-xs text-red-400 mb-1.5 flex items-center gap-1">
                                  <AlertCircle className="w-3 h-3" /> Missing ({result.missing_skills.length})
                                </div>
                                <div className="flex flex-wrap gap-1">
                                  {result.missing_skills.map((s) => (
                                    <span key={s} className="skill-missing text-xs">{s}</span>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>

                          {/* Interview questions */}
                          <div className="space-y-3">
                            <div className="text-xs text-slate-500 uppercase tracking-wide flex items-center gap-2">
                              <Award className="w-3.5 h-3.5" />
                              Interview Questions
                            </div>
                            <div className="space-y-2">
                              {(result.ai_interview_questions || []).slice(0, 4).map((q, qi) => (
                                <div
                                  key={qi}
                                  className="text-xs text-slate-300 bg-slate-800/50 rounded-lg p-2.5 leading-relaxed"
                                >
                                  {qi + 1}. {q}
                                </div>
                              ))}
                              {!(result.ai_interview_questions?.length) && (
                                <p className="text-xs text-slate-500">Run ranking to generate questions</p>
                              )}
                            </div>
                          </div>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.div>
              );
            })}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}
