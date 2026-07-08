"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useDropzone } from "react-dropzone";
import {
  Upload, Users, Search, Pin, Trash2, FileText, Brain,
  Star, ChevronRight, Loader2, X, Filter, SortAsc,
  CheckCircle, AlertCircle, Code2, Award, BookOpen,
} from "lucide-react";
import { resumeApi } from "@/lib/api";
import toast from "react-hot-toast";

interface Resume {
  id: string;
  filename: string;
  candidate_name?: string;
  email?: string;
  phone?: string;
  skills: string[];
  experience_years: number;
  completeness_score: number;
  technical_score: number;
  leadership_score: number;
  job_readiness: number;
  ai_summary?: string;
  strengths: string[];
  weaknesses: string[];
  career_path?: string;
  is_pinned: boolean;
  notes?: string;
  status: string;
  uploaded_at: string;
}

function ScoreBadge({ score }: { score: number }) {
  const color =
    score >= 90 ? "text-emerald-400 bg-emerald-400/10" :
    score >= 75 ? "text-indigo-400 bg-indigo-400/10" :
    score >= 55 ? "text-amber-400 bg-amber-400/10" :
    "text-red-400 bg-red-400/10";
  return (
    <span className={`text-xs font-bold px-2 py-0.5 rounded-lg ${color}`}>
      {score.toFixed(0)}%
    </span>
  );
}

function CandidateCard({ resume, onPin, onDelete, onClick }: {
  resume: Resume;
  onPin: (id: string) => void;
  onDelete: (id: string) => void;
  onClick: (r: Resume) => void;
}) {
  return (
    <motion.div
      layout
      initial={{ opacity: 0, scale: 0.96 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.96 }}
      whileHover={{ y: -2 }}
      className="bg-slate-900/80 border border-slate-700/50 rounded-2xl p-5 hover:border-slate-600/50 transition-all cursor-pointer group"
      onClick={() => onClick(resume)}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center text-white font-semibold text-sm">
            {resume.candidate_name?.[0]?.toUpperCase() || "?"}
          </div>
          <div>
            <div className="font-semibold text-white text-sm">{resume.candidate_name || "Unknown"}</div>
            <div className="text-xs text-slate-500 truncate max-w-32">{resume.email || resume.filename}</div>
          </div>
        </div>
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            onClick={(e) => { e.stopPropagation(); onPin(resume.id); }}
            className={`p-1.5 rounded-lg transition-colors ${resume.is_pinned ? "text-amber-400 bg-amber-400/10" : "text-slate-500 hover:text-amber-400 hover:bg-amber-400/10"}`}
          >
            <Pin className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); onDelete(resume.id); }}
            className="p-1.5 rounded-lg text-slate-500 hover:text-red-400 hover:bg-red-400/10 transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Scores */}
      <div className="grid grid-cols-2 gap-2 mb-3">
        <div className="bg-slate-800/60 rounded-xl p-2 text-center">
          <div className="text-xs text-slate-500 mb-0.5">Readiness</div>
          <ScoreBadge score={resume.job_readiness} />
        </div>
        <div className="bg-slate-800/60 rounded-xl p-2 text-center">
          <div className="text-xs text-slate-500 mb-0.5">Technical</div>
          <ScoreBadge score={resume.technical_score} />
        </div>
      </div>

      {/* Stats */}
      <div className="flex items-center gap-3 text-xs text-slate-500 mb-3">
        <span className="flex items-center gap-1">
          <Code2 className="w-3 h-3" />
          {resume.skills?.length ?? 0} skills
        </span>
        <span className="flex items-center gap-1">
          <BookOpen className="w-3 h-3" />
          {resume.experience_years?.toFixed(0)}y exp
        </span>
        {resume.completeness_score > 0 && (
          <span className={`flex items-center gap-1 ${resume.completeness_score >= 80 ? "text-emerald-500" : "text-amber-500"}`}>
            {resume.completeness_score >= 80 ? <CheckCircle className="w-3 h-3" /> : <AlertCircle className="w-3 h-3" />}
            {resume.completeness_score.toFixed(0)}% complete
          </span>
        )}
      </div>

      {/* Top skills */}
      {resume.skills?.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {resume.skills.slice(0, 4).map((s) => (
            <span key={s} className="skill-chip bg-slate-800 text-slate-400">{s}</span>
          ))}
          {resume.skills.length > 4 && (
            <span className="skill-chip bg-slate-800 text-slate-500">+{resume.skills.length - 4}</span>
          )}
        </div>
      )}
    </motion.div>
  );
}

