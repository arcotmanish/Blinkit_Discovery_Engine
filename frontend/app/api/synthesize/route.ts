import { supabase } from "@/lib/supabase";
import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  let runId = searchParams.get("run_id");

  let query = supabase
    .from("synthesized_reports")
    .select("*")
    .order("question_id", { ascending: true });

  if (runId) {
    query = query.eq("run_id", runId);
  }

  const { data, error } = await query;

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  return NextResponse.json(data);
}
