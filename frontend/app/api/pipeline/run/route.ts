import { NextRequest } from "next/server";
import { spawn } from "child_process";
import path from "path";
import crypto from "crypto";
import { createClient } from "@supabase/supabase-js";

// Global memory lock to prevent multiple pipelines from running at the same time.
let pipelineRunning = false;

// Initialize Supabase client for pre-flight safety check
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || "";
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "";
const supabase = createClient(supabaseUrl, supabaseKey);

export async function POST(req: NextRequest) {
  // 1. Concurrency Lock
  if (pipelineRunning) {
    return new Response(JSON.stringify({ error: "A pipeline execution is already in progress. Please wait for it to complete." }), {
      status: 409,
      headers: { "Content-Type": "application/json" },
    });
  }

  try {
    const { sources } = await req.json();
    if (!sources || !Array.isArray(sources) || sources.length === 0) {
      return new Response(JSON.stringify({ error: "No sources selected." }), { status: 400 });
    }

    pipelineRunning = true;

    // 2. Pre-Flight Safety Check
    const newRunId = crypto.randomUUID();
    const { data: existingRuns, error: dbError } = await supabase
      .from("raw_reviews")
      .select("run_id")
      .eq("run_id", newRunId)
      .limit(1);

    if (dbError) {
      pipelineRunning = false;
      return new Response(JSON.stringify({ error: "Database error during safety check." }), { status: 500 });
    }

    if (existingRuns && existingRuns.length > 0) {
      pipelineRunning = false;
      return new Response(JSON.stringify({ error: "FATAL: UUID collision detected. Aborting to prevent data overwrite." }), { status: 500 });
    }

    // 3. Prepare Subprocess
    const ROOT = path.resolve(process.cwd(), "..", "backend");
    const pythonScript = "run_pipeline.py";
    const sourcesArg = sources.join(",");

    const pythonPath = process.platform === "win32" ? "venv/Scripts/python" : "python3";
    const proc = spawn(pythonPath, [pythonScript, "--run-id", newRunId, "--sources", sourcesArg], {
      cwd: ROOT,
      env: { ...process.env, PYTHONIOENCODING: "utf-8" }
    });

    // 4. Set up Server-Sent Events (SSE) Stream
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(new TextEncoder().encode(`data: {"event": "run_id", "data": "${newRunId}"}\n\n`));
        controller.enqueue(new TextEncoder().encode(`data: {"event": "log", "data": "Pipeline started with run_id: ${newRunId}"}\n\n`));

        // Listen for log output from Python
        proc.stdout.on("data", (data) => {
          const lines = data.toString().split("\n");
          for (const line of lines) {
            if (line.trim()) {
              // Simple heuristic to emit stage events based on python print statements
              if (line.includes("[STAGE 1]")) controller.enqueue(new TextEncoder().encode(`data: {"event": "stage", "data": "stage1"}\n\n`));
              if (line.includes("[STAGE 2]")) controller.enqueue(new TextEncoder().encode(`data: {"event": "stage", "data": "stage2"}\n\n`));
              if (line.includes("[STAGE 3]")) controller.enqueue(new TextEncoder().encode(`data: {"event": "stage", "data": "stage3"}\n\n`));
              if (line.includes("[STAGE 4]")) controller.enqueue(new TextEncoder().encode(`data: {"event": "stage", "data": "stage4"}\n\n`));
              if (line.includes("✅ PIPELINE COMPLETE!")) controller.enqueue(new TextEncoder().encode(`data: {"event": "done", "data": ""}\n\n`));

              const safeLine = line.replace(/"/g, '\\"').replace(/\r/g, '');
              controller.enqueue(new TextEncoder().encode(`data: {"event": "log", "data": "${safeLine}"}\n\n`));
            }
          }
        });

        // Listen for errors from Python
        proc.stderr.on("data", (data) => {
          const safeLine = data.toString().replace(/"/g, '\\"').replace(/\r/g, '').replace(/\n/g, ' ');
          controller.enqueue(new TextEncoder().encode(`data: {"event": "log", "data": "[ERROR] ${safeLine}"}\n\n`));
        });

        proc.on("close", (code) => {
          pipelineRunning = false;
          if (code !== 0 && code !== null) {
            controller.enqueue(new TextEncoder().encode(`data: {"event": "error", "data": "Pipeline exited with code ${code}"}\n\n`));
          }
          controller.close();
        });

        // 5. Abort / Kill Switch
        req.signal.addEventListener("abort", () => {
          console.log(`[API] Client disconnected. Sending SIGKILL to Python process ${proc.pid}`);
          try {
            // Windows specific kill command since process.kill doesn't always kill child processes
            if (process.platform === "win32") {
              spawn("taskkill", ["/pid", proc.pid?.toString() || "", "/f", "/t"]);
            } else {
              proc.kill("SIGKILL");
            }
          } catch (e) {
            console.error("Failed to kill process:", e);
          }
          pipelineRunning = false;
          // controller.close() may throw if already closed by abort
        });
      },
    });

    return new Response(stream, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
      },
    });
  } catch (error: any) {
    pipelineRunning = false;
    return new Response(JSON.stringify({ error: error.message || "Internal Server Error" }), { status: 500 });
  }
}
