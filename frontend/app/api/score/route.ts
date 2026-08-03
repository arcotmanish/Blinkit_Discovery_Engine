import { supabase } from "@/lib/supabase";
import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

async function fetchAll(table: string, columns: string = "*", runId?: string | null) {
  let all: any[] = [];
  let page = 0;
  const size = 1000;
  while (true) {
    let query = supabase.from(table).select(columns).range(page * size, (page + 1) * size - 1);
    if (runId) {
      query = query.eq("run_id", runId);
    }
    const { data, error } = await query;
    if (error) {
      console.error("Fetch error for table", table, error);
      throw error;
    }
    if (!data) break;
    all = all.concat(data);
    if (data.length < size) break;
    page++;
  }
  return all;
}

function pct(count: number, total: number) {
  return total ? Math.round((count / total) * 1000) / 10 : 0;
}

function toList(counter: Record<string, number>, total: number, limit?: number) {
  return Object.entries(counter)
    .sort(([, a], [, b]) => b - a)
    .slice(0, limit)
    .map(([key, count]) => ({ key, count, pct: pct(count, total) }));
}

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  let activeRunId = searchParams.get("run_id");
  if (!activeRunId) {
    const { data } = await supabase.from("chunk_annotations").select("run_id").limit(1);
    if (data && data.length > 0) activeRunId = data[0].run_id;
  }

  const [allChunks, annotations] = await Promise.all([
    fetchAll("review_chunks", "id, chunk_text", activeRunId),
    fetchAll("chunk_annotations", "*", activeRunId)
  ]);

  const chunksMap = new Map(allChunks.map(c => [c.id, c.chunk_text]));
  const valid = annotations.filter((a) => !a.annotation_failed);
  
  const uniqueTexts = new Set();
  const uniqueValid = [];
  
  for (const a of valid) {
    const text = chunksMap.get(a.chunk_id);
    if (text && !uniqueTexts.has(text)) {
      uniqueTexts.add(text);
      uniqueValid.push(a);
    }
  }
  const total = uniqueValid.length;

  const driverCounts: Record<string, number> = {};
  const contextCounts: Record<string, number> = {};
  const evidenceCounts: Record<string, number> = {};
  const segmentCounts: Record<string, number> = {};
  const confCounts: Record<string, number> = {};
  const catCounts: Record<string, number> = {};
  const crossCounts: Record<string, number> = {};

  for (const a of uniqueValid) {
    if (a.decision_driver)        driverCounts[a.decision_driver]   = (driverCounts[a.decision_driver]   || 0) + 1;
    if (a.purchase_context)       contextCounts[a.purchase_context]  = (contextCounts[a.purchase_context]  || 0) + 1;
    if (a.decision_evidence_type) evidenceCounts[a.decision_evidence_type] = (evidenceCounts[a.decision_evidence_type] || 0) + 1;
    if (a.inferred_segment)       segmentCounts[a.inferred_segment]  = (segmentCounts[a.inferred_segment]  || 0) + 1;
    if (a.confidence)             confCounts[a.confidence]           = (confCounts[a.confidence]           || 0) + 1;
    for (const cat of (a.categories_mentioned || [])) {
      catCounts[cat] = (catCounts[cat] || 0) + 1;
    }
    const crossKey = `${a.decision_driver || "none"}|||${a.purchase_context || "none"}`;
    crossCounts[crossKey] = (crossCounts[crossKey] || 0) + 1;
  }

  const crossPatterns = Object.entries(crossCounts)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 10)
    .map(([key, count]) => {
      const [driver, context] = key.split("|||");
      return { driver, context, count, pct: pct(count, total) };
    });

  return NextResponse.json({
    run_id: activeRunId || "unknown",
    total_annotations: total,
    decision_driver:        toList(driverCounts,   total),
    purchase_context:       toList(contextCounts,  total),
    decision_evidence_type: toList(evidenceCounts, total),
    inferred_segment:       toList(segmentCounts,  total),
    confidence:             toList(confCounts,      total),
    categories_mentioned:   toList(catCounts,       total, 15),
    cross_patterns:         crossPatterns,
  });
}

export async function POST(req: Request) {
  const scores = await req.json();
  const { run_id, ...dims } = scores;

  const rows: any[] = [];

  for (const dim of ["decision_driver", "purchase_context",
    "decision_evidence_type", "inferred_segment", "confidence", "categories_mentioned"]) {
    for (const entry of (dims[dim] || [])) {
      rows.push({ run_id, signal_type: dim, signal_key: entry.key, signal_key2: null, count: entry.count, percentage: entry.pct });
    }
  }

  for (const cp of (dims.cross_patterns || [])) {
    rows.push({ run_id, signal_type: "cross_pattern", signal_key: cp.driver, signal_key2: cp.context, count: cp.count, percentage: cp.pct });
  }

  // Insert in chunks
  for (let i = 0; i < rows.length; i += 100) {
    const { error } = await supabase.from("signal_scores").insert(rows.slice(i, i + 100));
    if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  }

  return NextResponse.json({ saved: rows.length });
}
