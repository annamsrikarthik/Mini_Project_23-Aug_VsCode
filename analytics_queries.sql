-- Lead Intelligence PostgreSQL analytics
-- Database: MiniProject_FDE
-- Schema: public
--
-- These reports were verified against the committed 100-lead demonstration:
-- 35 qualified, 36 review, 29 rejected, and 35 outreach drafts.
-- They are read-only and do not modify project data.


-- 1. Qualification decision summary
-- Shows the number and percentage of leads in each decision category.
SELECT
    decision,
    COUNT(*) AS lead_count,
    ROUND(
        COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (),
        2
    ) AS percentage
FROM qualification_results
GROUP BY decision
ORDER BY
    CASE decision
        WHEN 'qualified' THEN 1
        WHEN 'review' THEN 2
        WHEN 'rejected' THEN 3
    END;


-- 2. Score profile by decision
-- NULL scores are excluded because they represent records that could not be
-- scored safely. The five unscored records remain in the review decision.
SELECT
    decision,
    COUNT(*) AS lead_count,
    ROUND(AVG(score), 2) AS average_score,
    MIN(score) AS minimum_score,
    MAX(score) AS maximum_score
FROM qualification_results
WHERE score IS NOT NULL
GROUP BY decision
ORDER BY
    CASE decision
        WHEN 'qualified' THEN 1
        WHEN 'review' THEN 2
        WHEN 'rejected' THEN 3
    END;


-- 3. Performance by lead source
-- AVG ignores NULL scores. Missing, NA, and unmapped sources remain visible.
SELECT
    COALESCE(occurrence.source, 'Missing source') AS lead_source,
    COUNT(*) AS total_leads,
    COUNT(*) FILTER (
        WHERE result.decision = 'qualified'
    ) AS qualified_leads,
    COUNT(*) FILTER (
        WHERE result.decision = 'review'
    ) AS review_leads,
    COUNT(*) FILTER (
        WHERE result.decision = 'rejected'
    ) AS rejected_leads,
    ROUND(AVG(result.score), 2) AS average_score,
    ROUND(
        COUNT(*) FILTER (
            WHERE result.decision = 'qualified'
        ) * 100.0 / COUNT(*),
        2
    ) AS qualification_rate
FROM lead_occurrences AS occurrence
JOIN qualification_results AS result
    ON result.lead_occurrence_id = occurrence.lead_occurrence_id
GROUP BY COALESCE(occurrence.source, 'Missing source')
ORDER BY
    qualification_rate DESC,
    total_leads DESC;


-- 4. Performance by company-size range
WITH company_size_groups AS (
    SELECT
        occurrence.lead_occurrence_id,
        CASE
            WHEN occurrence.company_size IS NULL
                THEN 'Missing company size'
            WHEN occurrence.company_size < 20
                THEN 'Below 20'
            WHEN occurrence.company_size BETWEEN 20 AND 500
                THEN '20 to 500'
            ELSE 'Above 500'
        END AS company_size_group
    FROM lead_occurrences AS occurrence
)
SELECT
    size_group.company_size_group,
    COUNT(*) AS total_leads,
    COUNT(*) FILTER (
        WHERE result.decision = 'qualified'
    ) AS qualified_leads,
    COUNT(*) FILTER (
        WHERE result.decision = 'review'
    ) AS review_leads,
    COUNT(*) FILTER (
        WHERE result.decision = 'rejected'
    ) AS rejected_leads,
    ROUND(AVG(result.score), 2) AS average_score
FROM company_size_groups AS size_group
JOIN qualification_results AS result
    ON result.lead_occurrence_id = size_group.lead_occurrence_id
GROUP BY size_group.company_size_group
ORDER BY
    CASE size_group.company_size_group
        WHEN '20 to 500' THEN 1
        WHEN 'Below 20' THEN 2
        WHEN 'Above 500' THEN 3
        WHEN 'Missing company size' THEN 4
    END;


-- 5. Performance by interaction recency
-- Recency is calculated from the evaluation date belonging to each run.
WITH recency_groups AS (
    SELECT
        occurrence.lead_occurrence_id,
        CASE
            WHEN occurrence.last_interaction_date IS NULL
                THEN 'Missing interaction date'
            WHEN occurrence.last_interaction_date > run.evaluation_date
                THEN 'Future interaction date'
            WHEN run.evaluation_date
                 - occurrence.last_interaction_date <= 30
                THEN '0 to 30 days'
            WHEN run.evaluation_date
                 - occurrence.last_interaction_date <= 90
                THEN '31 to 90 days'
            ELSE 'Over 90 days'
        END AS recency_group
    FROM lead_occurrences AS occurrence
    JOIN input_files AS input_file
        ON input_file.input_file_id = occurrence.input_file_id
    JOIN processing_runs AS run
        ON run.run_id = input_file.run_id
)
SELECT
    recency.recency_group,
    COUNT(*) AS total_leads,
    COUNT(*) FILTER (
        WHERE result.decision = 'qualified'
    ) AS qualified_leads,
    COUNT(*) FILTER (
        WHERE result.decision = 'review'
    ) AS review_leads,
    COUNT(*) FILTER (
        WHERE result.decision = 'rejected'
    ) AS rejected_leads,
    ROUND(AVG(result.score), 2) AS average_score
