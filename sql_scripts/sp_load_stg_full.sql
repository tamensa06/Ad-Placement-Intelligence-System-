
-- STAGING: PLATFORM PERFORMANCE

DROP TABLE IF EXISTS stg_platform_performance;

WITH checking_platform_data AS (
    SELECT 
        platform,
        content_type,
        time_block,
        audience_age,
        audience_gender,
        audience_location, -- changing the datatype 
        engagement_rate::float,
        conversion_rate::float,
        cost_per_result::float,
        impressions::integer,
        week_start_date
    FROM raw_platform_performance
),
null_flagged AS (
    SELECT *,
        CASE WHEN engagement_rate IS NULL THEN 1 ELSE 0 END AS engagement_rate_missing,
        CASE WHEN conversion_rate IS NULL THEN 1 ELSE 0 END AS conversion_rate_missing, -- checking for missing values
        CASE WHEN cost_per_result IS NULL THEN 1 ELSE 0 END AS cost_missing,
        CASE WHEN impressions IS NULL THEN 1 ELSE 0 END AS impressions_missing
    FROM checking_platform_data
),
null_handled AS (
    SELECT
        platform,
        content_type,
        time_block,
        audience_age,
        audience_gender,
        audience_location,
        COALESCE(engagement_rate, AVG(engagement_rate) OVER()) AS engagement_rate,
        COALESCE(conversion_rate, AVG(conversion_rate) OVER()) AS conversion_rate,
        COALESCE(cost_per_result, AVG(cost_per_result) OVER()) AS cost_per_result, -- handling missing values
        COALESCE(impressions, 0) AS impressions,
        week_start_date,
        engagement_rate_missing,
        conversion_rate_missing,
        cost_missing,
        impressions_missing
    FROM null_flagged
),
duplicate AS (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY platform, content_type, time_block,
                         audience_age, audience_gender,
                         audience_location
            ORDER BY platform, week_start_date DESC -- checking for duplicate 
        ) AS row_num
    FROM null_handled
),
remove_duplicate AS (
    SELECT * FROM duplicate -- moving duplicate 
    WHERE row_num = 1
),
add_id AS (
    SELECT
        ROW_NUMBER() OVER (ORDER BY platform, content_type, time_block) AS stg_id,-- creating table id
        *,
        NOW() AS stg_loaded_at
    FROM remove_duplicate
)
SELECT * INTO stg_platform_performance -- inserting cleaned data into table
FROM add_id;

-- validate
SELECT COUNT(*) FROM stg_platform_performance;



-- STAGING: GOOGLE TRENDS

DROP TABLE IF EXISTS stg_google_trends;

WITH checking_googletrend_data AS (
    SELECT
        trend_date::timestamp,
        keyword,                       -- changing the datatype    
        search_interest::float,
        INITCAP(region) AS region,
        week_start_date::date,
        pulled_at
    FROM raw_google_trends
),
check_nulls AS (
    SELECT *,
        CASE WHEN search_interest IS NULL THEN 1 ELSE 0 END AS search_interest_missing,
        CASE WHEN keyword IS NULL THEN 1 ELSE 0 END AS keyword_missing,
        CASE WHEN trend_date IS NULL THEN 1 ELSE 0 END AS trend_missing     -- checking for missing values
    FROM checking_googletrend_data
),
remove_nulls AS (
    SELECT
        COALESCE(trend_date, CURRENT_DATE) AS trend_date,
        COALESCE(keyword, 'not found') AS keyword,
        COALESCE(search_interest, AVG(search_interest) OVER()) AS search_interest,
        region,
        week_start_date,
        pulled_at, --handling missing values
        search_interest_missing,
        keyword_missing,
        trend_missing
    FROM check_nulls
),
filter_data AS (
    SELECT *
    FROM remove_nulls
    WHERE search_interest > 0 
    AND search_interest IS NOT NULL
    AND keyword IS NOT NULL
    AND trend_date IS NOT NULL
    AND keyword != 'not found'
),
standardize_text AS (
    SELECT
        trend_date,
        LOWER(keyword) AS keyword,
        search_interest,
        INITCAP(region) AS region, -- standardizing texts
        week_start_date,
        pulled_at,
        search_interest_missing,
        keyword_missing,
        trend_missing
    FROM filter_data
),
check_duplicate AS (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY keyword, trend_date, week_start_date -- checking of duplicate
            ORDER BY trend_date, week_start_date DESC
        ) AS row_num
    FROM standardize_text
),
remove_duplicate AS (
    SELECT * FROM check_duplicate  -- handling duplicate
    WHERE row_num = 1
),
add_id AS (
    SELECT
        ROW_NUMBER() OVER (ORDER BY trend_date, keyword) AS stg_id,
        trend_date,
        keyword,
        search_interest,
        region,
        week_start_date,
        pulled_at,
        search_interest_missing,
        keyword_missing,
        trend_missing,    -- creating a column id
        NOW() AS stg_loaded_at
    FROM remove_duplicate
)
SELECT * INTO stg_google_trends
FROM add_id;

-- validate
SELECT COUNT(*) FROM stg_google_trends;
SELECT COUNT(*) FROM stg_platform_performance;