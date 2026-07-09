"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useDropzone } from "react-dropzone";
import {
  Upload, Database, Play, CheckCircle2, Loader2, BarChart2, Table2,
  Trophy, Zap, X, ChevronDown, AlertCircle, Cpu, FlaskConical,
  Rocket, Archive, Trash2, RefreshCw, TrendingUp, ShieldCheck,
  Activity, GitBranch, Star, ChevronRight, Eye, Download,
} from "lucide-react";
import { trainingApi } from "@/lib/api";
import toast from "react-hot-toast";

// ── Types ─────────────────────────────────────────────────────────────────────

interface DatasetProfile {
  dataset_id: string;
  name: string;
  filename: string;
  rows: number;
  columns: number;
  missing_values: number;
  duplicate_rows: number;
  quality_score: number;
  column_types: Record<string, string>;
  column_stats: Record<string, any>;
  class_distribution: Record<string, number>;
  data_preview: Record<string, string>[];
  column_names: string[];
  status?: string;
  recommendations?: string[];
  missing_report?: Record<string, { count: number; pct: number }>;
  correlation_matrix?: { columns: string[]; values: number[][] };
  feature_importance_eda?: Record<string, number>;
  outliers_report?: Record<string, { count: number; pct: number; q1: number; q3: number }>;
  engineering_steps?: { name: string; status: string; detail: string }[];
  feature_count_before?: number;
  feature_count_after?: number;
  class_balance_after?: Record<string, number>;
  samples_after_smote?: number;
}

interface Experiment {
  id: string;
  name: string;
  status: string;
  algorithms: string[];
  algorithms_completed: number;
  algorithms_total: number;
  progress_pct: number;
  current_algorithm: string | null;
  best_model_id: string | null;
  model_ids: string[];
  error_message: string | null;
}

interface MLModel {
  id: string;
  name: string;
  algorithm: string;
  version: string;
  deployment_status: string;
  accuracy: number;
  precision_score: number;
  recall_score: number;
  f1_score: number;
  roc_auc: number;
  inference_time_ms: number;
  training_time_s: number;
  model_size_mb: number;
  feature_count: number;
  training_samples: number;
  feature_importance?: Record<string, number>;
  confusion_matrix_data?: { matrix: number[][]; labels: string[] };
  feature_names?: string[];
  trained_at: string | null;
  deployed_at: string | null;
}

const STEP_LABELS = [
  { n: 1, label: "Dataset Upload", icon: Upload },
  { n: 2, label: "EDA", icon: BarChart2 },
  { n: 3, label: "Feature Engineering", icon: Zap },
  { n: 4, label: "Model Training", icon: Cpu },
  { n: 5, label: "Leaderboard", icon: Trophy },
];

const TYPE_BADGE: Record<string, string> = {
  numerical: "bg-blue-500/20 text-blue-300 border-blue-500/30",
  categorical: "bg-violet-500/20 text-violet-300 border-violet-500/30",
  text: "bg-amber-500/20 text-amber-300 border-amber-500/30",
  date: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
  identifier: "bg-slate-500/20 text-slate-400 border-slate-500/30",
};

const DEPLOY_BADGE: Record<string, string> = {
  production: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
  experimental: "bg-indigo-500/20 text-indigo-400 border-indigo-500/30",
  archived: "bg-slate-500/20 text-slate-500 border-slate-600/30",
};

const ALL_ALGORITHMS = [
  "Logistic Regression", "Random Forest", "XGBoost", "LightGBM",
  "Gradient Boosting", "SVM", "Neural Network", "Extra Trees",
];

// ── Helpers ───────────────────────────────────────────────────────────────────

function pct(v: number) { return `${Math.round((v || 0) * 100)}%`; }
function fmt(v: number, d = 3) { return (v || 0).toFixed(d); }
function qualityColor(score: number) {
  if (score >= 80) return "text-emerald-400";
  if (score >= 60) return "text-amber-400";
  return "text-red-400";
}

// ── Step Indicator ────────────────────────────────────────────────────────────

