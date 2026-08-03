"use client";

import { useState, useRef, useEffect } from "react";
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { Filter, MessageSquare, Tag, Zap, BarChart2, Loader2, CheckCircle, XCircle } from "lucide-react";

type Insight = {
  id: string;
  chunk_id: string;
  decision_driver: string;
  purchase_context: string;
  evidence_quote: string;
  run_id: string;
  created_at: string;
  chunk_text: string;
  review_id: string;
  source: string;
};

function SourceBadge({ source }: { source: string }) {
  const isReddit = source?.toLowerCase().includes("reddit");
  const isPlay = source?.toLowerCase().includes("play") || source?.toLowerCase().includes("google");

  if (isReddit) {
    return (
      <span className="px-3 py-1 bg-orange-900/40 text-orange-300 text-xs font-semibold rounded-full border border-orange-800/50 flex items-center gap-1">
        <span>↑</span> Reddit
      </span>
    );
  }
  if (isPlay) {
    return (
      <span className="px-3 py-1 bg-green-900/40 text-green-300 text-xs font-semibold rounded-full border border-green-800/50 flex items-center gap-1">
        <span>▶</span> Play Store
      </span>
    );
  }
  return (
    <span className="px-3 py-1 bg-gray-700/40 text-gray-400 text-xs font-semibold rounded-full border border-gray-700/50">
      {source || "Unknown"}
    </span>
  );
}

