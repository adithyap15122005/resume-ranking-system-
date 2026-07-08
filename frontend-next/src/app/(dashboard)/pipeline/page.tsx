"use client";

import { useCallback, useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { DragDropContext, Droppable, Draggable, DropResult } from "@hello-pangea/dnd";
import { GripVertical, ChevronDown, Users, Loader2 } from "lucide-react";
import { jobApi } from "@/lib/api";
import toast from "react-hot-toast";

const STAGES = [
  { id: "applied",     label: "Applied",     color: "border-slate-500/40 bg-slate-500/5" },
  { id: "screening",   label: "Screening",   color: "border-blue-500/40 bg-blue-500/5" },
  { id: "shortlisted", label: "Shortlisted", color: "border-indigo-500/40 bg-indigo-500/5" },
  { id: "interview",   label: "Interview",   color: "border-violet-500/40 bg-violet-500/5" },
  { id: "technical",   label: "Technical",   color: "border-purple-500/40 bg-purple-500/5" },
  { id: "hr_round",    label: "HR Round",    color: "border-pink-500/40 bg-pink-500/5" },
  { id: "offer",       label: "Offer",       color: "border-amber-500/40 bg-amber-500/5" },
  { id: "accepted",    label: "Accepted",    color: "border-emerald-500/40 bg-emerald-500/5" },
];

const STAGE_BADGE: Record<string, string> = {
  applied:     "bg-slate-500/20 text-slate-400",
  screening:   "bg-blue-500/20 text-blue-400",
  shortlisted: "bg-indigo-500/20 text-indigo-400",
  interview:   "bg-violet-500/20 text-violet-400",
  technical:   "bg-purple-500/20 text-purple-400",
  hr_round:    "bg-pink-500/20 text-pink-400",
  offer:       "bg-amber-500/20 text-amber-400",
  accepted:    "bg-emerald-500/20 text-emerald-400",
};

interface Candidate {
  id: string;           // RankingResult.id (row PK)
  resume_id: string;    // actual Resume FK — used for pipeline API calls
  candidate_name?: string;
  candidate_email?: string;
  // similarity_score is 0–100 from backend
  similarity_score: number;
  pipeline_stage: string;
  rank: number;
}

interface ColumnMap {
  [stage: string]: Candidate[];
}

function ScoreDot({ score100 }: { score100: number }) {
  const color =
    score100 >= 85 ? "bg-emerald-400" :
    score100 >= 70 ? "bg-indigo-400" :
    score100 >= 55 ? "bg-amber-400" : "bg-red-400";
  return <div className={`w-2 h-2 rounded-full ${color} flex-shrink-0`} />;
}

export default function PipelinePage() {
  const [jobs, setJobs] = useState<{ id: string; title: string }[]>([]);
  const [selectedJob, setSelectedJob] = useState("");
  const [columns, setColumns] = useState<ColumnMap>({});
  const [loading, setLoading] = useState(false);
  const [jobsLoading, setJobsLoading] = useState(true);
  const [moving, setMoving] = useState(false);

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
      const data: Candidate[] = await jobApi.getRankings(jobId);
      const grouped: ColumnMap = {};
      STAGES.forEach((s) => { grouped[s.id] = []; });
      (Array.isArray(data) ? data : []).forEach((c) => {
        const stage = c.pipeline_stage || "applied";
        if (!grouped[stage]) grouped[stage] = [];
        grouped[stage].push(c);
      });
      setColumns(grouped);
    } catch {
      toast.error("Failed to load pipeline");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selectedJob) fetchRankings(selectedJob);
  }, [selectedJob, fetchRankings]);

  const onDragEnd = async (result: DropResult) => {
    const { source, destination, draggableId } = result;
    if (!destination || destination.droppableId === source.droppableId) return;

    const srcStage = source.droppableId;
    const dstStage = destination.droppableId;

    // Find the candidate being moved so we can use resume_id for the API call
    const srcItems = [...(columns[srcStage] || [])];
    const [moved] = srcItems.splice(source.index, 1);
    const dstItems = [...(columns[dstStage] || [])];
    dstItems.splice(destination.index, 0, { ...moved, pipeline_stage: dstStage });

    // Optimistic UI update
    setColumns((prev) => ({
      ...prev,
      [srcStage]: srcItems,
      [dstStage]: dstItems,
    }));

    // draggableId === resume_id (see key below)
    setMoving(true);
    try {
      await jobApi.movePipeline(selectedJob, draggableId, dstStage);
    } catch {
      toast.error("Failed to move candidate");
      fetchRankings(selectedJob);
    } finally {
      setMoving(false);
    }
  };

  const totalCandidates = Object.values(columns).reduce((sum, arr) => sum + arr.length, 0);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Hiring Pipeline</h1>
          <p className="text-slate-400 text-sm mt-0.5">
            {totalCandidates} candidates across {STAGES.length} stages
          </p>
        </div>
        <div className="flex items-center gap-3">
          {moving && (
            <div className="flex items-center gap-2 text-sm text-slate-400">
              <Loader2 className="w-4 h-4 animate-spin" /> Saving...
            </div>
          )}
          <div className="relative">
            <select
              value={selectedJob}
              onChange={(e) => setSelectedJob(e.target.value)}
              className="bg-slate-900/80 border border-slate-700/50 rounded-xl pl-4 pr-8 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 appearance-none"
            >
              {jobsLoading ? (
                <option>Loading jobs...</option>
              ) : jobs.length === 0 ? (
                <option value="">No jobs available</option>
              ) : (
                jobs.map((j) => <option key={j.id} value={j.id}>{j.title}</option>)
              )}
            </select>
            <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
          </div>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center gap-4 overflow-x-auto pb-4">
          {STAGES.map((s) => (
            <div key={s.id} className="flex-shrink-0 w-64 bg-slate-900/80 border border-slate-700/50 rounded-2xl p-4 h-80 shimmer" />
          ))}
        </div>
      ) : totalCandidates === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <Users className="w-16 h-16 text-slate-700 mb-4" />
          <h3 className="text-lg font-semibold text-slate-400">No candidates in pipeline</h3>
          <p className="text-slate-500 text-sm mt-1">
            Go to Rankings and run AI ranking to populate the pipeline
          </p>
        </div>
      ) : (
        <DragDropContext onDragEnd={onDragEnd}>
          <div className="flex gap-4 overflow-x-auto pb-4">
            {STAGES.map((stage) => {
              const items = columns[stage.id] || [];
              return (
                <div key={stage.id} className={`flex-shrink-0 w-64 border rounded-2xl ${stage.color}`}>
                  <div className="p-3 border-b border-slate-700/30 flex items-center justify-between">
                    <span className="text-sm font-medium text-white">{stage.label}</span>
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-lg ${STAGE_BADGE[stage.id]}`}>
                      {items.length}
                    </span>
                  </div>
                  <Droppable droppableId={stage.id}>
                    {(provided, snapshot) => (
                      <div
                        ref={provided.innerRef}
                        {...provided.droppableProps}
                        className={`p-2 min-h-40 space-y-2 transition-colors rounded-b-2xl ${
                          snapshot.isDraggingOver ? "bg-white/5" : ""
                        }`}
                      >
                        <AnimatePresence>
                          {items.map((candidate, index) => (
                            // Use resume_id as draggableId so onDragEnd can pass it to the API
                            <Draggable
                              key={candidate.resume_id}
                              draggableId={candidate.resume_id}
                              index={index}
                            >
                              {(prov, snap) => (
                                <div
                                  ref={prov.innerRef}
                                  {...prov.draggableProps}
                                  className={`bg-slate-900 border border-slate-700/50 rounded-xl p-3 select-none transition-shadow ${
                                    snap.isDragging
                                      ? "shadow-xl border-indigo-500/50 rotate-1"
                                      : "hover:border-slate-600/50"
                                  }`}
                                >
                                  <div className="flex items-center gap-2">
                                    <div
                                      {...prov.dragHandleProps}
                                      className="text-slate-600 hover:text-slate-400 cursor-grab active:cursor-grabbing"
                                    >
                                      <GripVertical className="w-3.5 h-3.5" />
                                    </div>
                                    <div className="w-7 h-7 rounded-full bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center text-white text-xs font-semibold flex-shrink-0">
                                      {candidate.candidate_name?.[0]?.toUpperCase() || "?"}
                                    </div>
                                    <div className="flex-1 min-w-0">
                                      <div className="text-xs font-medium text-white truncate">
                                        {candidate.candidate_name || "Unknown"}
                                      </div>
                                      <div className="text-xs text-slate-500 truncate">{candidate.candidate_email}</div>
                                    </div>
                                  </div>
                                  <div className="flex items-center justify-between mt-2 pt-2 border-t border-slate-800">
                                    <div className="flex items-center gap-1.5">
                                      <ScoreDot score100={candidate.similarity_score || 0} />
                                      <span className="text-xs text-slate-400">
                                        {Math.round(candidate.similarity_score || 0)}% match
                                      </span>
                                    </div>
                                    <span className="text-xs text-slate-600">#{candidate.rank}</span>
                                  </div>
                                </div>
                              )}
                            </Draggable>
                          ))}
                        </AnimatePresence>
                        {provided.placeholder}
                        {items.length === 0 && !snapshot.isDraggingOver && (
                          <div className="flex items-center justify-center h-20 text-slate-700 text-xs">
                            Drop here
                          </div>
                        )}
                      </div>
                    )}
                  </Droppable>
                </div>
              );
            })}
          </div>
        </DragDropContext>
      )}
    </div>
  );
}
