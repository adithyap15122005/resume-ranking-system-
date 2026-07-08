"use client";

import { useCallback, useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  Briefcase, Plus, Search, Trophy, Zap, Loader2, X,
  MapPin, Clock, DollarSign, Users, ChevronRight,
  Building2, Star, Trash2, Edit3,
} from "lucide-react";
import { jobApi } from "@/lib/api";
import toast from "react-hot-toast";

interface Job {
  id: string;
  title: string;
  department?: string;
  location?: string;
  employment_type: string;
  experience_level: string;
  salary_min?: number;
  salary_max?: number;
  status: string;
  required_skills: string[];
  preferred_skills: string[];
  candidate_count: number;
  created_at: string;
}

const schema = z.object({
  title: z.string().min(2, "Job title required"),
  description: z.string().min(50, "Description must be at least 50 characters"),
  department: z.string().optional(),
  location: z.string().optional(),
  employment_type: z.enum(["full_time", "part_time", "contract", "internship"]),
  experience_level: z.enum(["entry", "mid", "senior", "lead", "executive"]),
  salary_min: z.number().optional(),
  salary_max: z.number().optional(),
  required_skills: z.string().optional(),
  preferred_skills: z.string().optional(),
  experience_requirement: z.string().optional(),
  education_requirement: z.string().optional(),
});
type FormData = z.infer<typeof schema>;

const STATUS_COLORS: Record<string, string> = {
  active: "text-emerald-400 bg-emerald-400/10",
  draft: "text-slate-400 bg-slate-400/10",
  paused: "text-amber-400 bg-amber-400/10",
  closed: "text-red-400 bg-red-400/10",
};

const EMP_LABELS: Record<string, string> = {
  full_time: "Full Time",
  part_time: "Part Time",
  contract: "Contract",
  internship: "Internship",
};

const EXP_LABELS: Record<string, string> = {
  entry: "Entry Level",
  mid: "Mid Level",
  senior: "Senior",
  lead: "Lead",
  executive: "Executive",
};

