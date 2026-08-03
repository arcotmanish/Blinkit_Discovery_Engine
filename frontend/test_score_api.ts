import { supabase } from "./lib/supabase.ts";

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
    if (error || !data) break;
    all = all.concat(data);
    if (data.length < size) break;
    page++;
  }
  return all;
}

async function test() {
  const activeRunId = "4a58551b-b5fd-469e-803f-b8871cab3a42";
  const [allChunks, annotations] = await Promise.all([
    fetchAll("review_chunks", "id, chunk_text", activeRunId),
    fetchAll("chunk_annotations", "*", activeRunId)
  ]);
  
  console.log("Total chunks:", allChunks.length);
  console.log("Total annotations:", annotations.length);

  const chunksMap = new Map(allChunks.map(c => [c.id, c.chunk_text]));
  const valid = annotations.filter((a) => !a.annotation_failed);
  console.log("Valid annotations:", valid.length);
  
  const uniqueTexts = new Set();
  const uniqueValid = [];
  
  for (const a of valid) {
    const text = chunksMap.get(a.chunk_id);
    if (text && !uniqueTexts.has(text)) {
      uniqueTexts.add(text);
      uniqueValid.push(a);
    }
  }
  
  console.log("Unique Valid:", uniqueValid.length);
}
test();
