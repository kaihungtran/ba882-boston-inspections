-- BA882 Team 10 | Irene Tang | GenAI Phase 1 input review
-- Raw tables as queried on 2026-10-16. Run one statement at a time.
-- Read-only SELECT statements. BigQuery results can change after ingestion.

-- 1. Inspection row IDs, text, code, and date coverage.
SELECT
  COUNT(*) AS total_rows,
  COUNT(DISTINCT _id) AS unique_row_ids,
  COUNT(DISTINCT licenseno) AS unique_license_numbers,
  COUNTIF(NULLIF(TRIM(violdesc), '') IS NULL) AS missing_violdesc,
  COUNTIF(NULLIF(TRIM(comments), '') IS NULL) AS missing_comments,
  COUNTIF(NULLIF(TRIM(violation), '') IS NULL) AS missing_violation_code,
  COUNTIF(NULLIF(TRIM(viol_level), '') IS NULL) AS missing_violation_level,
  COUNTIF(NULLIF(TRIM(resultdttm), '') IS NULL) AS missing_inspection_date
FROM `ba882-team10-inspections.raw.food_inspections`;

-- 2. Most frequent violation descriptions (not all distinct descriptions).
SELECT
  violdesc,
  COUNT(*) AS record_count
FROM `ba882-team10-inspections.raw.food_inspections`
WHERE violdesc IS NOT NULL AND TRIM(violdesc) != ''
GROUP BY violdesc
ORDER BY record_count DESC
LIMIT 30;

-- 3. Distinct descriptions/codes and available text combinations.
WITH source AS (
  SELECT
    NULLIF(TRIM(violdesc), '') AS description,
    NULLIF(TRIM(comments), '') AS comment_text,
    NULLIF(TRIM(violation), '') AS violation_code
  FROM `ba882-team10-inspections.raw.food_inspections`
)
SELECT
  COUNT(DISTINCT description) AS unique_descriptions,
  COUNT(DISTINCT violation_code) AS unique_violation_codes,
  COUNTIF(description IS NOT NULL AND comment_text IS NOT NULL) AS rows_with_both_texts,
  COUNTIF(description IS NOT NULL AND comment_text IS NULL) AS description_only_rows,
  COUNTIF(description IS NULL AND comment_text IS NOT NULL) AS comments_only_rows
FROM source;

-- 4. Repeatable exploratory sample of 20 inspection text records.
-- This is not a representative sample of all inspection visits.
SELECT
  _id, violdesc, comments, violation, viol_level, result, resultdttm
FROM `ba882-team10-inspections.raw.food_inspections`
WHERE NULLIF(TRIM(violdesc), '') IS NOT NULL
  AND NULLIF(TRIM(comments), '') IS NOT NULL
ORDER BY FARM_FINGERPRINT(CAST(_id AS STRING))
LIMIT 20;

-- 5. Legacy 311: top 40 category pairs and parseable coordinates.
SELECT
  reason,
  type,
  COUNT(*) AS request_rows,
  COUNTIF(
    SAFE_CAST(latitude AS FLOAT64) IS NOT NULL
    AND SAFE_CAST(longitude AS FLOAT64) IS NOT NULL
  ) AS rows_with_coordinates
FROM `ba882-team10-inspections.raw.requests_311_legacy`
GROUP BY reason, type
ORDER BY request_rows DESC
LIMIT 40;

-- 6. New 311: top 40 category pairs and parseable coordinates.
SELECT
  case_topic,
  service_name,
  COUNT(*) AS request_rows,
  COUNTIF(
    SAFE_CAST(latitude AS FLOAT64) IS NOT NULL
    AND SAFE_CAST(longitude AS FLOAT64) IS NOT NULL
  ) AS rows_with_coordinates
FROM `ba882-team10-inspections.raw.requests_311_new`
GROUP BY case_topic, service_name
ORDER BY request_rows DESC
LIMIT 40;