function JobCard({ job, onDelete, onRank, onView }: {
  job: Job;
  onDelete: (id: string) => void;
  onRank: (id: string) => void;
  onView: (job: Job) => void;
}) {
  const [ranking, setRanking] = useState(false);

  const handleRank = async (e: React.MouseEvent) => {
    e.stopPropagation();
    setRanking(true);
    try {
      await onRank(job.id);
    } finally {
      setRanking(false);
    }
  };

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.96 }}
      whileHover={{ y: -2 }}
      className="bg-slate-900/80 border border-slate-700/50 rounded-2xl p-5 hover:border-slate-600/50 transition-all cursor-pointer group"
      onClick={() => onView(job)}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500/20 to-violet-500/20 border border-indigo-500/20 flex items-center justify-center">
            <Briefcase className="w-5 h-5 text-indigo-400" />
          </div>
          <div>
            <h3 className="font-semibold text-white text-sm leading-tight">{job.title}</h3>
            {job.department && (
              <span className="text-xs text-slate-500">{job.department}</span>
            )}
          </div>
        </div>
        <span className={`text-xs font-medium px-2 py-0.5 rounded-lg capitalize ${STATUS_COLORS[job.status] || STATUS_COLORS.draft}`}>
          {job.status}
        </span>
      </div>

      <div className="flex flex-wrap gap-2 mb-4">
        {job.location && (
          <span className="flex items-center gap-1 text-xs text-slate-500">
            <MapPin className="w-3 h-3" />{job.location}
          </span>
        )}
        <span className="flex items-center gap-1 text-xs text-slate-500">
          <Clock className="w-3 h-3" />{EMP_LABELS[job.employment_type]}
        </span>
        <span className="text-xs text-slate-500">{EXP_LABELS[job.experience_level]}</span>
        {job.salary_min && job.salary_max && (
          <span className="flex items-center gap-1 text-xs text-emerald-500">
            <DollarSign className="w-3 h-3" />
            {(job.salary_min / 1000).toFixed(0)}k–{(job.salary_max / 1000).toFixed(0)}k
          </span>
        )}
      </div>

      {job.required_skills?.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-4">
          {job.required_skills.slice(0, 4).map((s) => (
            <span key={s} className="skill-chip bg-slate-800 text-slate-400">{s}</span>
          ))}
          {job.required_skills.length > 4 && (
            <span className="skill-chip bg-slate-800 text-slate-500">+{job.required_skills.length - 4}</span>
          )}
        </div>
      )}

      <div className="flex items-center justify-between pt-3 border-t border-slate-700/50">
        <div className="flex items-center gap-1 text-xs text-slate-500">
          <Users className="w-3.5 h-3.5" />
          {job.candidate_count} candidates
        </div>
        <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            onClick={handleRank}
            disabled={ranking}
            className="flex items-center gap-1.5 text-xs bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-400 px-2.5 py-1.5 rounded-lg transition-all"
          >
            {ranking ? <Loader2 className="w-3 h-3 animate-spin" /> : <Zap className="w-3 h-3" />}
            Rank
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); if (confirm("Delete this job?")) onDelete(job.id); }}
            className="p-1.5 rounded-lg text-slate-500 hover:text-red-400 hover:bg-red-400/10 transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </motion.div>
  );
}

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<Job | null>(null);

  const { register, handleSubmit, reset, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { employment_type: "full_time", experience_level: "mid" },
  });

  const fetchJobs = useCallback(async () => {
    try {
      const data = await jobApi.list();
      setJobs(Array.isArray(data) ? data : []);
    } catch {
      toast.error("Failed to load jobs");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchJobs(); }, [fetchJobs]);

  const onSubmit = async (data: FormData) => {
    setSubmitting(true);
    try {
      const payload = {
        ...data,
        required_skills: data.required_skills
          ? data.required_skills.split(",").map((s) => s.trim()).filter(Boolean)
          : [],
        preferred_skills: data.preferred_skills
          ? data.preferred_skills.split(",").map((s) => s.trim()).filter(Boolean)
          : [],
        salary_min: data.salary_min || undefined,
        salary_max: data.salary_max || undefined,
      };
      await jobApi.create(payload);
      toast.success("Job created!");
      reset();
      setShowForm(false);
      fetchJobs();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Failed to create job";
      toast.error(msg);
    } finally {
      setSubmitting(false);
    }
  };

  const handleRank = async (jobId: string) => {
    try {
      const results = await jobApi.rank(jobId);
      toast.success(`Ranked ${results.length} candidates!`);
      fetchJobs();
    } catch {
      toast.error("Ranking failed");
    }
  };

  const handleDelete = async (jobId: string) => {
    try {
      await jobApi.delete(jobId);
      setJobs((prev) => prev.filter((j) => j.id !== jobId));
      if (selected?.id === jobId) setSelected(null);
      toast.success("Job deleted");
    } catch { toast.error("Delete failed"); }
  };

  const filtered = jobs.filter((j) =>
    !search || j.title.toLowerCase().includes(search.toLowerCase()) ||
    (j.department || "").toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6 max-w-7xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Jobs</h1>
          <p className="text-slate-400 text-sm mt-0.5">{jobs.length} open positions</p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-2 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white px-4 py-2.5 rounded-xl text-sm font-medium transition-all shadow-glow"
        >
          <Plus className="w-4 h-4" />
          Post New Job
        </button>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search jobs..."
          className="w-full bg-slate-900/80 border border-slate-700/50 rounded-xl pl-10 pr-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 text-sm"
        />
      </div>

      {/* Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="bg-slate-900/80 border border-slate-700/50 rounded-2xl p-5 h-52 shimmer" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <Briefcase className="w-16 h-16 text-slate-700 mb-4" />
          <h3 className="text-lg font-semibold text-slate-400">No jobs found</h3>
          <p className="text-slate-500 text-sm mt-1 mb-6">
            {search ? "Try a different search" : "Post your first job to start ranking candidates"}
          </p>
          {!search && (
            <button
              onClick={() => setShowForm(true)}
              className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2.5 rounded-xl text-sm font-medium transition-all"
            >
              <Plus className="w-4 h-4" /> Post a Job
            </button>
          )}
        </div>
      ) : (
        <AnimatePresence mode="popLayout">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filtered.map((job) => (
              <JobCard key={job.id} job={job} onDelete={handleDelete} onRank={handleRank} onView={setSelected} />
            ))}
          </div>
        </AnimatePresence>
      )}

      {/* Create Job Modal */}
      <AnimatePresence>
        {showForm && (
          <>
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40" onClick={() => setShowForm(false)} />
            <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.95 }}
              className="fixed inset-0 z-50 flex items-center justify-center p-4">
              <div className="bg-slate-950 border border-slate-700 rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
                <div className="flex items-center justify-between p-6 border-b border-slate-700/50">
                  <h2 className="text-lg font-semibold text-white">Post New Job</h2>
                  <button onClick={() => setShowForm(false)} className="p-2 rounded-xl text-slate-500 hover:text-white hover:bg-white/5 transition-all">
                    <X className="w-4 h-4" />
                  </button>
                </div>
                <form onSubmit={handleSubmit(onSubmit)} className="p-6 space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="col-span-2">
                      <label className="block text-sm font-medium text-slate-300 mb-1.5">Job Title *</label>
                      <input {...register("title")} placeholder="Senior Backend Engineer" className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50" />
                      {errors.title && <p className="mt-1 text-xs text-red-400">{errors.title.message}</p>}
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-300 mb-1.5">Department</label>
                      <input {...register("department")} placeholder="Engineering" className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-300 mb-1.5">Location</label>
                      <input {...register("location")} placeholder="Remote / San Francisco" className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-300 mb-1.5">Employment Type</label>
                      <select {...register("employment_type")} className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50 appearance-none">
                        <option value="full_time">Full Time</option>
                        <option value="part_time">Part Time</option>
                        <option value="contract">Contract</option>
                        <option value="internship">Internship</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-300 mb-1.5">Experience Level</label>
                      <select {...register("experience_level")} className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50 appearance-none">
                        <option value="entry">Entry Level</option>
                        <option value="mid">Mid Level</option>
                        <option value="senior">Senior</option>
                        <option value="lead">Lead</option>
                        <option value="executive">Executive</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-300 mb-1.5">Salary Min ($)</label>
                      <input {...register("salary_min", { valueAsNumber: true })} type="number" placeholder="80000" className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-300 mb-1.5">Salary Max ($)</label>
                      <input {...register("salary_max", { valueAsNumber: true })} type="number" placeholder="120000" className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50" />
                    </div>
                    <div className="col-span-2">
                      <label className="block text-sm font-medium text-slate-300 mb-1.5">Required Skills (comma-separated)</label>
                      <input {...register("required_skills")} placeholder="Python, FastAPI, PostgreSQL, Docker" className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50" />
                    </div>
                    <div className="col-span-2">
                      <label className="block text-sm font-medium text-slate-300 mb-1.5">Preferred Skills</label>
                      <input {...register("preferred_skills")} placeholder="Kubernetes, Redis, GraphQL" className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50" />
                    </div>
                    <div className="col-span-2">
                      <label className="block text-sm font-medium text-slate-300 mb-1.5">Job Description *</label>
                      <textarea
                        {...register("description")}
                        rows={6}
                        placeholder="We are looking for a Senior Backend Engineer to join our growing team. You will be responsible for designing and implementing scalable microservices..."
                        className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 resize-none"
                      />
                      {errors.description && <p className="mt-1 text-xs text-red-400">{errors.description.message}</p>}
                    </div>
                  </div>
                  <div className="flex justify-end gap-3 pt-2">
                    <button type="button" onClick={() => setShowForm(false)} className="px-4 py-2.5 rounded-xl text-slate-400 hover:text-white border border-slate-700 hover:border-slate-600 transition-all text-sm">
                      Cancel
                    </button>
                    <button type="submit" disabled={submitting} className="flex items-center gap-2 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white px-6 py-2.5 rounded-xl text-sm font-medium transition-all disabled:opacity-60">
                      {submitting ? <><Loader2 className="w-4 h-4 animate-spin" />Creating...</> : "Create Job"}
                    </button>
                  </div>
                </form>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}
