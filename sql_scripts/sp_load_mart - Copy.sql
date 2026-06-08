CREATE OR REPLACE PROCEDURE sp_load_mart_incremental()
LANGUAGE plpgsql
AS $$
BEGIN

RAISE NOTICE 'Incremental load: mart_pis_scores...';

EXECUTE '
    DELETE FROM mart_pis_scores
    WHERE week_start_date = (SELECT MAX(week_start_date) FROM stg_platform_performance);

    INSERT INTO mart_pis_scores
    WITH normalize_data AS (
        SELECT 
            platform, content_type, time_block,
            audience_age, audience_gender, audience_location,
            impressions, week_start_date,
            ROUND(((engagement_rate - MIN(engagement_rate) OVER()) / 
                   NULLIF(MAX(engagement_rate) OVER() - MIN(engagement_rate) OVER(), 0) * 100)::numeric, 2) AS engagement_score,
            ROUND(((conversion_rate - MIN(conversion_rate) OVER()) / 
                   NULLIF(MAX(conversion_rate) OVER() - MIN(conversion_rate) OVER(), 0) * 100)::numeric, 2) AS conversion_score,
            ROUND(((MAX(cost_per_result) OVER() - cost_per_result) / 
                   NULLIF(MAX(cost_per_result) OVER() - MIN(cost_per_result) OVER(), 0) * 100)::numeric, 2) AS cost_efficiency_score
        FROM stg_platform_performance
        WHERE week_start_date = (SELECT MAX(week_start_date) FROM stg_platform_performance)
    ),
    pis_score AS (
        SELECT 
            platform, content_type, time_block,
            audience_age, audience_gender, audience_location,
            impressions, week_start_date,
            engagement_score, conversion_score, cost_efficiency_score,
            ROUND(((engagement_score * 0.35) + (conversion_score * 0.45) + (cost_efficiency_score * 0.20))::numeric, 2) AS pis
        FROM normalize_data
    )
    SELECT * FROM pis_score
';

RAISE NOTICE 'Incremental load: mart_recommendations...';

EXECUTE '
    DELETE FROM mart_recommendations
    WHERE week_start_date = (SELECT MAX(week_start_date) FROM mart_pis_scores);

    INSERT INTO mart_recommendations
    WITH ranked AS (
        SELECT *,
            RANK() OVER(PARTITION BY week_start_date ORDER BY pis DESC) AS pis_rank
        FROM mart_pis_scores
        WHERE week_start_date = (SELECT MAX(week_start_date) FROM mart_pis_scores)
    ),
    winner AS (
        SELECT * FROM ranked WHERE pis_rank = 1
    )
    SELECT * FROM winner
';

RAISE NOTICE 'Incremental load complete!';
END;
$$;