-- Migration: Add truvari_metrics table
-- Date: 2025-11-13
-- Description: Create table for storing Truvari structural variant benchmarking metrics

CREATE TABLE IF NOT EXISTS truvari_metrics (
    id SERIAL PRIMARY KEY,
    
    -- True Positives
    tp_base INTEGER NOT NULL,  -- True Positives in base (reference)
    tp_comp INTEGER NOT NULL,  -- True Positives in comparison (query)
    
    -- False Positives and False Negatives
    fp INTEGER NOT NULL,  -- False Positives
    fn INTEGER NOT NULL,  -- False Negatives
    
    -- Performance metrics
    precision FLOAT NOT NULL,  -- Precision (TP / (TP + FP))
    recall FLOAT NOT NULL,  -- Recall/Sensitivity (TP / (TP + FN))
    f1 FLOAT NOT NULL,  -- F1 Score (harmonic mean of precision and recall)
    
    -- Variant counts
    base_cnt INTEGER NOT NULL,  -- Total variants in base (after filtering)
    comp_cnt INTEGER NOT NULL,  -- Total variants in comparison (after filtering)
    
    -- Genotype concordance
    gt_concordance FLOAT NOT NULL,  -- Genotype concordance for TP variants
    tp_comp_tp_gt INTEGER NOT NULL,  -- TP-comp with correct genotype
    tp_comp_fp_gt INTEGER NOT NULL,  -- TP-comp with incorrect genotype
    tp_base_tp_gt INTEGER NOT NULL,  -- TP-base with correct genotype
    tp_base_fp_gt INTEGER NOT NULL,  -- TP-base with incorrect genotype
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign key
    run_id INTEGER NOT NULL REFERENCES lab_runs(id) ON DELETE CASCADE,
    
    -- Indexes
    CONSTRAINT unique_run_truvari UNIQUE (run_id)
);

-- Create index on run_id for faster lookups
CREATE INDEX IF NOT EXISTS idx_truvari_metrics_run_id ON truvari_metrics(run_id);

-- Comments for documentation
COMMENT ON TABLE truvari_metrics IS 'Stores Truvari structural variant benchmarking metrics for each run';
COMMENT ON COLUMN truvari_metrics.tp_base IS 'True Positives found in reference/base VCF';
COMMENT ON COLUMN truvari_metrics.tp_comp IS 'True Positives found in comparison/query VCF';
COMMENT ON COLUMN truvari_metrics.fp IS 'False Positives - variants in query but not in reference';
COMMENT ON COLUMN truvari_metrics.fn IS 'False Negatives - variants in reference but not found in query';
COMMENT ON COLUMN truvari_metrics.precision IS 'Precision: TP / (TP + FP)';
COMMENT ON COLUMN truvari_metrics.recall IS 'Recall/Sensitivity: TP / (TP + FN)';
COMMENT ON COLUMN truvari_metrics.f1 IS 'F1 Score: harmonic mean of precision and recall';
COMMENT ON COLUMN truvari_metrics.gt_concordance IS 'Genotype concordance for matched variants';

