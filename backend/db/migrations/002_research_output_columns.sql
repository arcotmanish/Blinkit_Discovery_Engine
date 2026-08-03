-- ================================================================
-- Migration 002: Research Output Columns
-- Purpose: Add excluded_short status and research-ready output
--           columns to synthesized_insights.
-- Apply via: Supabase SQL Editor
-- ================================================================

-- ── 1. Add excluded_short to raw_reviews status constraint ──────
-- Drop the old constraint, add the new one with excluded_short
ALTER TABLE raw_reviews DROP CONSTRAINT IF EXISTS raw_reviews_status_check;
ALTER TABLE raw_reviews ADD CONSTRAINT raw_reviews_status_check
    CHECK (status IN (
        'pending',
        'excluded_operational',
        'excluded_short',       -- NEW: word_count < 10, pre-LLM filter
        'archived',
        'low_relevance',
        'relevant',
        'core_evidence',
        'non_english'
    ));

-- ── 2. Add research-ready output columns to synthesized_insights ─
ALTER TABLE synthesized_insights
    ADD COLUMN IF NOT EXISTS is_strategic_theme    BOOLEAN DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS corpus_percentage     NUMERIC(5,2),
    ADD COLUMN IF NOT EXISTS source_distribution   JSONB,
    ADD COLUMN IF NOT EXISTS rating_distribution   JSONB,
    ADD COLUMN IF NOT EXISTS suggested_interview_question TEXT,
    ADD COLUMN IF NOT EXISTS suggested_survey_hypothesis  TEXT;

-- ── 3. Comment ───────────────────────────────────────────────────
COMMENT ON COLUMN synthesized_insights.is_strategic_theme IS
    'TRUE for top 5-7 clusters; FALSE for additional_signal clusters below threshold';
COMMENT ON COLUMN synthesized_insights.corpus_percentage IS
    'evidence_count / total_chunks_in_run * 100';
COMMENT ON COLUMN synthesized_insights.source_distribution IS
    'JSON: {play_store: N, app_store: N, reddit: N}';
COMMENT ON COLUMN synthesized_insights.rating_distribution IS
    'JSON: {1: N, 2: N, 3: N, 4: N, 5: N} — from app store and play store chunks only';
COMMENT ON COLUMN synthesized_insights.suggested_interview_question IS
    'LLM-generated open-ended question for qualitative research on this pattern';
COMMENT ON COLUMN synthesized_insights.suggested_survey_hypothesis IS
    'LLM-generated falsifiable survey statement for quantitative validation';