function StepIndicator({ current, maxReached }: { current: number; maxReached: number }) {
  return (
    <div className="flex items-center gap-0">
      {STEP_LABELS.map((s, i) => {
        const done = s.n < current;
        const active = s.n === current;
        const reachable = s.n <= maxReached;
        const Icon = s.icon;
        return (
          <div key={s.n} className="flex items-center">
            <div className={`flex flex-col items-center gap-1 ${!reachable ? "opacity-30" : ""}`}>
              <div className={`w-9 h-9 rounded-full flex items-center justify-center border-2 transition-all duration-300 ${
                done ? "bg-indigo-600 border-indigo-500 text-white" :
                active ? "bg-indigo-600/20 border-indigo-400 text-indigo-300" :
                "bg-slate-800 border-slate-600 text-slate-500"
              }`}>
                {done ? <CheckCircle2 className="w-4 h-4" /> : <Icon className="w-4 h-4" />}
              </div>
              <span className={`text-xs font-medium hidden md:block whitespace-nowrap ${active ? "text-indigo-300" : done ? "text-slate-300" : "text-slate-600"}`}>
                {s.label}
              </span>
            </div>
            {i < STEP_LABELS.length - 1 && (
              <div className={`w-8 md:w-16 h-0.5 mx-1 mb-5 transition-all ${done ? "bg-indigo-500" : "bg-slate-700"}`} />
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── Correlation Heatmap (CSS grid) ────────────────────────────────────────────

function CorrelationHeatmap({ matrix }: { matrix: { columns: string[]; values: number[][] } }) {
  const { columns, values } = matrix;
  if (!columns.length) return null;
  const shown = columns.slice(0, 12);
  const shownVals = values.slice(0, 12).map(r => r.slice(0, 12));

  function corrColor(v: number) {
    const r = v > 0
      ? Math.round(v * 100)
      : 0;
    const b = v < 0
      ? Math.round(-v * 100)
      : 0;
    return `rgba(${r + 20}, 30, ${b + 20}, 0.8)`;
  }

  return (
    <div className="overflow-x-auto">
      <div className="inline-grid" style={{ gridTemplateColumns: `80px repeat(${shown.length}, 44px)` }}>
        <div />
        {shown.map(col => (
          <div key={col} className="h-12 flex items-end justify-center pb-1">
            <span className="text-[9px] text-slate-500 -rotate-45 origin-bottom-left block w-10 truncate">{col}</span>
          </div>
        ))}
        {shown.map((row, ri) => (
          <>
            <div key={`row-${row}`} className="h-11 flex items-center pr-2">
              <span className="text-[10px] text-slate-500 truncate text-right w-full">{row}</span>
            </div>
            {shownVals[ri]?.map((val, ci) => (
              <div
                key={`${ri}-${ci}`}
                className="h-11 w-11 flex items-center justify-center text-[9px] font-mono rounded-sm"
                style={{ background: corrColor(val), color: Math.abs(val) > 0.5 ? "#fff" : "#888" }}
                title={`${row} × ${shown[ci]}: ${val.toFixed(2)}`}
              >
                {val.toFixed(1)}
              </div>
            ))}
          </>
        ))}
      </div>
    </div>
  );
}

// ── Feature Importance Bar ────────────────────────────────────────────────────

function FeatureBar({ feature, value, max }: { feature: string; value: number; max: number }) {
  const width = max > 0 ? (value / max) * 100 : 0;
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-slate-400 w-28 truncate text-right">{feature}</span>
      <div className="flex-1 h-4 bg-slate-800 rounded-full overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-indigo-600 to-violet-500 rounded-full transition-all duration-700"
          style={{ width: `${width}%` }}
        />
      </div>
      <span className="text-xs text-slate-400 w-12 text-right font-mono">{(value * 100).toFixed(1)}%</span>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function TrainingPage() {
  const [step, setStep] = useState(1);
  const [maxReached, setMaxReached] = useState(1);
  const goStep = (n: number) => { if (n <= maxReached) { setStep(n); } };
  const advance = (n: number) => { setStep(n); if (n > maxReached) setMaxReached(n); };

  // Step 1 state
  const [uploading, setUploading] = useState(false);
  const [dataset, setDataset] = useState<DatasetProfile | null>(null);
  const [targetColumn, setTargetColumn] = useState("");

  // Step 2 state
  const [analyzing, setAnalyzing] = useState(false);
  const [edaDone, setEdaDone] = useState(false);

  // Step 3 state
  const [engineering, setEngineering] = useState(false);
  const [engDone, setEngDone] = useState(false);

  // Step 4 state
  const [selectedAlgos, setSelectedAlgos] = useState<string[]>(ALL_ALGORITHMS);
  const [expName, setExpName] = useState("Experiment-1");
  const [launching, setLaunching] = useState(false);
  const [experiment, setExperiment] = useState<Experiment | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Step 5 state
  const [models, setModels] = useState<MLModel[]>([]);
  const [loadingModels, setLoadingModels] = useState(false);
  const [selectedModel, setSelectedModel] = useState<MLModel | null>(null);
  const [deploying, setDeploying] = useState<string | null>(null);

  // ── Step 1: Upload ──────────────────────────────────────────────────────────

  const onDrop = useCallback(async (accepted: File[]) => {
    if (!accepted[0]) return;
    setUploading(true);
    try {
      const result = await trainingApi.uploadDataset(accepted[0]);
      setDataset({ ...result, dataset_id: result.dataset_id || result.id });
      if (result.column_names?.length) setTargetColumn(result.column_names[result.column_names.length - 1]);
      toast.success(`Dataset uploaded: ${result.rows.toLocaleString()} rows, ${result.columns} columns`);
    } catch {
      toast.error("Upload failed");
    } finally {
      setUploading(false);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "text/csv": [".csv"], "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"] },
    maxFiles: 1,
  });

  // ── Step 2: EDA ─────────────────────────────────────────────────────────────

  const runEDA = async () => {
    if (!dataset) return;
    setAnalyzing(true);
    try {
      const result = await trainingApi.analyzeDataset(dataset.dataset_id);
      setDataset(prev => prev ? { ...prev, ...result } : result);
      setEdaDone(true);
      advance(3);
      toast.success("EDA complete");
    } catch {
      toast.error("EDA failed");
    } finally {
      setAnalyzing(false);
    }
  };

  // ── Step 3: Feature Engineering ─────────────────────────────────────────────

  const runEngineering = async () => {
    if (!dataset || !targetColumn) return;
    setEngineering(true);
    try {
      const result = await trainingApi.engineerFeatures(dataset.dataset_id, targetColumn);
      setDataset(prev => prev ? { ...prev, ...result } : result);
      setEngDone(true);
      advance(4);
      toast.success("Feature engineering complete");
    } catch {
      toast.error("Feature engineering failed");
    } finally {
      setEngineering(false);
    }
  };

  // ── Step 4: Training ─────────────────────────────────────────────────────────

  const startTraining = async () => {
    if (!dataset || !targetColumn) return;
    setLaunching(true);
    try {
      const result = await trainingApi.startExperiment({
        dataset_id: dataset.dataset_id,
        name: expName,
        target_column: targetColumn,
        algorithms: selectedAlgos,
      });
      setExperiment({ ...result, algorithms: selectedAlgos, algorithms_completed: 0, algorithms_total: selectedAlgos.length, progress_pct: 0, current_algorithm: null, best_model_id: null, model_ids: [], error_message: null, status: "queued" });
      toast.success("Training started!");

      // Start polling
      pollRef.current = setInterval(async () => {
        try {
          const status = await trainingApi.getExperiment(result.experiment_id);
          setExperiment(status);
          if (status.status === "completed") {
            clearInterval(pollRef.current!);
            advance(5);
            loadModels();
            toast.success("Training complete! View the leaderboard.");
          } else if (status.status === "failed") {
            clearInterval(pollRef.current!);
            toast.error("Training failed: " + (status.error_message || "Unknown error"));
          }
        } catch {
          // ignore transient poll errors
        }
      }, 2500);
    } catch {
      toast.error("Failed to start training");
    } finally {
      setLaunching(false);
    }
  };

  useEffect(() => {
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, []);

  // ── Step 5: Leaderboard ──────────────────────────────────────────────────────

  const loadModels = async () => {
    setLoadingModels(true);
    try {
      const result = await trainingApi.listModels();
      setModels(Array.isArray(result) ? result : []);
    } catch {
      toast.error("Failed to load models");
    } finally {
      setLoadingModels(false);
    }
  };

  useEffect(() => {
    if (step === 5) loadModels();
  }, [step]);

  const deployModel = async (modelId: string) => {
    setDeploying(modelId);
    try {
      await trainingApi.deployModel(modelId);
      toast.success("Model deployed as production!");
      loadModels();
    } catch {
      toast.error("Deployment failed");
    } finally {
      setDeploying(null);
    }
  };

  const deleteModel = async (modelId: string) => {
    if (!confirm("Delete this model?")) return;
    try {
      await trainingApi.deleteModel(modelId);
      toast.success("Model deleted");
      loadModels();
    } catch {
      toast.error("Failed to delete");
    }
  };

  // ── Render ────────────────────────────────────────────────────────────────────

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <FlaskConical className="w-6 h-6 text-indigo-400" /> ML Training Console
        </h1>
        <p className="text-slate-400 text-sm mt-1">
          Upload datasets, run EDA, engineer features, train multiple models, and deploy the best one.
        </p>
      </div>

      {/* Step Indicator */}
      <div className="flex justify-center">
        <div className="cursor-pointer" onClick={(e) => {
          const t = (e.target as HTMLElement).closest("[data-step]");
          if (t) goStep(Number(t.getAttribute("data-step")));
        }}>
          <StepIndicator current={step} maxReached={maxReached} />
        </div>
      </div>

      <AnimatePresence mode="wait">
        {/* ── STEP 1: Dataset Upload ─────────────────────────────────────────── */}
        {step === 1 && (
          <motion.div
            key="step1"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -16 }}
            className="space-y-6"
          >
            {/* Drop zone */}
            <div
              {...getRootProps()}
              className={`border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-all ${
                isDragActive
                  ? "border-indigo-400 bg-indigo-500/10"
                  : "border-slate-700/50 hover:border-slate-600 bg-slate-900/40"
              }`}
            >
              <input {...getInputProps()} />
              {uploading ? (
                <div className="flex flex-col items-center gap-3">
                  <Loader2 className="w-12 h-12 text-indigo-400 animate-spin" />
                  <p className="text-slate-300">Uploading and profiling dataset…</p>
                </div>
              ) : (
                <div className="flex flex-col items-center gap-3">
                  <Upload className="w-12 h-12 text-slate-600" />
                  <p className="text-slate-300 font-medium">Drop a CSV or XLSX file here</p>
                  <p className="text-slate-500 text-sm">or click to browse</p>
                  <p className="text-slate-600 text-xs mt-2">Kaggle exports, company HR data, synthetic datasets — any labeled tabular dataset</p>
                </div>
              )}
            </div>

            {/* Dataset card (shown after upload) */}
            {dataset && (
              <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
                {/* Stats row */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {[
                    { label: "Rows", value: dataset.rows.toLocaleString(), icon: Database, color: "text-blue-400" },
                    { label: "Columns", value: dataset.columns, icon: Table2, color: "text-violet-400" },
                    { label: "Missing Values", value: dataset.missing_values.toLocaleString(), icon: AlertCircle, color: "text-amber-400" },
                    { label: "Duplicates", value: dataset.duplicate_rows.toLocaleString(), icon: GitBranch, color: "text-slate-400" },
                  ].map(s => (
                    <div key={s.label} className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
                      <div className="flex items-center gap-2 mb-1">
                        <s.icon className={`w-4 h-4 ${s.color}`} />
                        <span className="text-xs text-slate-500">{s.label}</span>
                      </div>
                      <div className="text-xl font-bold text-white">{s.value}</div>
                    </div>
                  ))}
                </div>

                {/* Quality score */}
                <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 flex items-center justify-between">
                  <div>
                    <div className="text-xs text-slate-500 mb-1">Dataset Quality Score</div>
                    <div className={`text-4xl font-bold ${qualityColor(dataset.quality_score)}`}>
                      {dataset.quality_score}
                      <span className="text-lg text-slate-500">/100</span>
                    </div>
                  </div>
                  <ShieldCheck className={`w-16 h-16 ${qualityColor(dataset.quality_score)} opacity-20`} />
                </div>

                {/* Column types */}
                <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5">
                  <h3 className="text-sm font-semibold text-slate-300 mb-3">Column Types (auto-detected)</h3>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(dataset.column_types || {}).map(([col, type]) => (
                      <span key={col} className={`text-xs px-2 py-1 rounded-lg border font-mono ${TYPE_BADGE[type] || "bg-slate-800 text-slate-400 border-slate-700"}`}>
                        {col} <span className="opacity-60">·</span> {type}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Target column selector */}
                <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5">
                  <label className="block text-sm font-semibold text-slate-300 mb-2">Target Column (what to predict)</label>
                  <div className="relative">
                    <select
                      value={targetColumn}
                      onChange={e => setTargetColumn(e.target.value)}
                      className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 appearance-none"
                    >
                      {(dataset.column_names || []).map(col => (
                        <option key={col} value={col}>{col} ({dataset.column_types[col] || "?"})</option>
                      ))}
                    </select>
                    <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
                  </div>
                </div>

                {/* Class distribution */}
                {Object.keys(dataset.class_distribution || {}).length > 0 && (
                  <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5">
                    <h3 className="text-sm font-semibold text-slate-300 mb-3">Class Distribution</h3>
                    <div className="space-y-2">
                      {Object.entries(dataset.class_distribution).map(([cls, cnt]) => {
                        const total = Object.values(dataset.class_distribution).reduce((a, b) => a + b, 0);
                        const w = total > 0 ? (cnt / total) * 100 : 0;
                        return (
                          <div key={cls} className="flex items-center gap-3">
                            <span className="text-xs text-slate-400 w-24 truncate">{cls}</span>
                            <div className="flex-1 h-3 bg-slate-800 rounded-full overflow-hidden">
                              <div className="h-full bg-gradient-to-r from-indigo-600 to-violet-500 rounded-full" style={{ width: `${w}%` }} />
                            </div>
                            <span className="text-xs text-slate-500 w-16 text-right">{cnt.toLocaleString()} ({w.toFixed(1)}%)</span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Data preview table */}
                <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden">
                  <div className="px-5 py-3 border-b border-slate-800 flex items-center gap-2">
                    <Eye className="w-4 h-4 text-slate-500" />
                    <h3 className="text-sm font-semibold text-slate-300">Data Preview (first 20 rows)</h3>
                  </div>
                  <div className="overflow-x-auto max-h-72">
                    <table className="w-full text-xs">
                      <thead className="bg-slate-800/80 sticky top-0">
                        <tr>
                          {(dataset.column_names || []).slice(0, 10).map(col => (
                            <th key={col} className="px-3 py-2 text-left text-slate-400 font-medium whitespace-nowrap">{col}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {(dataset.data_preview || []).map((row, i) => (
                          <tr key={i} className={i % 2 === 0 ? "bg-transparent" : "bg-slate-800/20"}>
                            {(dataset.column_names || []).slice(0, 10).map(col => (
                              <td key={col} className="px-3 py-1.5 text-slate-300 max-w-[120px] truncate">{row[col] ?? ""}</td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                <button
                  onClick={() => advance(2)}
                  disabled={!targetColumn}
                  className="w-full py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold transition-colors disabled:opacity-40 flex items-center justify-center gap-2"
                >
                  Analyze Dataset <ChevronRight className="w-4 h-4" />
                </button>
              </motion.div>
            )}
          </motion.div>
        )}

        {/* ── STEP 2: EDA ───────────────────────────────────────────────────── */}
        {step === 2 && dataset && (
          <motion.div key="step2" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -16 }} className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-bold text-white">Automatic EDA</h2>
                <p className="text-sm text-slate-400">Analyzing dataset quality, correlations, and feature importance</p>
              </div>
              {!edaDone && (
                <button
                  onClick={runEDA}
                  disabled={analyzing}
                  className="px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold transition-colors flex items-center gap-2 disabled:opacity-60"
                >
                  {analyzing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                  {analyzing ? "Analyzing…" : "Run EDA"}
                </button>
              )}
            </div>

            {analyzing && (
              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-8 flex flex-col items-center gap-4">
                <div className="relative">
                  <div className="w-20 h-20 rounded-full border-4 border-slate-800" />
                  <div className="absolute inset-0 w-20 h-20 rounded-full border-4 border-indigo-500 border-t-transparent animate-spin" />
                  <BarChart2 className="absolute inset-0 m-auto w-8 h-8 text-indigo-400" />
                </div>
                <p className="text-slate-300 font-medium">Running exploratory data analysis…</p>
                <p className="text-slate-500 text-sm">Computing correlations, outliers, feature importance</p>
              </div>
            )}

            {edaDone && dataset && (
              <>
                {/* Quality score */}
                <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 flex items-center justify-between">
                  <div>
                    <div className="text-xs text-slate-500 mb-1">Post-EDA Quality Score</div>
                    <div className={`text-5xl font-bold ${qualityColor(dataset.quality_score)}`}>
                      {dataset.quality_score}<span className="text-xl text-slate-500">/100</span>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-slate-500 mb-1">Recommendations</p>
                    <p className="text-sm text-slate-300">{(dataset.recommendations || []).length} items</p>
                  </div>
                </div>

                {/* Recommendations */}
                {(dataset.recommendations || []).length > 0 && (
                  <div className="bg-amber-500/5 border border-amber-500/20 rounded-xl p-5">
                    <h3 className="text-sm font-semibold text-amber-400 mb-3 flex items-center gap-2">
                      <AlertCircle className="w-4 h-4" /> Recommendations
                    </h3>
                    <ul className="space-y-1.5">
                      {(dataset.recommendations || []).map((r, i) => (
                        <li key={i} className="text-sm text-slate-300 flex gap-2">
                          <span className="text-amber-500 flex-shrink-0">•</span> {r}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Missing values report */}
                {dataset.missing_report && (
                  <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5">
                    <h3 className="text-sm font-semibold text-slate-300 mb-4">Missing Value Report</h3>
                    <div className="space-y-2 max-h-48 overflow-y-auto">
                      {Object.entries(dataset.missing_report).filter(([, v]) => v.count > 0).map(([col, v]) => (
                        <div key={col} className="flex items-center gap-3">
                          <span className="text-xs text-slate-400 w-32 truncate">{col}</span>
                          <div className="flex-1 h-3 bg-slate-800 rounded-full overflow-hidden">
                            <div className="h-full bg-red-500/70 rounded-full" style={{ width: `${v.pct}%` }} />
                          </div>
                          <span className="text-xs text-red-400 w-20 text-right">{v.count} ({v.pct}%)</span>
                        </div>
                      ))}
                      {Object.values(dataset.missing_report).every(v => v.count === 0) && (
                        <div className="flex items-center gap-2 text-emerald-400 text-sm">
                          <CheckCircle2 className="w-4 h-4" /> No missing values detected
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Feature importance */}
                {dataset.feature_importance_eda && Object.keys(dataset.feature_importance_eda).length > 0 && (
                  <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5">
                    <h3 className="text-sm font-semibold text-slate-300 mb-4">Feature Importance (Quick RF Estimate)</h3>
                    <div className="space-y-2">
                      {Object.entries(dataset.feature_importance_eda)
                        .sort(([, a], [, b]) => b - a)
                        .slice(0, 15)
                        .map(([feat, imp]) => (
                          <FeatureBar
                            key={feat}
                            feature={feat}
                            value={imp}
                            max={Math.max(...Object.values(dataset.feature_importance_eda!))}
                          />
                        ))}
                    </div>
                  </div>
                )}

                {/* Correlation heatmap */}
                {dataset.correlation_matrix?.columns?.length > 1 && (
                  <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5">
                    <h3 className="text-sm font-semibold text-slate-300 mb-4">Correlation Heatmap</h3>
                    <CorrelationHeatmap matrix={dataset.correlation_matrix} />
                  </div>
                )}

                {/* Outliers */}
                {dataset.outliers_report && Object.keys(dataset.outliers_report).length > 0 && (
                  <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5">
                    <h3 className="text-sm font-semibold text-slate-300 mb-4">Outlier Detection (IQR Method)</h3>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                      {Object.entries(dataset.outliers_report).map(([col, v]) => (
                        <div key={col} className={`rounded-xl p-3 border ${v.pct > 5 ? "bg-red-500/5 border-red-500/20" : "bg-slate-800/60 border-slate-700/50"}`}>
                          <div className="text-xs text-slate-400 truncate mb-1">{col}</div>
                          <div className={`text-lg font-bold ${v.pct > 5 ? "text-red-400" : "text-slate-300"}`}>{v.count}</div>
                          <div className="text-xs text-slate-500">{v.pct}% outliers</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <button onClick={() => advance(3)} className="w-full py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold flex items-center justify-center gap-2">
                  Engineer Features <ChevronRight className="w-4 h-4" />
                </button>
              </>
            )}
          </motion.div>
        )}

        {/* ── STEP 3: Feature Engineering ───────────────────────────────────── */}
        {step === 3 && dataset && (
          <motion.div key="step3" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -16 }} className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-bold text-white">Feature Engineering</h2>
                <p className="text-sm text-slate-400">Auto-apply transformations to prepare data for ML</p>
              </div>
              {!engDone && (
                <button
                  onClick={runEngineering}
                  disabled={engineering || !targetColumn}
                  className="px-6 py-2.5 rounded-xl bg-violet-600 hover:bg-violet-500 text-white text-sm font-semibold flex items-center gap-2 disabled:opacity-60"
                >
                  {engineering ? <Loader2 className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
                  {engineering ? "Processing…" : "Run Feature Engineering"}
                </button>
              )}
            </div>

            {/* Steps list */}
            {dataset.engineering_steps ? (
              <div className="bg-slate-900/60 border border-slate-800 rounded-xl divide-y divide-slate-800">
                {(dataset.engineering_steps || []).map((s, i) => (
                  <div key={i} className="p-4 flex items-start gap-4">
                    <div className={`w-7 h-7 rounded-full flex-shrink-0 flex items-center justify-center mt-0.5 ${
                      s.status === "done" ? "bg-emerald-500/20 text-emerald-400" : "bg-slate-800 text-slate-500"
                    }`}>
                      {s.status === "done" ? <CheckCircle2 className="w-4 h-4" /> : <span className="text-xs">{i + 1}</span>}
                    </div>
                    <div>
                      <div className="text-sm font-medium text-slate-200">{s.name}</div>
                      <div className="text-xs text-slate-500 mt-0.5">{s.detail}</div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6">
                <h3 className="text-sm font-semibold text-slate-300 mb-4">Steps to be applied automatically:</h3>
                <div className="space-y-3">
                  {[
                    { name: "Remove Duplicates", detail: "Deduplicate rows before training" },
                    { name: "Drop Identifier Columns", detail: "Remove high-cardinality ID columns" },
                    { name: "Handle Missing Values", detail: "Median imputation for numerical, mode for categorical" },
                    { name: "Encode Categorical Features", detail: "Label encoding for categorical columns" },
                    { name: "Normalize Numerical Features", detail: "StandardScaler: μ=0, σ=1" },
                    { name: "Drop Text/Date Columns", detail: "Remove raw text and date columns" },
                    { name: "Feature Selection", detail: "Select engineered features" },
                    { name: "Class Balance Check", detail: "Verify class distribution after processing" },
                  ].map((s, i) => (
                    <div key={i} className="flex items-center gap-3">
                      <div className="w-6 h-6 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-xs text-slate-500">{i + 1}</div>
                      <div>
                        <span className="text-sm text-slate-300">{s.name}</span>
                        <span className="text-xs text-slate-500 ml-2">{s.detail}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Before/after stats */}
            {engDone && (
              <>
                <div className="grid grid-cols-3 gap-4">
                  <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 text-center">
                    <div className="text-xs text-slate-500 mb-1">Features Before</div>
                    <div className="text-2xl font-bold text-slate-300">{dataset.feature_count_before ?? dataset.columns}</div>
                  </div>
                  <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 text-center">
                    <div className="text-xs text-slate-500 mb-1">Features After</div>
                    <div className="text-2xl font-bold text-indigo-400">{dataset.feature_count_after ?? dataset.columns}</div>
                  </div>
                  <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 text-center">
                    <div className="text-xs text-slate-500 mb-1">Samples</div>
                    <div className="text-2xl font-bold text-emerald-400">{(dataset.samples_after_smote ?? dataset.rows).toLocaleString()}</div>
                  </div>
                </div>

                <button onClick={() => advance(4)} className="w-full py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold flex items-center justify-center gap-2">
                  Start Training <ChevronRight className="w-4 h-4" />
                </button>
              </>
            )}
          </motion.div>
        )}

        {/* ── STEP 4: Model Training ─────────────────────────────────────────── */}
        {step === 4 && (
          <motion.div key="step4" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -16 }} className="space-y-6">
            <div>
              <h2 className="text-lg font-bold text-white">Model Training</h2>
              <p className="text-sm text-slate-400">Train multiple algorithms and compare on the leaderboard</p>
            </div>

            {!experiment ? (
              <>
                {/* Experiment name */}
                <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5">
                  <label className="block text-sm font-semibold text-slate-300 mb-2">Experiment Name</label>
                  <input
                    value={expName}
                    onChange={e => setExpName(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                    placeholder="My Hiring Prediction v1"
                  />
                </div>

                {/* Algorithm selection */}
                <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-sm font-semibold text-slate-300">Select Algorithms to Train</h3>
                    <div className="flex gap-2">
                      <button onClick={() => setSelectedAlgos(ALL_ALGORITHMS)} className="text-xs text-indigo-400 hover:text-indigo-300">Select all</button>
                      <span className="text-slate-600">·</span>
                      <button onClick={() => setSelectedAlgos([])} className="text-xs text-slate-500 hover:text-slate-400">Clear</button>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    {ALL_ALGORITHMS.map(algo => (
                      <label key={algo} className={`flex items-center gap-2 p-3 rounded-xl border cursor-pointer transition-all ${
                        selectedAlgos.includes(algo)
                          ? "bg-indigo-600/10 border-indigo-500/40 text-indigo-300"
                          : "bg-slate-800/50 border-slate-700/50 text-slate-400 hover:border-slate-600"
                      }`}>
                        <input
                          type="checkbox"
                          checked={selectedAlgos.includes(algo)}
                          onChange={e => setSelectedAlgos(prev =>
                            e.target.checked ? [...prev, algo] : prev.filter(a => a !== algo)
                          )}
                          className="sr-only"
                        />
                        {selectedAlgos.includes(algo)
                          ? <CheckCircle2 className="w-3.5 h-3.5 flex-shrink-0" />
                          : <div className="w-3.5 h-3.5 rounded-full border border-slate-600 flex-shrink-0" />
                        }
                        <span className="text-xs font-medium leading-tight">{algo}</span>
                      </label>
                    ))}
                  </div>
                </div>

                <button
                  onClick={startTraining}
                  disabled={launching || selectedAlgos.length === 0}
                  className="w-full py-3.5 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white font-bold flex items-center justify-center gap-2 disabled:opacity-50 transition-all"
                >
                  {launching ? <Loader2 className="w-5 h-5 animate-spin" /> : <Play className="w-5 h-5" />}
                  {launching ? "Launching…" : `Train ${selectedAlgos.length} Algorithm${selectedAlgos.length !== 1 ? "s" : ""}`}
                </button>
              </>
            ) : (
              <>
                {/* Live progress */}
                <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      {experiment.status === "running" || experiment.status === "queued" ? (
                        <div className="w-3 h-3 rounded-full bg-indigo-400 animate-pulse" />
                      ) : experiment.status === "completed" ? (
                        <div className="w-3 h-3 rounded-full bg-emerald-400" />
                      ) : (
                        <div className="w-3 h-3 rounded-full bg-red-400" />
                      )}
                      <span className="text-sm font-semibold text-slate-200 capitalize">{experiment.status}</span>
                    </div>
                    <span className="text-sm text-slate-400">{experiment.algorithms_completed}/{experiment.algorithms_total} models</span>
                  </div>

                  {/* Overall progress bar */}
                  <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-indigo-500 to-violet-500 rounded-full transition-all duration-500"
                      style={{ width: `${experiment.progress_pct}%` }}
                    />
                  </div>

                  {experiment.current_algorithm && (
                    <div className="flex items-center gap-2 text-sm text-slate-400">
                      <Loader2 className="w-4 h-4 animate-spin text-indigo-400" />
                      Training: <span className="text-indigo-300 font-medium">{experiment.current_algorithm}</span>
                    </div>
                  )}
                </div>

                {/* Individual algorithm cards */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {(experiment.algorithms || []).map((algo, i) => {
                    const done = i < experiment.algorithms_completed;
                    const active = experiment.current_algorithm === algo;
                    return (
                      <div key={algo} className={`rounded-xl p-3 border transition-all ${
                        done ? "bg-emerald-500/5 border-emerald-500/20" :
                        active ? "bg-indigo-500/10 border-indigo-500/30" :
                        "bg-slate-900/40 border-slate-800"
                      }`}>
                        <div className="flex items-center gap-2 mb-2">
                          {done ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> :
                           active ? <Loader2 className="w-3.5 h-3.5 text-indigo-400 animate-spin" /> :
                           <div className="w-3.5 h-3.5 rounded-full border border-slate-600" />}
                          <span className="text-xs font-medium text-slate-300">{algo}</span>
                        </div>
                        <div className={`text-xs ${done ? "text-emerald-400" : active ? "text-indigo-400" : "text-slate-600"}`}>
                          {done ? "Completed" : active ? "Training…" : "Queued"}
                        </div>
                      </div>
                    );
                  })}
                </div>

                {experiment.status === "completed" && (
                  <button onClick={() => advance(5)} className="w-full py-3 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold flex items-center justify-center gap-2">
                    <Trophy className="w-4 h-4" /> View Leaderboard
                  </button>
                )}
              </>
            )}
          </motion.div>
        )}

        {/* ── STEP 5: Model Leaderboard ──────────────────────────────────────── */}
        {step === 5 && (
          <motion.div key="step5" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -16 }} className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-bold text-white">Model Leaderboard</h2>
                <p className="text-sm text-slate-400">Compare models and deploy the best one as production</p>
              </div>
              <button onClick={loadModels} disabled={loadingModels} className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition-colors">
                <RefreshCw className={`w-4 h-4 ${loadingModels ? "animate-spin" : ""}`} />
              </button>
            </div>

            {/* Production model banner */}
            {models.some(m => m.deployment_status === "production") && (
              <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-xl p-4 flex items-center gap-3">
                <Rocket className="w-5 h-5 text-emerald-400 flex-shrink-0" />
                <div>
                  <div className="text-sm font-semibold text-emerald-300">
                    Production Model: {models.find(m => m.deployment_status === "production")?.algorithm}
                  </div>
                  <div className="text-xs text-emerald-400/70">
                    F1={fmt(models.find(m => m.deployment_status === "production")?.f1_score || 0)} ·
                    ROC-AUC={fmt(models.find(m => m.deployment_status === "production")?.roc_auc || 0)} ·
                    Active for all recruiter rankings
                  </div>
                </div>
              </div>
            )}

            {loadingModels ? (
              <div className="flex items-center justify-center py-20">
                <Loader2 className="w-8 h-8 text-indigo-400 animate-spin" />
              </div>
            ) : models.length === 0 ? (
              <div className="text-center py-20 text-slate-500">
                <Trophy className="w-12 h-12 mx-auto mb-3 opacity-20" />
                <p>No models trained yet. Complete Steps 1-4 to train models.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {/* Leaderboard table */}
                <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden">
                  <table className="w-full text-sm">
                    <thead className="bg-slate-800/80">
                      <tr>
                        <th className="px-4 py-3 text-left text-slate-400 font-medium">#</th>
                        <th className="px-4 py-3 text-left text-slate-400 font-medium">Algorithm</th>
                        <th className="px-4 py-3 text-right text-slate-400 font-medium">Accuracy</th>
                        <th className="px-4 py-3 text-right text-slate-400 font-medium">F1</th>
                        <th className="px-4 py-3 text-right text-slate-400 font-medium">ROC-AUC</th>
                        <th className="px-4 py-3 text-right text-slate-400 font-medium">Inference</th>
                        <th className="px-4 py-3 text-right text-slate-400 font-medium">Size</th>
                        <th className="px-4 py-3 text-center text-slate-400 font-medium">Status</th>
                        <th className="px-4 py-3 text-center text-slate-400 font-medium">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800">
                      {models.map((model, rank) => (
                        <tr
                          key={model.id}
                          className={`cursor-pointer transition-colors hover:bg-slate-800/40 ${selectedModel?.id === model.id ? "bg-indigo-900/20" : ""}`}
                          onClick={() => setSelectedModel(prev => prev?.id === model.id ? null : model)}
                        >
                          <td className="px-4 py-3">
                            <span className={`text-xs font-bold ${rank === 0 ? "text-amber-400" : rank === 1 ? "text-slate-300" : rank === 2 ? "text-amber-700" : "text-slate-500"}`}>
                              #{rank + 1}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-2">
                              {rank === 0 && <Star className="w-3.5 h-3.5 text-amber-400 fill-amber-400" />}
                              <span className="text-slate-200 font-medium">{model.algorithm}</span>
                            </div>
                          </td>
                          <td className="px-4 py-3 text-right">
                            <span className={`font-mono text-sm ${model.accuracy >= 0.9 ? "text-emerald-400" : model.accuracy >= 0.75 ? "text-indigo-400" : "text-slate-400"}`}>
                              {pct(model.accuracy)}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-right font-mono text-sm text-slate-300">{fmt(model.f1_score)}</td>
                          <td className="px-4 py-3 text-right font-mono text-sm text-slate-300">{fmt(model.roc_auc)}</td>
                          <td className="px-4 py-3 text-right font-mono text-xs text-slate-400">{model.inference_time_ms.toFixed(2)}ms</td>
                          <td className="px-4 py-3 text-right font-mono text-xs text-slate-400">{model.model_size_mb.toFixed(2)}MB</td>
                          <td className="px-4 py-3 text-center">
                            <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${DEPLOY_BADGE[model.deployment_status] || "bg-slate-800 text-slate-400 border-slate-700"}`}>
                              {model.deployment_status}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex items-center justify-center gap-2" onClick={e => e.stopPropagation()}>
                              {model.deployment_status !== "production" && (
                                <button
                                  onClick={() => deployModel(model.id)}
                                  disabled={deploying === model.id}
                                  title="Deploy as production"
                                  className="p-1.5 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 transition-colors disabled:opacity-50"
                                >
                                  {deploying === model.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Rocket className="w-3.5 h-3.5" />}
                                </button>
                              )}
                              <button
                                onClick={() => deleteModel(model.id)}
                                disabled={model.deployment_status === "production"}
                                title="Delete"
                                className="p-1.5 rounded-lg bg-red-500/10 hover:bg-red-500/20 text-red-400 transition-colors disabled:opacity-30"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Selected model detail panel */}
                {selectedModel && (
                  <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4">
                    <div className="flex items-center justify-between">
                      <h3 className="text-sm font-bold text-slate-200">{selectedModel.algorithm} — Details</h3>
                      <button onClick={() => setSelectedModel(null)} className="text-slate-500 hover:text-slate-300">
                        <X className="w-4 h-4" />
                      </button>
                    </div>

                    {/* Metrics grid */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                      {[
                        { label: "Accuracy", value: pct(selectedModel.accuracy), color: "text-indigo-400" },
                        { label: "Precision", value: fmt(selectedModel.precision_score), color: "text-blue-400" },
                        { label: "Recall", value: fmt(selectedModel.recall_score), color: "text-violet-400" },
                        { label: "F1 Score", value: fmt(selectedModel.f1_score), color: "text-emerald-400" },
                        { label: "ROC-AUC", value: fmt(selectedModel.roc_auc), color: "text-amber-400" },
                        { label: "Inference", value: `${selectedModel.inference_time_ms.toFixed(2)}ms`, color: "text-slate-300" },
                        { label: "Train Time", value: `${selectedModel.training_time_s.toFixed(1)}s`, color: "text-slate-300" },
                        { label: "Model Size", value: `${selectedModel.model_size_mb.toFixed(2)}MB`, color: "text-slate-300" },
                      ].map(m => (
                        <div key={m.label} className="bg-slate-800/60 rounded-xl p-3">
                          <div className="text-xs text-slate-500 mb-1">{m.label}</div>
                          <div className={`text-lg font-bold ${m.color}`}>{m.value}</div>
                        </div>
                      ))}
                    </div>

                    {/* Feature importance */}
                    {selectedModel.feature_importance && Object.keys(selectedModel.feature_importance).length > 0 && (
                      <div>
                        <h4 className="text-xs font-semibold text-slate-400 mb-3">Feature Importance</h4>
                        <div className="space-y-1.5">
                          {Object.entries(selectedModel.feature_importance)
                            .sort(([, a], [, b]) => b - a)
                            .slice(0, 10)
                            .map(([feat, imp]) => (
                              <FeatureBar
                                key={feat}
                                feature={feat}
                                value={imp}
                                max={Math.max(...Object.values(selectedModel.feature_importance!))}
                              />
                            ))}
                        </div>
                      </div>
                    )}

                    {/* Confusion matrix */}
                    {selectedModel.confusion_matrix_data?.matrix && (
                      <div>
                        <h4 className="text-xs font-semibold text-slate-400 mb-3">Confusion Matrix</h4>
                        <div className="inline-block">
                          <div
                            className="grid gap-1"
                            style={{ gridTemplateColumns: `repeat(${selectedModel.confusion_matrix_data.matrix[0]?.length || 2}, 56px)` }}
                          >
                            {selectedModel.confusion_matrix_data.matrix.map((row, ri) =>
                              row.map((val, ci) => {
                                const max = Math.max(...selectedModel.confusion_matrix_data!.matrix.flat());
                                const intensity = max > 0 ? val / max : 0;
                                const bg = ri === ci
                                  ? `rgba(99, 102, 241, ${0.2 + intensity * 0.6})`
                                  : `rgba(239, 68, 68, ${intensity * 0.5})`;
                                return (
                                  <div key={`${ri}-${ci}`} className="w-14 h-14 flex items-center justify-center rounded-lg text-sm font-bold text-white" style={{ background: bg }}>
                                    {val}
                                  </div>
                                );
                              })
                            )}
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Feature Metadata */}
                    {selectedModel.feature_names && selectedModel.feature_names.length > 0 && (
                      <div>
                        <h4 className="text-xs font-semibold text-slate-400 mb-3">
                          Model Features ({selectedModel.feature_names.length})
                        </h4>
                        <div className="grid grid-cols-2 gap-1">
                          {selectedModel.feature_names.map((f, i) => (
                            <code
                              key={i}
                              className="text-xs bg-slate-800/60 text-slate-300 px-2 py-1 rounded border border-slate-700/40 truncate"
                              title={f}
                            >
                              {f}
                            </code>
                          ))}
                        </div>
                        {/* Compatibility badge */}
                        {selectedModel.feature_names.every((f) =>
                          [
                            "tfidf_similarity","sbert_similarity","skill_match_required",
                            "skill_match_preferred","experience_match","education_score",
                            "ats_score","projects_count_norm","certifications_count_norm",
                            "languages_count_norm","soft_skills_count_norm","has_portfolio",
                            "has_github","years_experience_norm","skills_count_norm","keyword_density",
                          ].includes(f)
                        ) ? (
                          <div className="mt-2 flex items-center gap-1.5 text-xs text-emerald-400">
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            Compatible with Hybrid AI ranking mode
                          </div>
                        ) : (
                          <div className="mt-2 flex items-center gap-1.5 text-xs text-amber-400">
                            <AlertCircle className="w-3.5 h-3.5" />
                            Custom features — Hybrid mode falls back to Traditional
                          </div>
                        )}
                      </div>
                    )}

                    {selectedModel.deployment_status !== "production" && (
                      <button
                        onClick={() => deployModel(selectedModel.id)}
                        disabled={!!deploying}
                        className="w-full py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold flex items-center justify-center gap-2 disabled:opacity-50"
                      >
                        <Rocket className="w-4 h-4" /> Deploy as Production Model
                      </button>
                    )}
                  </motion.div>
                )}
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