function CandidateDetail({ resume, onClose }: { resume: Resume; onClose: () => void }) {
  return (
    <motion.div
      initial={{ opacity: 0, x: 40 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 40 }}
      className="fixed right-0 top-0 h-full w-96 bg-slate-950 border-l border-slate-700/50 z-50 overflow-y-auto"
    >
      <div className="p-5 border-b border-slate-700/50 flex items-center justify-between sticky top-0 bg-slate-950 z-10">
        <h2 className="font-semibold text-white">Candidate Profile</h2>
        <button onClick={onClose} className="p-2 rounded-xl text-slate-500 hover:text-white hover:bg-white/5 transition-all">
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="p-5 space-y-5">
        {/* Header */}
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center text-white text-xl font-bold">
            {resume.candidate_name?.[0]?.toUpperCase() || "?"}
          </div>
          <div>
            <h3 className="font-bold text-white text-lg">{resume.candidate_name || "Unknown"}</h3>
            <div className="text-sm text-slate-400">{resume.email}</div>
            <div className="text-xs text-slate-500">{resume.phone}</div>
          </div>
        </div>

        {/* AI Summary */}
        {resume.ai_summary && (
          <div className="bg-indigo-500/10 border border-indigo-500/20 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-2 text-indigo-400 text-sm font-medium">
              <Brain className="w-4 h-4" />
              AI Summary
            </div>
            <p className="text-sm text-slate-300 leading-relaxed">{resume.ai_summary}</p>
          </div>
        )}

        {/* Scores grid */}
        <div className="grid grid-cols-2 gap-3">
          {[
            { label: "Technical", value: resume.technical_score, color: "indigo" },
            { label: "Leadership", value: resume.leadership_score, color: "violet" },
            { label: "Job Readiness", value: resume.job_readiness, color: "emerald" },
            { label: "Completeness", value: resume.completeness_score, color: "amber" },
          ].map(({ label, value, color }) => (
            <div key={label} className="bg-slate-800/60 rounded-xl p-3">
              <div className="text-xs text-slate-500 mb-1">{label}</div>
              <div className="flex items-center gap-2">
                <div className="flex-1 h-1.5 bg-slate-700 rounded-full overflow-hidden">
                  <div
                    className={`h-full bg-${color}-500 rounded-full transition-all`}
                    style={{ width: `${value}%` }}
                  />
                </div>
                <span className="text-xs font-bold text-white">{value?.toFixed(0)}%</span>
              </div>
            </div>
          ))}
        </div>

        {/* Career Path */}
        {resume.career_path && (
          <div>
            <div className="text-xs text-slate-500 mb-2 uppercase tracking-wide">Career Path</div>
            <div className="text-sm text-slate-300 bg-slate-800/50 rounded-xl p-3">{resume.career_path}</div>
          </div>
        )}

        {/* Strengths */}
        {resume.strengths?.length > 0 && (
          <div>
            <div className="text-xs text-slate-500 mb-2 uppercase tracking-wide">Strengths</div>
            <div className="space-y-1.5">
              {resume.strengths.map((s) => (
                <div key={s} className="flex items-start gap-2 text-sm text-slate-300">
                  <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                  {s}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Weaknesses */}
        {resume.weaknesses?.length > 0 && (
          <div>
            <div className="text-xs text-slate-500 mb-2 uppercase tracking-wide">Areas to Improve</div>
            <div className="space-y-1.5">
              {resume.weaknesses.map((w) => (
                <div key={w} className="flex items-start gap-2 text-sm text-slate-300">
                  <AlertCircle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
                  {w}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Skills */}
        {resume.skills?.length > 0 && (
          <div>
            <div className="text-xs text-slate-500 mb-2 uppercase tracking-wide">Skills ({resume.skills.length})</div>
            <div className="flex flex-wrap gap-1.5">
              {resume.skills.map((s) => (
                <span key={s} className="skill-matched">{s}</span>
              ))}
            </div>
          </div>
        )}
      </div>
    </motion.div>
  );
}

export default function CandidatesPage() {
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<Resume | null>(null);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);

  const fetchResumes = useCallback(async () => {
    try {
      const data = await resumeApi.list({ page, page_size: 20, search: search || undefined });
      setResumes(data.items || []);
      setTotal(data.total || 0);
    } catch {
      toast.error("Failed to load resumes");
    } finally {
      setLoading(false);
    }
  }, [page, search]);

  useEffect(() => {
    fetchResumes();
  }, [fetchResumes]);

  const onDrop = useCallback(async (files: File[]) => {
    if (!files.length) return;
    setUploading(true);
    setUploadProgress(0);
    try {
      const uploaded = await resumeApi.upload(files, setUploadProgress);
      toast.success(`${uploaded.length} resume(s) uploaded and parsed!`);
      fetchResumes();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Upload failed";
      toast.error(msg);
    } finally {
      setUploading(false);
      setUploadProgress(0);
    }
  }, [fetchResumes]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "application/pdf": [".pdf"], "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"], "text/plain": [".txt"] },
    multiple: true,
  });

  const handlePin = async (id: string) => {
    try {
      await resumeApi.pin(id);
      setResumes((prev) => prev.map((r) => (r.id === id ? { ...r, is_pinned: !r.is_pinned } : r)));
    } catch { toast.error("Failed to pin"); }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this resume?")) return;
    try {
      await resumeApi.delete(id);
      setResumes((prev) => prev.filter((r) => r.id !== id));
      if (selected?.id === id) setSelected(null);
      toast.success("Resume deleted");
    } catch { toast.error("Delete failed"); }
  };

  const filtered = resumes.filter((r) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      (r.candidate_name || "").toLowerCase().includes(q) ||
      (r.email || "").toLowerCase().includes(q) ||
      (r.skills || []).some((s) => s.toLowerCase().includes(q))
    );
  });

  return (
    <div className="space-y-6 max-w-7xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Candidates</h1>
          <p className="text-slate-400 text-sm mt-0.5">{total} resumes in your talent pool</p>
        </div>
      </div>

      {/* Upload zone */}
      <div
        {...getRootProps()}
        className={`relative border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all ${
          isDragActive
            ? "border-indigo-500 bg-indigo-500/10"
            : "border-slate-700 bg-slate-900/40 hover:border-slate-600 hover:bg-slate-900/60"
        }`}
      >
        <input {...getInputProps()} />
        {uploading ? (
          <div className="flex flex-col items-center gap-3">
            <Loader2 className="w-8 h-8 text-indigo-400 animate-spin" />
            <p className="text-slate-300 text-sm">Parsing resumes... {uploadProgress}%</p>
            <div className="w-48 h-1.5 bg-slate-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-indigo-500 to-violet-500 rounded-full transition-all"
                style={{ width: `${uploadProgress}%` }}
              />
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3">
            <div className={`w-12 h-12 rounded-2xl flex items-center justify-center transition-all ${isDragActive ? "bg-indigo-500" : "bg-slate-800"}`}>
              <Upload className={`w-6 h-6 ${isDragActive ? "text-white" : "text-slate-400"}`} />
            </div>
            <div>
              <p className="text-slate-300 font-medium">
                {isDragActive ? "Drop files here!" : "Drag & drop resumes, or click to browse"}
              </p>
              <p className="text-slate-500 text-sm mt-1">Supports PDF, DOCX, TXT — up to 10MB each</p>
            </div>
          </div>
        )}
      </div>

      {/* Search */}
      <div className="flex items-center gap-3">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by name, email, or skill..."
            className="w-full bg-slate-900/80 border border-slate-700/50 rounded-xl pl-10 pr-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 text-sm"
          />
        </div>
        <button className="flex items-center gap-2 bg-slate-900/80 border border-slate-700/50 rounded-xl px-4 py-2.5 text-sm text-slate-400 hover:text-white transition-all">
          <Filter className="w-4 h-4" />
          Filters
        </button>
      </div>

      {/* Grid */}
      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="bg-slate-900/80 border border-slate-700/50 rounded-2xl p-5 h-48 shimmer" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <Users className="w-16 h-16 text-slate-700 mb-4" />
          <h3 className="text-lg font-semibold text-slate-400">No candidates found</h3>
          <p className="text-slate-500 text-sm mt-1">
            {search ? "Try a different search term" : "Upload resumes to get started"}
          </p>
        </div>
      ) : (
        <AnimatePresence mode="popLayout">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {filtered.map((r) => (
              <CandidateCard
                key={r.id}
                resume={r}
                onPin={handlePin}
                onDelete={handleDelete}
                onClick={setSelected}
              />
            ))}
          </div>
        </AnimatePresence>
      )}

      {/* Detail panel */}
      <AnimatePresence>
        {selected && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/40 backdrop-blur-sm z-40"
              onClick={() => setSelected(null)}
            />
            <CandidateDetail resume={selected} onClose={() => setSelected(null)} />
          </>
        )}
      </AnimatePresence>
    </div>
  );
}