FROM recency_groups AS recency
JOIN qualification_results AS result
    ON result.lead_occurrence_id = recency.lead_occurrence_id
GROUP BY recency.recency_group
ORDER BY
    CASE recency.recency_group
        WHEN '0 to 30 days' THEN 1
        WHEN '31 to 90 days' THEN 2
        WHEN 'Over 90 days' THEN 3
        WHEN 'Missing interaction date' THEN 4
        WHEN 'Future interaction date' THEN 5
    END;


-- 6. Qualified-lead sales queue
-- LEFT JOIN preserves a qualified lead if its expected draft is missing.
SELECT
    result.priority_rank,
    occurrence.lead_name,
    occurrence.company_name,
    occurrence.company_size,
    occurrence.industry,
    occurrence.source,
    occurrence.last_interaction_date,
    result.score,
    draft.subject,
    draft.draft_status,
    draft.requires_sales_review,
    draft.sent
FROM qualification_results AS result
JOIN lead_occurrences AS occurrence
    ON occurrence.lead_occurrence_id = result.lead_occurrence_id
LEFT JOIN outreach_drafts AS draft
    ON draft.qualification_id = result.qualification_id
WHERE result.decision = 'qualified'
ORDER BY
    result.priority_rank ASC,
    result.score DESC,
    occurrence.lead_name ASC;


-- 7. Human-review queue
-- Unscored records with blocking data issues appear before scored borderline leads.
SELECT
    occurrence.csv_row,
    occurrence.lead_name,
    occurrence.company_name,
    occurrence.company_size,
    occurrence.source,
    occurrence.last_interaction_date,
    result.validation_status,
    result.score,
    CASE
        WHEN result.score IS NULL
            THEN 'Data problem prevents scoring'
        ELSE 'Score falls within the 5-7 review range'
    END AS review_reason,
    result.issues,
    result.warnings,
    result.reasoning,
    result.next_action
FROM qualification_results AS result
JOIN lead_occurrences AS occurrence
    ON occurrence.lead_occurrence_id = result.lead_occurrence_id
WHERE result.decision = 'review'
ORDER BY
    (result.score IS NULL) DESC,
    result.score DESC,
    occurrence.csv_row ASC;


-- 8. Most common rejection reasons
-- One lead may contribute to several reason counts.
SELECT
    reason.value AS rejection_reason,
    COUNT(*) AS affected_leads
FROM qualification_results AS result
CROSS JOIN LATERAL jsonb_array_elements_text(
    result.rejection_reasons
) AS reason(value)
WHERE result.decision = 'rejected'
GROUP BY reason.value
ORDER BY
    affected_leads DESC,
    rejection_reason ASC;


-- 9. Outreach-draft workflow status
SELECT
    draft.draft_status,
    draft.requires_sales_review,
    draft.sent,
    COUNT(*) AS draft_count
FROM outreach_drafts AS draft
GROUP BY
    draft.draft_status,
    draft.requires_sales_review,
    draft.sent
ORDER BY
    draft.draft_status,
    draft.requires_sales_review DESC,
    draft.sent;


-- 10. Data-quality summary
-- Counts may overlap because one occurrence can have multiple data-quality conditions.
SELECT
    COUNT(*) AS total_records,
    COUNT(*) FILTER (
        WHERE occurrence.identity_status = 'review_required'
    ) AS identity_review_records,
    COUNT(*) FILTER (
        WHERE occurrence.lead_name IS NULL
    ) AS missing_lead_names,
    COUNT(*) FILTER (
        WHERE occurrence.company_name IS NULL
    ) AS missing_company_names,
    COUNT(*) FILTER (
        WHERE occurrence.company_size IS NULL
    ) AS missing_company_sizes,
    COUNT(*) FILTER (
        WHERE occurrence.source IS NULL
           OR occurrence.source = 'NA'
    ) AS missing_sources,
    COUNT(*) FILTER (
        WHERE occurrence.source IS NOT NULL
          AND occurrence.source <> 'NA'
          AND occurrence.source NOT IN (
              'Inbound demo request',
              'Referral',
              'Sales call',
              'Webinar attendee',
              'Content download',
              'LinkedIn outreach'
          )
    ) AS unmapped_sources,
    COUNT(*) FILTER (
        WHERE occurrence.last_interaction_date IS NULL
    ) AS missing_interaction_dates,
    COUNT(*) FILTER (
        WHERE occurrence.last_interaction_date > run.evaluation_date
    ) AS future_interaction_dates,
    COUNT(*) FILTER (
        WHERE result.score IS NULL
    ) AS unscored_records,
    COUNT(*) FILTER (
        WHERE jsonb_array_length(result.issues) > 0
    ) AS records_with_issues,
    COUNT(*) FILTER (
        WHERE jsonb_array_length(result.warnings) > 0
    ) AS records_with_warnings
FROM lead_occurrences AS occurrence
JOIN input_files AS input_file
    ON input_file.input_file_id = occurrence.input_file_id
JOIN processing_runs AS run
    ON run.run_id = input_file.run_id
JOIN qualification_results AS result
    ON result.lead_occurrence_id = occurrence.lead_occurrence_id;

