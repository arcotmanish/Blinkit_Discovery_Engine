import { supabase } from "@/lib/supabase";
import DashboardClient from "./DashboardClient";

async function fetchAll(table: string, columns: string = "*", runId?: string) {
  let allData: any[] = [];
  let page = 0;
  const size = 1000;
  while (true) {
    let query = supabase.from(table).select(columns).range(page * size, (page + 1) * size - 1);
    if (runId) {
      query = query.eq("run_id", runId);
    }
    const { data, error } = await query;
    if (error || !data) break;
    allData = allData.concat(data);
    if (data.length < size) break;
    page++;
  }
  return allData;
}

export default async function DashboardPage(props: { searchParams: Promise<{ run_id?: string }> }) {
  const searchParams = await props.searchParams;
  // Fetch all available run_ids to populate the Time Machine Run Selector
  const allRunIdsData = await fetchAll("raw_reviews", "run_id");
  const uniqueRunIds = Array.from(new Set(allRunIdsData.map((d: any) => d.run_id))).filter(Boolean) as string[];

  // If no run_id is in the URL, fetch one (the default / latest)
  let activeRunId = searchParams.run_id;
  if (!activeRunId && uniqueRunIds.length > 0) {
    activeRunId = uniqueRunIds[0];
  }

  // Fetch all three tables in parallel for speed, filtered by activeRunId
  const [allChunks, allAnnotations, allReviews] = await Promise.all([
    fetchAll("review_chunks", "*", activeRunId),
    fetchAll("chunk_annotations", "*", activeRunId),
    fetchAll("raw_reviews", "id, source", activeRunId),
  ]);

  // Build lookup maps
  const chunksMap = new Map(allChunks.map((c) => [c.id, c]));
  const reviewsMap = new Map(allReviews.map((r) => [r.id, r]));

  const uniqueTexts = new Set<string>();
  const unifiedInsights: any[] = [];

  for (const ann of allAnnotations) {
    const chunk = chunksMap.get(ann.chunk_id);
    if (chunk && !uniqueTexts.has(chunk.chunk_text)) {
      uniqueTexts.add(chunk.chunk_text);

      // Look up which source (reddit / playstore) this review came from
      const review = reviewsMap.get(chunk.review_id);
      const source = review?.source ?? "unknown";

      unifiedInsights.push({
        ...ann,
        chunk_text: chunk.chunk_text,
        review_id: chunk.review_id,
        source,
      });
    }
  }

  // Sort newest first
  unifiedInsights.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

  return (
    <div className="min-h-screen bg-black text-gray-100 font-sans p-8">
      <DashboardClient 
        initialInsights={unifiedInsights} 
        rawReviewsCount={allReviews.length} 
        availableRuns={uniqueRunIds}
        activeRunId={activeRunId}
      />
    </div>
  );
}
