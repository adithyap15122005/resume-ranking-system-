"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useDropzone } from "react-dropzone";
import {
  Upload, Database, Play, CheckCircle2, Loader2,
  BarChart2, Table2, Trophy, Zap, X, ChevronDown, AlertCircle,
} from "lucide-react";
import { trainingApi } from "@/lib/api";
import toast from "react-hot-toast";
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell,
} from "recharts";

interface Dataset {
  id: string;
  name: string;
  filename: string;
  rows: number;
  columns: number;
  uploaded_at: string;
  status: string;
}

interface EDA {
  rows: number;
  columns: number;
  column_names: string[];
  dtypes: Record<string, string>;
  missing_values: Record<string, number>;
  value_counts: Record<string, Record<string, number>>;
}

interface TrainingStatus {
  job_id: string;
  status: "pending" | "running" | "completed" | "failed";
  progress: number;
  message: string;
  best_model?: string;
  metrics?: Record<string, number>;
}

interface LeaderboardEntry {
  model: string;
  accuracy: number;
  f1: number;
  precision: number;
  recall: number;
  training_time: number;
}

const COLORS = ["#6366f1", "#8b5cf6", "#ec4899", "#f59e0b", "#10b981", "#3b82f6"];

export default function TrainingPage() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [selectedDataset, setSelectedDataset] = useState<string>("");
  const [eda, setEda] = useState<EDA | null>(null);
  const [edaLoading, setEdaLoading] = useState(false);
  const [trainingJobId, setTrainingJobId] = useState<string | null>(null);
  const [trainStatus, setTrainStatus] = useState<TrainingStatus | null>(null);
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);
  const [targetColumn, setTargetColumn] = useState("hired");
  const [activeTab, setActiveTab] = useState<"upload" | "eda" | "train" | "results">("upload");
  const pollRef = useRef<NodeJS.Timeout | null>(null);

  const fetchDatasets = useCallback(async () => {
    try {
      const data = await trainingApi.datasets();
      const list = Array.isArray(data) ? data : [];
      setDatasets(list);
      if (list.length > 0 && !selectedDataset) setSelectedDataset(list[0].id);
    } catch { /* ignore */ }
  }, [selectedDataset]);

  const fetchLeaderboard = useCallback(async () => {
    try {
      const data = await trainingApi.leaderboard();
      setLeaderboard(Array.isArray(data) ? data : []);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    fetchDatasets();
    fetchLeaderboard();
  }, [fetchDatasets, fetchLeaderboard]);

  // Poll training status
  useEffect(() => {
    if (!trainingJobId) return;
    const poll = async () => {
      try {
        const s = await trainingApi.status(trainingJobId);
        setTrainStatus(s);
        if (s.status === "completed") {
          fetchLeaderboard();
          setActiveTab("results");
          pollRef.current && clearInterval(pollRef.current);
        } else if (s.status === "failed") {
          toast.error(s.message || "Training failed");
          pollRef.current && clearInterval(pollRef.current);
        }
      } catch { /* ignore */ }
    };
    pollRef.current = setInterval(poll, 2000);
    return () => { pollRef.current && clearInterval(pollRef.current); };
  }, [trainingJobId, fetchLeaderboard]);

  const onDrop = useCallback(async (files: File[]) => {
    if (!files.length) return;
    setUploading(true);
    setUploadProgress(0);
    try {
      const result = await trainingApi.uploadDataset(files[0]);
      toast.success("Dataset uploaded!");
      fetchDatasets();
      setSelectedDataset(result.id);
      setActiveTab("eda");
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Upload failed";
      toast.error(msg);
    } finally {
      setUploading(false);
      setUploadProgress(0);
    }
  }, [fetchDatasets]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "text/csv": [".csv"] },
    multiple: false,
  });

  const handleAnalyze = async () => {
    if (!selectedDataset) return;
    setEdaLoading(true);
    try {
      const data = await trainingApi.analyze(selectedDataset);
      setEda(data);
      setActiveTab("eda");
    } catch {
      toast.error("Analysis failed");
    } finally {
      setEdaLoading(false);
    }
  };

  const handleTrain = async () => {
    if (!selectedDataset) { toast.error("Select a dataset first"); return; }
    try {
      const result = await trainingApi.train({ dataset_id: selectedDataset, target_column: targetColumn });
      setTrainingJobId(result.job_id);
      setTrainStatus({ job_id: result.job_id, status: "pending", progress: 0, message: "Starting..." });
      setActiveTab("train");
      toast.success("Training started!");
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Failed to start training";
      toast.error(msg);
    }
  };

  const tabs = [
    { id: "upload", label: "Upload", icon: Upload },
    { id: "eda", label: "EDA", icon: Table2 },
    { id: "train", label: "Train", icon: Play },
    { id: "results", label: "Leaderboard", icon: Trophy },
  ] as const;

  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <h1 className="text-2xl font-bold text-white">AI Training Dashboard</h1>
        <p className="text-slate-400 text-sm mt-0.5">Upload Kaggle CSVs, explore data, train ML models</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-slate-900/80 border border-slate-700/50 rounded-xl p-1 w-fit">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              activeTab === id
                ? "bg-indigo-600 text-white"
                : "text-slate-400 hover:text-white hover:bg-white/5"
            }`}
          >
            <Icon className="w-3.5 h-3.5" />
            {label}
          </button>
        ))}
      </div>

      {/* Upload Tab */}
      {activeTab === "upload" && (
        <div className="space-y-4">
          <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-all ${
              isDragActive
                ? "border-indigo-500 bg-indigo-500/10"
                : "border-slate-700 bg-slate-900/40 hover:border-slate-600 hover:bg-slate-900/60"
            }`}
          >
            <input {...getInputProps()} />
            {uploading ? (
              <div className="flex flex-col items-center gap-3">
                <Loader2 className="w-10 h-10 text-indigo-400 animate-spin" />
                <p className="text-slate-300 font-medium">Uploading dataset...</p>
                <div className="w-48 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                  <div className="h-full bg-indigo-500 rounded-full animate-pulse" style={{ width: "70%" }} />
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-3">
                <div className={`w-14 h-14 rounded-2xl flex items-center justify-center transition-all ${isDragActive ? "bg-indigo-500" : "bg-slate-800"}`}>
                  <Database className={`w-7 h-7 ${isDragActive ? "text-white" : "text-slate-400"}`} />
                </div>
                <div>
                  <p className="text-slate-300 font-medium text-lg">
                    {isDragActive ? "Drop CSV here!" : "Drop a Kaggle CSV dataset"}
                  </p>
                  <p className="text-slate-500 text-sm mt-1">
                    Upload any hiring/HR dataset with a target column (hired, shortlisted, etc.)
                  </p>
                </div>
                <div className="flex gap-2 mt-2">
                  {["hired", "shortlisted", "selected", "accepted"].map((col) => (
                    <span key={col} className="text-xs bg-slate-800 text-slate-400 px-2.5 py-1 rounded-lg">{col}</span>
                  ))}
                  <span className="text-xs text-slate-600 self-center">← example target columns</span>
                </div>
              </div>
            )}
          </div>

          {datasets.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-sm font-medium text-slate-400">Uploaded Datasets</h3>
              {datasets.map((d) => (
                <div
                  key={d.id}
                  className={`flex items-center justify-between p-4 bg-slate-900/80 border rounded-xl cursor-pointer transition-all ${
                    selectedDataset === d.id ? "border-indigo-500/50 bg-indigo-500/5" : "border-slate-700/50 hover:border-slate-600/50"
                  }`}
                  onClick={() => setSelectedDataset(d.id)}
                >
                  <div className="flex items-center gap-3">
                    <Database className="w-4 h-4 text-slate-400" />
                    <div>
                      <div className="text-sm font-medium text-white">{d.name || d.filename}</div>
                      <div className="text-xs text-slate-500">{d.rows?.toLocaleString()} rows × {d.columns} columns</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-slate-500">{new Date(d.uploaded_at).toLocaleDateString()}</span>
                    <button
                      onClick={(e) => { e.stopPropagation(); setSelectedDataset(d.id); handleAnalyze(); }}
                      disabled={edaLoading}
                      className="text-xs text-indigo-400 hover:text-indigo-300 bg-indigo-500/10 hover:bg-indigo-500/20 px-3 py-1.5 rounded-lg transition-all"
                    >
                      Analyze
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* EDA Tab */}
      {activeTab === "eda" && (
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <div className="relative flex-1 max-w-sm">
              <select
                value={selectedDataset}
                onChange={(e) => setSelectedDataset(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 pr-8 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 appearance-none"
              >
                {datasets.map((d) => <option key={d.id} value={d.id}>{d.name || d.filename}</option>)}
              </select>
              <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
            </div>
            <button
              onClick={handleAnalyze}
              disabled={edaLoading || !selectedDataset}
              className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2.5 rounded-xl text-sm font-medium transition-all disabled:opacity-60"
            >
              {edaLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <BarChart2 className="w-4 h-4" />}
              Run EDA
            </button>
          </div>

          {eda ? (
            <div className="space-y-4">
              {/* Overview */}
              <div className="grid grid-cols-3 gap-4">
                {[
                  { label: "Rows", value: eda.rows?.toLocaleString() },
                  { label: "Columns", value: eda.columns },
                  { label: "Missing Values", value: Object.values(eda.missing_values || {}).reduce((a, b) => a + b, 0) },
                ].map(({ label, value }) => (
                  <div key={label} className="bg-slate-900/80 border border-slate-700/50 rounded-xl p-4 text-center">
                    <div className="text-2xl font-bold text-white">{value}</div>
                    <div className="text-xs text-slate-500 mt-1">{label}</div>
                  </div>
                ))}
              </div>

              {/* Column overview */}
              <div className="bg-slate-900/80 border border-slate-700/50 rounded-2xl overflow-hidden">
                <div className="p-4 border-b border-slate-700/50">
                  <h3 className="font-medium text-white text-sm">Column Summary</h3>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-slate-700/50">
                        <th className="text-left text-xs text-slate-500 px-4 py-3 font-medium">Column</th>
                        <th className="text-left text-xs text-slate-500 px-4 py-3 font-medium">Type</th>
                        <th className="text-left text-xs text-slate-500 px-4 py-3 font-medium">Missing</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(eda.column_names || []).map((col) => (
                        <tr key={col} className="border-b border-slate-800/50 hover:bg-white/2 transition-colors">
                          <td className="px-4 py-2.5 text-slate-300 font-medium">{col}</td>
                          <td className="px-4 py-2.5">
                            <span className="text-xs bg-slate-800 text-slate-400 px-2 py-0.5 rounded">{eda.dtypes?.[col]}</span>
                          </td>
                          <td className="px-4 py-2.5">
                            {(eda.missing_values?.[col] || 0) > 0 ? (
                              <span className="text-xs text-amber-400">{eda.missing_values[col]}</span>
                            ) : (
                              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Target column selector + train button */}
              <div className="flex items-center gap-3">
                <div className="flex-1 space-y-1">
                  <label className="text-xs text-slate-500">Target Column (label to predict)</label>
                  <div className="relative">
                    <select
                      value={targetColumn}
                      onChange={(e) => setTargetColumn(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 pr-8 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 appearance-none"
                    >
                      {(eda.column_names || []).map((c) => <option key={c} value={c}>{c}</option>)}
                    </select>
                    <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
                  </div>
                </div>
                <button
                  onClick={handleTrain}
                  className="flex items-center gap-2 mt-6 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white px-6 py-2.5 rounded-xl text-sm font-medium transition-all shadow-glow"
                >
                  <Zap className="w-4 h-4" />
                  Train Models
                </button>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <Table2 className="w-12 h-12 text-slate-700 mb-3" />
              <p className="text-slate-500 text-sm">Select a dataset and click Run EDA</p>
            </div>
          )}
        </div>
      )}

      {/* Training Tab */}
      {activeTab === "train" && (
        <div className="space-y-4">
          {trainStatus ? (
            <div className="bg-slate-900/80 border border-slate-700/50 rounded-2xl p-6 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold text-white">Training Progress</h3>
                <span className={`text-xs px-2 py-1 rounded-lg font-medium ${
                  trainStatus.status === "completed" ? "text-emerald-400 bg-emerald-400/10" :
                  trainStatus.status === "failed" ? "text-red-400 bg-red-400/10" :
                  "text-indigo-400 bg-indigo-400/10"
                }`}>
                  {trainStatus.status}
                </span>
              </div>

              <div className="space-y-1.5">
                <div className="flex justify-between text-sm">
                  <span className="text-slate-400">{trainStatus.message}</span>
                  <span className="text-white font-medium">{trainStatus.progress}%</span>
                </div>
                <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                  <motion.div
                    className="h-full bg-gradient-to-r from-indigo-500 to-violet-500 rounded-full"
                    style={{ width: `${trainStatus.progress}%` }}
                    transition={{ duration: 0.5 }}
                  />
                </div>
              </div>

              {trainStatus.status === "running" && (
                <div className="flex items-center gap-2 text-sm text-slate-400">
                  <Loader2 className="w-4 h-4 animate-spin text-indigo-400" />
                  Training XGBoost, LightGBM, Random Forest, and more...
                </div>
              )}

              {trainStatus.status === "completed" && trainStatus.metrics && (
                <div className="grid grid-cols-2 gap-3 mt-2">
                  {Object.entries(trainStatus.metrics).map(([key, val]) => (
                    <div key={key} className="bg-slate-800/60 rounded-xl p-3 text-center">
                      <div className="text-xl font-bold text-indigo-400">{(val * 100).toFixed(1)}%</div>
                      <div className="text-xs text-slate-500 mt-1 capitalize">{key.replace(/_/g, " ")}</div>
                    </div>
                  ))}
                </div>
              )}

              {trainStatus.best_model && (
                <div className="flex items-center gap-2 text-sm text-emerald-400">
                  <Trophy className="w-4 h-4" />
                  Best model: <span className="font-semibold">{trainStatus.best_model}</span>
                </div>
              )}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <Play className="w-12 h-12 text-slate-700 mb-3" />
              <p className="text-slate-500 text-sm">Upload and analyze a dataset, then click Train Models</p>
            </div>
          )}
        </div>
      )}

      {/* Leaderboard Tab */}
      {activeTab === "results" && (
        <div className="space-y-4">
          {leaderboard.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <Trophy className="w-12 h-12 text-slate-700 mb-3" />
              <p className="text-slate-500 text-sm">No trained models yet. Upload a dataset and run training.</p>
            </div>
          ) : (
            <>
              {/* Chart */}
              <div className="bg-slate-900/80 border border-slate-700/50 rounded-2xl p-5">
                <h3 className="font-semibold text-white mb-4">Model Comparison</h3>
                <ResponsiveContainer width="100%" height={240}>
                  <BarChart data={leaderboard} margin={{ left: -20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis dataKey="model" tick={{ fontSize: 10, fill: "#64748b" }} />
                    <YAxis domain={[0, 1]} tick={{ fontSize: 10, fill: "#64748b" }} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} />
                    <Tooltip
                      contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 8, fontSize: 12 }}
                      formatter={(v: number) => `${(v * 100).toFixed(1)}%`}
                    />
                    <Bar dataKey="accuracy" name="Accuracy" fill="#6366f1" radius={[4, 4, 0, 0]}>
                      {leaderboard.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Table */}
              <div className="bg-slate-900/80 border border-slate-700/50 rounded-2xl overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-700/50">
                      <th className="text-left text-xs text-slate-500 px-4 py-3 font-medium">Rank</th>
                      <th className="text-left text-xs text-slate-500 px-4 py-3 font-medium">Model</th>
                      <th className="text-right text-xs text-slate-500 px-4 py-3 font-medium">Accuracy</th>
                      <th className="text-right text-xs text-slate-500 px-4 py-3 font-medium">F1</th>
                      <th className="text-right text-xs text-slate-500 px-4 py-3 font-medium">Precision</th>
                      <th className="text-right text-xs text-slate-500 px-4 py-3 font-medium">Recall</th>
                    </tr>
                  </thead>
                  <tbody>
                    {leaderboard.map((m, i) => (
                      <tr key={m.model} className={`border-b border-slate-800/50 hover:bg-white/2 transition-colors ${i === 0 ? "bg-indigo-500/5" : ""}`}>
                        <td className="px-4 py-3">
                          {i === 0 ? "🥇" : i === 1 ? "🥈" : i === 2 ? "🥉" : <span className="text-slate-500">#{i + 1}</span>}
                        </td>
                        <td className="px-4 py-3 font-medium text-white">{m.model}</td>
                        <td className="px-4 py-3 text-right text-indigo-400 font-medium">{(m.accuracy * 100).toFixed(1)}%</td>
                        <td className="px-4 py-3 text-right text-slate-300">{(m.f1 * 100).toFixed(1)}%</td>
                        <td className="px-4 py-3 text-right text-slate-300">{(m.precision * 100).toFixed(1)}%</td>
                        <td className="px-4 py-3 text-right text-slate-300">{(m.recall * 100).toFixed(1)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
