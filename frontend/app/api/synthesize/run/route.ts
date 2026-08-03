import { NextRequest } from "next/server";
import { spawn } from "child_process";
import path from "path";

export async function POST(req: NextRequest) {
  try {
    const { run_id } = await req.json();
    if (!run_id) {
      return new Response(JSON.stringify({ error: "Missing run_id" }), { status: 400 });
    }

    // Prepare Subprocess
    const ROOT = path.resolve(process.cwd(), "..", "backend");
    const pythonScript = "pipeline/stages/synthesize.py";

    const pythonPath = process.platform === "win32" ? "venv/Scripts/python" : "python3";
    const proc = spawn(pythonPath, [pythonScript, "--run-id", run_id], {
      cwd: ROOT,
      env: { ...process.env, PYTHONIOENCODING: "utf-8" }
    });

    // Set up Server-Sent Events (SSE) Stream
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(new TextEncoder().encode(`data: {"event": "log", "data": "Initializing LLM Synthesis Engine..."}\n\n`));

        proc.stdout.on("data", (data) => {
          const lines = data.toString().split("\n");
          for (const line of lines) {
            if (line.trim()) {
              const safeLine = line.replace(/"/g, '\\"').replace(/\r/g, '');
              controller.enqueue(new TextEncoder().encode(`data: {"event": "log", "data": "${safeLine}"}\n\n`));
            }
          }
        });

        proc.stderr.on("data", (data) => {
          const safeLine = data.toString().replace(/"/g, '\\"').replace(/\r/g, '').replace(/\n/g, ' ');
          controller.enqueue(new TextEncoder().encode(`data: {"event": "log", "data": "[ERROR] ${safeLine}"}\n\n`));
        });

        proc.on("close", (code) => {
          if (code === 0) {
            controller.enqueue(new TextEncoder().encode(`data: {"event": "done", "data": ""}\n\n`));
          } else {
            controller.enqueue(new TextEncoder().encode(`data: {"event": "error", "data": "Synthesis failed with code ${code}"}\n\n`));
          }
          controller.close();
        });

        req.signal.addEventListener("abort", () => {
          try {
            if (process.platform === "win32") {
              spawn("taskkill", ["/pid", proc.pid?.toString() || "", "/f", "/t"]);
            } else {
              proc.kill("SIGKILL");
            }
          } catch (e) {}
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
    return new Response(JSON.stringify({ error: error.message }), { status: 500 });
  }
}