function formatLabel(str: string) {
  if (!str || str.toLowerCase() === "none") return "Not Mentioned";
  return str
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

const BLINKIT_YELLOW = "#F6C22E";
const COLORS = [BLINKIT_YELLOW, "#ff6b6b", "#4ecdc4", "#45b7d1", "#96ceb4", "#ffeead"];

import { Database, Play, Square, RefreshCcw } from "lucide-react";

export default function DashboardClient({ 
  initialInsights, 
  rawReviewsCount,
  availableRuns = [],
  activeRunId = ""
}: { 
  initialInsights: Insight[], 
  rawReviewsCount: number,
  availableRuns?: string[],
  activeRunId?: string
}) {
  const [activeTab, setActiveTab] = useState<"stage1" | "feed" | "stage4" | "stage5">("feed");
  const [filterDriver, setFilterDriver] = useState<string>("All");
  const [filterContext, setFilterContext] = useState<string>("All");
  const [filterSource, setFilterSource] = useState<string>("All");

  const pmRelevantCount = new Set(initialInsights.map(i => i.review_id)).size;

  // Stage 4 state
  const [stage4Status, setStage4Status] = useState<"idle" | "loading" | "preview" | "saving" | "saved" | "error">("idle");
  const [stage4Scores, setStage4Scores] = useState<any>(null);
  const [stage4Error, setStage4Error] = useState<string>("");

  async function runStage4() {
    setStage4Status("loading");
    setStage4Error("");
    try {
      const res = await fetch(`/api/score${activeRunId ? `?run_id=${activeRunId}` : ""}`);
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setStage4Scores(data);
      setStage4Status("preview");
    } catch (e: any) {
      setStage4Error(e.message || "Unknown error");
      setStage4Status("error");
    }
  }

  async function confirmSave() {
    if (!stage4Scores) return;
    setStage4Status("saving");
    try {
      const res = await fetch(`/api/score${activeRunId ? `?run_id=${activeRunId}` : ""}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(stage4Scores),
      });
      if (!res.ok) throw new Error(await res.text());
      setStage4Status("saved");
    } catch (e: any) {
      setStage4Error(e.message || "Save failed");
      setStage4Status("error");
    }
  }

  function discardScores() {
    setStage4Scores(null);
    setStage4Status("idle");
  }

  // Stage 5 state
  const [stage5Status, setStage5Status] = useState<"idle" | "loading" | "loaded" | "error">("idle");
  const [stage5Reports, setStage5Reports] = useState<any[]>([]);
  const [stage5Error, setStage5Error] = useState<string>("");

  async function loadStage5() {
    setStage5Status("loading");
    setStage5Error("");
    try {
      const res = await fetch(`/api/synthesize${activeRunId ? `?run_id=${activeRunId}` : ""}`);
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setStage5Reports(data);
      setStage5Status("loaded");
    } catch (e: any) {
      setStage5Error(e.message || "Failed to load reports");
      setStage5Status("error");
    }
  }

  const [synthesisLogs, setSynthesisLogs] = useState<string[]>([]);
  const [isSynthesizing, setIsSynthesizing] = useState(false);
  const synthLogsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    synthLogsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [synthesisLogs]);

  async function startSynthesis() {
    setIsSynthesizing(true);
    setSynthesisLogs([]);
    try {
      const res = await fetch("/api/synthesize/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ run_id: activeRunId })
      });
      if (!res.ok || !res.body) throw new Error(await res.text());

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        const chunk = decoder.decode(value);
        const lines = chunk.split("\n");
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const payload = JSON.parse(line.substring(6));
              if (payload.event === "log") {
                setSynthesisLogs(prev => [...prev, payload.data]);
              } else if (payload.event === "done") {
                setIsSynthesizing(false);
                loadStage5();
              } else if (payload.event === "error") {
                setIsSynthesizing(false);
                setSynthesisLogs(prev => [...prev, `[ERROR] ${payload.data}`]);
              }
            } catch (e) {}
          }
        }
      }
    } catch (e: any) {
      setIsSynthesizing(false);
      setSynthesisLogs(prev => [...prev, `[FATAL] ${e.message}`]);
    }
  }
  const filteredInsights = initialInsights.filter((item) => {
    const matchDriver = filterDriver === "All" || item.decision_driver === filterDriver;
    const matchContext = filterContext === "All" || item.purchase_context === filterContext;
    const matchSource = filterSource === "All" || item.source === filterSource;
    return matchDriver && matchContext && matchSource;
  });

  const driverCounts = filteredInsights.reduce((acc, item) => {
    acc[item.decision_driver] = (acc[item.decision_driver] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const driverChartData = Object.entries(driverCounts)
    .map(([name, value]) => ({ name: formatLabel(name), value }))
    .sort((a, b) => b.value - a.value);

  const contextCounts = filteredInsights.reduce((acc, item) => {
    acc[item.purchase_context] = (acc[item.purchase_context] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const contextChartData = Object.entries(contextCounts)
    .map(([name, value]) => ({ name: formatLabel(name), value }))
    .sort((a, b) => b.value - a.value);

  const uniqueDrivers = Array.from(new Set(initialInsights.map((i) => i.decision_driver))).sort();
  const uniqueContexts = Array.from(new Set(initialInsights.map((i) => i.purchase_context))).sort();
  const uniqueSources = Array.from(new Set(initialInsights.map((i) => i.source).filter(Boolean))).sort();

  // ---------------------------------------------------------
  // Stage 1 Pipeline Runner Logic
  // ---------------------------------------------------------
  const [sources, setSources] = useState<Record<string, boolean>>({ app_store: false, play_store: false, reddit: false });
  const [pipelineStatus, setPipelineStatus] = useState<"idle" | "running" | "error" | "done">("idle");
  const [pipelineLogs, setPipelineLogs] = useState<string[]>([]);
  const [currentStage, setCurrentStage] = useState<string>("");
  const [abortController, setAbortController] = useState<AbortController | null>(null);

  const startPipeline = async () => {
    const selected = Object.keys(sources).filter(k => sources[k]);
    if (selected.length === 0) return;

    setPipelineStatus("running");
    setPipelineLogs(["Initializing Pipeline..."]);
    setCurrentStage("stage1");

    const ctrl = new AbortController();
    setAbortController(ctrl);

    try {
      const res = await fetch("/api/pipeline/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sources: selected }),
        signal: ctrl.signal
      });

      if (!res.ok || !res.body) throw new Error(await res.text());

      const reader = res.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split("\n");

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const payload = JSON.parse(line.substring(6));
              if (payload.event === "log") {
                setPipelineLogs(prev => [...prev, payload.data]);
              } else if (payload.event === "stage") {
                setCurrentStage(payload.data);
              } else if (payload.event === "error") {
                setPipelineLogs(prev => [...prev, `[FATAL ERROR] ${payload.data}`]);
                setPipelineStatus("error");
              } else if (payload.event === "done") {
                setPipelineStatus("done");
                setCurrentStage("done");
              }
            } catch (e) {}
          }
        }
      }
    } catch (e: any) {
      if (e.name === "AbortError") {
        setPipelineLogs(prev => [...prev, "[SYSTEM] Pipeline aborted by user."]);
        setPipelineStatus("error");
      } else {
        setPipelineLogs(prev => [...prev, `[ERROR] ${e.message || "Unknown Error"}`]);
        setPipelineStatus("error");
      }
    }
  };

  const stopPipeline = () => {
    if (abortController) {
      abortController.abort();
      setAbortController(null);
    }
  };

  return (
    <div className="min-h-screen bg-[var(--background)] text-[var(--foreground)] p-6 font-sans">
      
      {/* Header */}
      <header className="mb-8 border-b border-gray-800 pb-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-[var(--blinkit-yellow)] rounded-lg flex items-center justify-center shadow-lg shadow-yellow-500/20">
            <Zap className="text-black w-6 h-6" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">PM Discovery Engine</h1>
            <p className="text-gray-400 text-sm mt-1">Blinkit Customer Insights Dashboard</p>
          </div>
        </div>
        <div className="flex gap-4">
          
          {/* RUN SELECTOR (TIME MACHINE) */}
          {availableRuns.length > 0 && (
            <div className="flex flex-col items-end border-r border-gray-800 pr-6 mr-2">
              <label className="text-[10px] text-gray-500 uppercase tracking-widest font-bold mb-1">Time Machine</label>
              <select 
                className="bg-[#1a1a1a] border border-gray-700 text-[var(--blinkit-yellow)] text-sm rounded-lg focus:ring-1 focus:ring-[var(--blinkit-yellow)] focus:border-[var(--blinkit-yellow)] block px-3 py-1.5 cursor-pointer font-semibold outline-none transition-colors hover:border-gray-500"
                value={activeRunId}
                onChange={(e) => {
                  window.location.href = `?run_id=${e.target.value}`;
                }}
              >
                {availableRuns.map((id, index) => (
                  <option key={id} value={id}>
                    {index === 0 ? "Original Batch (5.8k Reviews)" : `Live Scrape ${index}`}
                  </option>
                ))}
              </select>
            </div>
          )}

          <div className="bg-gray-900 border border-gray-800 px-4 py-2 rounded-lg flex flex-col items-center">
            <span className="text-xs text-gray-500 uppercase tracking-wider font-semibold">Raw Reviews</span>
            <span className="text-xl font-bold text-gray-300">{rawReviewsCount.toLocaleString()}</span>
          </div>
          <div className="flex items-center text-gray-600">→</div>
          <div className="bg-gray-900 border border-gray-800 px-4 py-2 rounded-lg flex flex-col items-center">
            <span className="text-xs text-gray-500 uppercase tracking-wider font-semibold">PM Relevant</span>
            <span className="text-xl font-bold text-gray-300">{pmRelevantCount}</span>
          </div>
          <div className="flex items-center text-gray-600">→</div>
          <div className="bg-gray-900 border border-[var(--blinkit-yellow)] px-4 py-2 rounded-lg flex flex-col items-center shadow-[0_0_15px_rgba(246,194,46,0.1)]">
            <span className="text-xs text-[var(--blinkit-yellow)] uppercase tracking-wider font-semibold">Annotated Data Points</span>
            <span className="text-xl font-bold text-[var(--blinkit-yellow)]">{initialInsights.length}</span>
          </div>
        </div>
      </header>

      {/* Tab Navigation */}
      <div className="flex gap-2 mb-8 border-b border-gray-800">
        <button
          onClick={() => setActiveTab("stage1")}
          className={`px-5 py-2.5 text-sm font-semibold rounded-t-lg transition-colors flex items-center gap-2 ${
            activeTab === "stage1"
              ? "bg-[#1a1a1a] text-[var(--blinkit-yellow)] border-t border-l border-r border-gray-700"
              : "text-gray-500 hover:text-gray-300"
          }`}
        >
          <Database className="w-4 h-4" />
          Live Pipeline Engine
        </button>
        <button
          onClick={() => setActiveTab("feed")}
          className={`px-5 py-2.5 text-sm font-semibold rounded-t-lg transition-colors ${
            activeTab === "feed"
              ? "bg-[#1a1a1a] text-[var(--blinkit-yellow)] border-t border-l border-r border-gray-700"
              : "text-gray-500 hover:text-gray-300"
          }`}
        >
          Raw Evidence Feed
        </button>
        <button
          onClick={() => setActiveTab("stage4")}
          className={`px-5 py-2.5 text-sm font-semibold rounded-t-lg transition-colors flex items-center gap-2 ${
            activeTab === "stage4"
              ? "bg-[#1a1a1a] text-[var(--blinkit-yellow)] border-t border-l border-r border-gray-700"
              : "text-gray-500 hover:text-gray-300"
          }`}
        >
          <BarChart2 className="w-4 h-4" />
          Quantitative Signals
          {stage4Status === "saved" && <span className="w-2 h-2 rounded-full bg-green-400 ml-1" />}
        </button>
        <button
          onClick={() => { setActiveTab("stage5"); loadStage5(); }}
          className={`px-5 py-2.5 text-sm font-semibold rounded-t-lg transition-colors flex items-center gap-2 ${
            activeTab === "stage5"
              ? "bg-[#1a1a1a] text-[var(--blinkit-yellow)] border-t border-l border-r border-gray-700"
              : "text-gray-500 hover:text-gray-300"
          }`}
        >
          <Zap className="w-4 h-4" />
          LLM Executive Summary
        </button>
      </div>

      {activeTab === "stage1" && (
        <div className="grid grid-cols-12 gap-8 mb-12">
          {/* Left Column: Existing Data */}
          <div className="col-span-5 space-y-6">
            <div className="bg-[#1a1a1a] p-6 rounded-xl border border-gray-800 shadow-xl">
              <h2 className="text-xl font-bold mb-4 flex items-center gap-2 text-white">
                <Database className="w-5 h-5 text-[var(--blinkit-yellow)]" />
                Current Dataset
              </h2>
              <p className="text-gray-400 mb-6 text-sm">
                You are currently viewing the dataset isolated under <strong>{activeRunId.substring(0,8)}...</strong>
                <br/>Any new scrape will generate a fresh dataset without deleting this one.
              </p>
              
              <div className="space-y-4">
                <div className="flex justify-between items-center p-3 bg-gray-900 rounded-lg border border-gray-800">
                  <span className="text-gray-300">Raw Reviews</span>
                  <span className="font-bold">{rawReviewsCount.toLocaleString()}</span>
                </div>
                <div className="flex justify-between items-center p-3 bg-gray-900 rounded-lg border border-gray-800">
                  <span className="text-gray-300">PM Relevant</span>
                  <span className="font-bold">{pmRelevantCount.toLocaleString()}</span>
                </div>
                <div className="flex justify-between items-center p-3 bg-gray-900 rounded-lg border border-[var(--blinkit-yellow)]/30">
                  <span className="text-[var(--blinkit-yellow)]">Annotated Chunks</span>
                  <span className="font-bold text-[var(--blinkit-yellow)]">{initialInsights.length.toLocaleString()}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: Trigger Scrape */}
          <div className="col-span-7">
            <div className="bg-[#111] border border-gray-800 rounded-xl p-8 col-span-2 shadow-2xl relative overflow-hidden">
              <div className="absolute top-0 left-0 w-1 h-full bg-[var(--blinkit-yellow)]"></div>
              <h3 className="text-xl font-bold mb-6 flex items-center gap-2">
                <Zap className="text-[var(--blinkit-yellow)] w-5 h-5" fill="currentColor" />
                Trigger Live Pipeline
              </h3>
              
              <div className="flex gap-4 mb-8">
                {Object.keys(sources).map((key) => (
                  <label key={key} className={`flex items-center gap-2 px-4 py-3 rounded-lg border cursor-pointer transition-all ${sources[key] ? 'border-[var(--blinkit-yellow)] bg-[var(--blinkit-yellow)]/10 text-white' : 'border-gray-700 hover:border-gray-500 text-gray-400'}`}>
                    <input 
                      type="checkbox" 
                      className="hidden" 
                      checked={sources[key]} 
                      onChange={() => setSources(prev => ({...prev, [key]: !prev[key]}))}
                      disabled={pipelineStatus === "running"}
                    />
                    <span className="capitalize font-semibold">{key.replace("_", " ")}</span>
                  </label>
                ))}
              </div>

              <div className="flex items-center gap-4">
                {pipelineStatus === "idle" || pipelineStatus === "error" || pipelineStatus === "done" ? (
                  <button 
                    onClick={startPipeline}
                    disabled={Object.values(sources).every(v => !v)}
                    className={`px-6 py-3 rounded-lg font-bold flex items-center gap-2 transition-all ${
                      Object.values(sources).every(v => !v)
                        ? "bg-gray-800 text-gray-500 cursor-not-allowed border border-gray-700"
                        : "bg-[var(--blinkit-yellow)] text-black hover:bg-yellow-400 shadow-[0_0_20px_rgba(246,194,46,0.6)] border border-yellow-400"
                    }`}
                  >
                    <Play className="w-5 h-5" fill={Object.values(sources).every(v => !v) ? "none" : "currentColor"} />
                    Start Extraction Pipeline
                  </button>
                ) : (
                  <button 
                    onClick={stopPipeline}
                    className="bg-red-500 text-white px-6 py-3 rounded-lg font-bold flex items-center gap-2 hover:bg-red-400 transition-colors"
                  >
                    <Square className="w-5 h-5" fill="currentColor" />
                    Emergency Stop
                  </button>
                )}
              </div>

              {/* Expanding Progress Dashboard */}
              {pipelineStatus !== "idle" && (
                <div className="mt-8 pt-8 border-t border-gray-800 animate-in fade-in slide-in-from-top-4 duration-500">
                  <h3 className="text-sm uppercase tracking-widest text-gray-500 font-bold mb-4">Pipeline Progress</h3>
                  <div className="flex gap-8 mb-6">
                    <div className={`flex items-center gap-2 text-sm font-semibold ${currentStage === 'stage1' ? 'text-[var(--blinkit-yellow)]' : 'text-gray-500'}`}>
                      {currentStage === 'stage1' && <RefreshCcw className="w-4 h-4 animate-spin" />}
                      1. Scraping
                    </div>
                    <div className={`flex items-center gap-2 text-sm font-semibold ${currentStage === 'stage2' ? 'text-[var(--blinkit-yellow)]' : 'text-gray-500'}`}>
                      {currentStage === 'stage2' && <RefreshCcw className="w-4 h-4 animate-spin" />}
                      2. Vocab Filter
                    </div>
                    <div className={`flex items-center gap-2 text-sm font-semibold ${currentStage === 'stage3' ? 'text-[var(--blinkit-yellow)]' : 'text-gray-500'}`}>
                      {currentStage === 'stage3' && <RefreshCcw className="w-4 h-4 animate-spin" />}
                      3. LLM Extraction
                    </div>
                    <div className={`flex items-center gap-2 text-sm font-semibold ${currentStage === 'stage4' ? 'text-[var(--blinkit-yellow)]' : 'text-gray-500'}`}>
                      {currentStage === 'stage4' && <RefreshCcw className="w-4 h-4 animate-spin" />}
                      4. Scoring
                    </div>
                  </div>

                  <div className="bg-black border border-gray-800 rounded-lg p-4 h-64 overflow-y-auto font-mono text-xs shadow-inner">
                    {pipelineLogs.map((log, i) => (
                      <div key={i} className={`mb-1 ${log.includes("ERROR") ? "text-red-400" : log.includes("✅") ? "text-green-400 font-bold" : "text-green-500"}`}>
                        <span className="text-gray-600 mr-2">{new Date().toLocaleTimeString()}</span> 
                        {log}
                      </div>
                    ))}
                    {pipelineStatus === "running" && (
                      <div className="text-gray-500 mt-2 animate-pulse">Waiting for process...</div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {activeTab === "feed" && (
      <div className="grid grid-cols-12 gap-8">
        
        {/* Left Sidebar - Filters */}
        <aside className="col-span-3 space-y-6">
          <div className="bg-[#1a1a1a] p-5 rounded-xl border border-gray-800 shadow-xl">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Filter className="w-5 h-5 text-[var(--blinkit-yellow)]" />
              Filters
            </h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-2">Decision Driver</label>
                <select 
                  className="w-full bg-black border border-gray-700 rounded-md p-2 text-white focus:border-[var(--blinkit-yellow)] outline-none transition-colors"
                  value={filterDriver}
                  onChange={(e) => setFilterDriver(e.target.value)}
                >
                              <option value="All">All Drivers</option>
                  {uniqueDrivers.map(d => <option key={d} value={d}>{formatLabel(d)}</option>)}
                </select>
              </div>

              <div>
                <label className="block text-sm text-gray-400 mb-2">Purchase Context</label>
                <select
                  className="w-full bg-black border border-gray-700 rounded-md p-2 text-white focus:border-[var(--blinkit-yellow)] outline-none transition-colors"
                  value={filterContext}
                  onChange={(e) => setFilterContext(e.target.value)}
                >
                  <option value="All">All Contexts</option>
                  {uniqueContexts.map(c => <option key={c} value={c}>{formatLabel(c)}</option>)}
                </select>
              </div>

              <div>
                <label className="block text-sm text-gray-400 mb-2">Source</label>
                <select
                  className="w-full bg-black border border-gray-700 rounded-md p-2 text-white focus:border-[var(--blinkit-yellow)] outline-none transition-colors"
                  value={filterSource}
                  onChange={(e) => setFilterSource(e.target.value)}
                >
                  <option value="All">All Sources</option>
                  {uniqueSources.map(s => <option key={s} value={s}>{formatLabel(s)}</option>)}
                </select>
              </div>
            </div>
            
            {(filterDriver !== "All" || filterContext !== "All" || filterSource !== "All") && (
              <button 
                onClick={() => { setFilterDriver("All"); setFilterContext("All"); setFilterSource("All"); }}
                className="w-full mt-6 bg-gray-800 hover:bg-gray-700 text-white py-2 rounded-md text-sm transition-colors"
              >
                Clear Filters
              </button>
            )}
          </div>
        </aside>

        {/* Main Content */}
        <main className="col-span-9 space-y-8">
          
          {/* Charts Row */}
          <div className="grid grid-cols-2 gap-6">
            
            {/* Pie Chart */}
            <div className="bg-[#1a1a1a] p-6 rounded-xl border border-gray-800 shadow-xl">
              <h3 className="text-lg font-semibold mb-6 flex items-center gap-2">
                <Tag className="w-5 h-5 text-[var(--blinkit-yellow)]" />
                Primary Decision Drivers
              </h3>
              <div className="h-64">
                {driverChartData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={driverChartData}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={90}
                        paddingAngle={2}
                        dataKey="value"
                      >
                        {driverChartData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip 
                        contentStyle={{ backgroundColor: '#000', border: '1px solid #333', borderRadius: '8px' }}
                        itemStyle={{ color: '#fff' }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-gray-500">No data for this filter combination</div>
                )}
              </div>
              <div className="mt-4 flex flex-wrap gap-2 justify-center">
                {driverChartData.map((entry, index) => (
                  <div key={entry.name} className="flex items-center gap-2 text-sm text-gray-300 bg-black px-2 py-1 rounded">
                    <span className="w-3 h-3 rounded-full" style={{ backgroundColor: COLORS[index % COLORS.length] }}></span>
                    {entry.name} ({entry.value})
                  </div>
                ))}
              </div>
            </div>

            {/* Bar Chart */}
            <div className="bg-[#1a1a1a] p-6 rounded-xl border border-gray-800 shadow-xl">
              <h3 className="text-lg font-semibold mb-6 flex items-center gap-2">
                <MessageSquare className="w-5 h-5 text-[var(--blinkit-yellow)]" />
                Purchase Contexts
              </h3>
              <div style={{ height: `${Math.max(200, contextChartData.length * 44)}px` }}>
                {contextChartData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={contextChartData} layout="vertical" margin={{ top: 0, right: 16, left: 30, bottom: 0 }}>
                      <XAxis type="number" hide />
                      <YAxis dataKey="name" type="category" axisLine={false} tickLine={false} tick={{ fill: '#aaa', fontSize: 12 }} width={90} />
                      <Tooltip 
                        cursor={{ fill: '#222' }}
                        contentStyle={{ backgroundColor: '#000', border: '1px solid #333', borderRadius: '8px' }}
                      />
                      <Bar dataKey="value" fill="var(--blinkit-yellow)" radius={[0, 4, 4, 0]} barSize={24} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-gray-500">No data for this filter combination</div>
                )}
              </div>
            </div>

          </div>

          {/* Evidence Feed */}
          <div>
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-2xl font-bold">Evidence Feed</h3>
              <span className="text-gray-400">{filteredInsights.length} Results</span>
            </div>
            
            <div className="space-y-4">
              {filteredInsights.length === 0 ? (
                <div className="text-center py-12 text-gray-500 bg-[#1a1a1a] rounded-xl border border-gray-800">
                  No insights match your selected filters.
                </div>
              ) : (
                filteredInsights.map((insight) => {
                  const quote = insight.evidence_quote || "";
                  const text = insight.chunk_text || "";
                  const highlightIndex = quote.length > 0 ? text.toLowerCase().indexOf(quote.toLowerCase()) : -1;
                  
                  let highlightedText = <span className="text-gray-300">{text}</span>;
                  
                  if (highlightIndex !== -1 && quote.length > 5) {
                    const before = text.substring(0, highlightIndex);
                    const highlight = text.substring(highlightIndex, highlightIndex + quote.length);
                    const after = text.substring(highlightIndex + quote.length);
                    
                    highlightedText = (
                      <>
                        <span className="text-gray-400">{before}</span>
                        <span className="bg-yellow-500/20 text-yellow-200 px-1 rounded-sm border-b border-yellow-500/50">{highlight}</span>
                        <span className="text-gray-400">{after}</span>
                      </>
                    );
                  }

                  return (
                    <div key={insight.id} className="bg-[#1a1a1a] p-5 rounded-xl border border-gray-800 hover:border-gray-600 transition-all shadow-md group">
                      <div className="flex flex-wrap gap-2 mb-4">
                        <SourceBadge source={insight.source} />
                        <span className="px-3 py-1 bg-blue-900/40 text-blue-300 text-xs font-semibold rounded-full border border-blue-800/50">
                          {formatLabel(insight.decision_driver)}
                        </span>
                        <span className="px-3 py-1 bg-purple-900/40 text-purple-300 text-xs font-semibold rounded-full border border-purple-800/50">
                          {formatLabel(insight.purchase_context)}
                        </span>
                      </div>
                      <p className="text-lg leading-relaxed font-medium mb-4">
                        "{highlightedText}"
                      </p>
                      <div className="text-xs text-gray-600 flex justify-between items-center border-t border-gray-800 pt-3">
                        <span>Chunk ID: {insight.chunk_id.split('-')[0]}</span>
                        <span className="opacity-0 group-hover:opacity-100 transition-opacity">View Full Review →</span>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

        </main>
      </div>
      )} {/* end feed tab */}

      {/* Stage 4 — Signal Scoring Panel */}
      {activeTab === "stage4" && (
        <div className="max-w-4xl mx-auto">
          <div className="bg-[#1a1a1a] rounded-xl border border-gray-800 shadow-xl p-8">
            <div className="flex items-center gap-3 mb-2">
              <BarChart2 className="w-6 h-6 text-[var(--blinkit-yellow)]" />
              <h2 className="text-2xl font-bold">Quantitative Signals</h2>
            </div>
            <p className="text-gray-400 text-sm mb-8">
              Converts the unstructured behavioral insights extracted by the LLM into hard mathematical data. 
              This stage calculates the frequency and statistical weight of each decision driver and purchase context, 
              proving the validity of the insights using pure percentages rather than LLM guesswork.
            </p>

            {/* Idle state */}
            {stage4Status === "idle" && (
              <button
                onClick={runStage4}
                className="flex items-center gap-2 bg-[var(--blinkit-yellow)] text-black font-bold px-6 py-3 rounded-lg hover:brightness-110 transition-all shadow-lg shadow-yellow-500/20"
              >
                <BarChart2 className="w-5 h-5" />
                Run Signal Scoring
              </button>
            )}

            {/* Loading */}
            {stage4Status === "loading" && (
              <div className="flex items-center gap-3 text-gray-400">
                <Loader2 className="w-6 h-6 animate-spin text-[var(--blinkit-yellow)]" />
                Computing scores from database...
              </div>
            )}

            {/* Error */}
            {stage4Status === "error" && (
              <div className="bg-red-900/20 border border-red-800/50 rounded-lg p-4 text-red-300">
                <div className="flex items-center gap-2 font-semibold mb-1"><XCircle className="w-5 h-5" /> Error</div>
                <p className="text-sm">{stage4Error}</p>
                <button onClick={runStage4} className="mt-3 text-sm underline text-red-400 hover:text-red-300">Retry</button>
              </div>
            )}

            {/* Saved Banner */}
            {stage4Status === "saved" && (
              <div className="bg-green-900/20 border border-green-800/50 rounded-lg p-6 text-center mb-8">
                <CheckCircle className="w-12 h-12 text-green-400 mx-auto mb-3" />
                <h3 className="text-xl font-bold text-green-300 mb-1">Stage 4 Complete!</h3>
                <p className="text-gray-400 text-sm">Signal scores successfully saved to Supabase. You are now ready to run Stage 5 — Synthesis.</p>
              </div>
            )}

            {/* Preview (Shown during preview, saving, and saved) */}
            {(stage4Status === "preview" || stage4Status === "saving" || stage4Status === "saved") && stage4Scores && (
              <div className="space-y-6">
                <div className="grid grid-cols-3 gap-4">
                  <div className="bg-black rounded-lg p-4 text-center border border-gray-800">
                    <div className="text-3xl font-bold text-[var(--blinkit-yellow)]">{stage4Scores.total_annotations}</div>
                    <div className="text-xs text-gray-400 mt-1">Valid Annotations</div>
                  </div>
                  <div className="bg-black rounded-lg p-4 text-center border border-gray-800">
                    <div className="text-3xl font-bold text-blue-400">{stage4Scores.decision_driver?.length}</div>
                    <div className="text-xs text-gray-400 mt-1">Decision Driver Categories</div>
                  </div>
                  <div className="bg-black rounded-lg p-4 text-center border border-gray-800">
                    <div className="text-3xl font-bold text-purple-400">{stage4Scores.purchase_context?.length}</div>
                    <div className="text-xs text-gray-400 mt-1">Purchase Context Categories</div>
                  </div>
                </div>

                {["decision_driver", "purchase_context", "inferred_segment", "decision_evidence_type", "confidence"].map((dim) => {
                  const descriptions: Record<string, string> = {
                    "decision_driver": "The core reason or motivation behind the user's choice to use Blinkit.",
                    "purchase_context": "The specific situation, event, or time of day when the purchase occurred.",
                    "inferred_segment": "The type of user profile the AI guessed based on how they write and what they buy.",
                    "decision_evidence_type": "How the user justified their decision in the text (e.g., comparing prices, emotional frustration).",
                    "confidence": "How confident the AI was in its own labeling of this review."
                  };

                  return (
                  <div key={dim} className="bg-[#111] p-4 rounded-lg border border-gray-800">
                    <h4 className="text-sm font-bold text-[var(--blinkit-yellow)] uppercase tracking-widest mb-1">
                      {dim.replace(/_/g, " ")}
                    </h4>
                    <p className="text-sm text-gray-400 mb-4">{descriptions[dim]}</p>
                    <div className="space-y-2">
                      {(stage4Scores[dim] || []).map((row: any) => (
                        <div key={row.key} className="flex items-center gap-3">
                          <span className="text-sm text-gray-400 w-48 truncate shrink-0">{formatLabel(row.key)}</span>
                          <div className="flex-1 h-2 bg-gray-800 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-[var(--blinkit-yellow)] rounded-full transition-all"
                              style={{ width: `${Math.min(row.pct, 100)}%` }}
                            />
                          </div>
                          <span className="text-sm font-bold text-[var(--blinkit-yellow)] w-24 text-right shrink-0">{row.count} <span className="text-gray-400 font-medium">({row.pct}%)</span></span>
                        </div>
                      ))}
                    </div>
                  </div>
                  );
                })}

                <div className="bg-[#111] p-4 rounded-lg border border-gray-800">
                  <h4 className="text-sm font-bold text-[var(--blinkit-yellow)] uppercase tracking-widest mb-1">Top Cross-Patterns</h4>
                  <p className="text-sm text-gray-400 mb-4">
                    Shows which Decision Driver and Purchase Context happen together most often. Useful for finding specific use-cases (e.g. Convenience + Late Night).
                  </p>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-gray-500 border-b border-gray-800">
                          <th className="text-left pb-2 font-medium">Decision Driver</th>
                          <th className="text-left pb-2 font-medium">Purchase Context</th>
                          <th className="text-right pb-2 font-medium">Count</th>
                          <th className="text-right pb-2 font-medium">%</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(stage4Scores.cross_patterns || []).map((cp: any, i: number) => (
                          <tr key={i} className="border-b border-gray-800/50 hover:bg-gray-800/20">
                            <td className="py-2 text-blue-300">{formatLabel(cp.driver)}</td>
                            <td className="py-2 text-purple-300">{formatLabel(cp.context)}</td>
                            <td className="py-2 text-right text-gray-300">{cp.count}</td>
                            <td className="py-2 text-right text-gray-500">{cp.pct}%</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Action buttons (Hide if already saved) */}
                {stage4Status !== "saved" && (
                  <div className="flex gap-4 pt-4 border-t border-gray-800">
                    <button
                      onClick={confirmSave}
                      disabled={stage4Status === "saving"}
                      className="flex items-center gap-2 bg-[var(--blinkit-yellow)] text-black font-bold px-6 py-3 rounded-lg hover:brightness-110 transition-all disabled:opacity-50"
                    >
                      {stage4Status === "saving" ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle className="w-4 h-4" />}
                      {stage4Status === "saving" ? "Saving..." : "Confirm — Save to Database"}
                    </button>
                    <button
                      onClick={discardScores}
                      disabled={stage4Status === "saving"}
                      className="flex items-center gap-2 bg-gray-800 hover:bg-gray-700 text-white px-6 py-3 rounded-lg transition-all disabled:opacity-50"
                    >
                      <XCircle className="w-4 h-4" />
                      Discard
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )} {/* end stage4 tab */}

      {/* Stage 5 — Synthesized Insights Panel */}
      {activeTab === "stage5" && (
        <div className="max-w-5xl mx-auto space-y-8">
          <div className="bg-[#1a1a1a] rounded-xl border border-gray-800 shadow-xl p-8 mb-8">
            <div className="flex items-center gap-3 mb-2">
              <Zap className="w-6 h-6 text-[var(--blinkit-yellow)]" />
              <h2 className="text-2xl font-bold">Synthesized PM Insights</h2>
            </div>
            <p className="text-gray-400 text-sm">
              These insights are generated by the LLM (Llama 3.3 70B Versatile) which was fed the statistical scores from Stage 4 and all {initialInsights.length} qualitative evidence quotes simultaneously.
            </p>
          </div>

          {stage5Status === "loading" && (
            <div className="flex items-center gap-3 justify-center text-gray-400 p-12">
              <Loader2 className="w-6 h-6 animate-spin text-[var(--blinkit-yellow)]" />
              Loading synthesized reports from database...
            </div>
          )}

          {stage5Status === "error" && (
            <div className="bg-red-900/20 border border-red-800/50 rounded-lg p-6 text-red-300 max-w-2xl mx-auto text-center">
              <XCircle className="w-8 h-8 mx-auto mb-2" />
              <h3 className="font-bold mb-1">Error Loading Reports</h3>
              <p className="text-sm">{stage5Error}</p>
              <button onClick={loadStage5} className="mt-4 px-4 py-2 bg-red-900/40 hover:bg-red-900/60 rounded border border-red-800 transition-colors">Retry</button>
            </div>
          )}

          {stage5Status === "loaded" && stage5Reports.length === 0 && (
            <div className="bg-[#111] border border-gray-800 rounded-xl p-8 max-w-2xl mx-auto text-center mt-12">
              <h3 className="text-xl font-bold mb-4">Almost there! Generating Synthesized Insights</h3>
              <p className="text-gray-400 mb-6 leading-relaxed">
                We are now ready to feed all the qualitative evidence directly into the LLM. 
                Because this requires analyzing a massive amount of context to write deeply accurate PM insights, it takes a little extra time (about 1 to 2 minutes).
              </p>
              
              {!isSynthesizing && synthesisLogs.length === 0 ? (
                <button 
                  onClick={startSynthesis}
                  className="bg-[var(--blinkit-yellow)] text-black px-8 py-3 rounded-lg font-bold flex items-center justify-center gap-2 hover:bg-yellow-400 shadow-[0_0_20px_rgba(246,194,46,0.6)] transition-all mx-auto mt-8"
                >
                  <Zap className="w-5 h-5" fill="currentColor" />
                  Start LLM Synthesis
                </button>
              ) : (
                <div className="mt-8 text-left bg-black border border-gray-800 rounded-xl overflow-hidden shadow-2xl">
                  <div className="bg-gray-900 px-4 py-2 flex items-center justify-between border-b border-gray-800">
                    <span className="text-xs font-mono text-gray-400 flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full bg-yellow-500 animate-pulse"></div>
                      LLM Synthesizer Running
                    </span>
                    <span className="text-xs text-gray-500 font-mono">{activeRunId?.substring(0,8)}</span>
                  </div>
                  <div className="h-64 overflow-y-auto p-4 font-mono text-xs text-green-400 leading-relaxed scrollbar-thin scrollbar-thumb-gray-800 scrollbar-track-transparent">
                    {synthesisLogs.map((log, i) => (
                      <div key={i} className="mb-1 opacity-90">{log}</div>
                    ))}
                    {isSynthesizing && (
                      <div className="animate-pulse mt-2 text-yellow-500 flex items-center gap-2">
                        <span className="w-1.5 h-1.5 bg-yellow-500 rounded-full"></span> 
                        Generating insights...
                      </div>
                    )}
                    <div ref={synthLogsEndRef} />
                  </div>
                </div>
              )}
            </div>
          )}

          {stage5Status === "loaded" && stage5Reports.length > 0 && (
            <div className="space-y-8">
              {stage5Reports.map((report) => (
                <div key={report.id} className="bg-[#1a1a1a] rounded-xl border border-gray-800 shadow-xl overflow-hidden">
                  <div className="bg-black/50 border-b border-gray-800 p-6">
                    <span className="text-xs font-bold text-gray-500 tracking-widest uppercase mb-2 block">{report.question_id}</span>
                    <h3 className="text-xl font-semibold text-gray-200">{report.question_text}</h3>
                  </div>
                  <div className="p-6 md:p-8">
                    <p className="text-gray-300 leading-relaxed text-lg mb-8">
                      {report.answer_text}
                    </p>
                    
                    <div className="grid md:grid-cols-2 gap-8 border-t border-gray-800 pt-8">
                      <div>
                        <h4 className="text-sm font-bold text-[var(--blinkit-yellow)] uppercase tracking-widest mb-4 flex items-center gap-2">
                          <BarChart2 className="w-4 h-4" /> Data Proof
                        </h4>
                        <div className="bg-black border border-[var(--blinkit-yellow)]/30 rounded-lg p-5">
                          <p className="text-[var(--blinkit-yellow)] font-medium text-lg leading-snug">
                            {report.key_statistic}
                          </p>
                        </div>
                      </div>
                      
                      <div>
                        <h4 className="text-sm font-bold text-blue-400 uppercase tracking-widest mb-4 flex items-center gap-2">
                          <MessageSquare className="w-4 h-4" /> Customer Voices
                        </h4>
                        <div className="space-y-4">
                          {(() => {
                            try {
                              const quotes = JSON.parse(report.supporting_quote);
                              return (Array.isArray(quotes) ? quotes : [report.supporting_quote]).map((quote: string, i: number) => (
                                <div key={i} className="bg-black/50 border border-gray-800 rounded-lg p-4 relative">
                                  <span className="absolute top-2 left-2 text-gray-700 text-3xl font-serif">"</span>
                                  <p className="text-gray-400 text-sm italic relative z-10 pl-6 leading-relaxed">
                                    {quote}
                                  </p>
                                </div>
                              ));
                            } catch(e) {
                               return (
                                <div className="bg-black/50 border border-gray-800 rounded-lg p-4 relative">
                                  <span className="absolute top-2 left-2 text-gray-700 text-3xl font-serif">"</span>
                                  <p className="text-gray-400 text-sm italic relative z-10 pl-6 leading-relaxed">
                                    {report.supporting_quote}
                                  </p>
                                </div>
                               )
                            }
                          })()}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )} {/* end stage5 tab */}

    </div>
  );
}
