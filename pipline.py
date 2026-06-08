import pandas as pd
import numpy as np
from sqlalchemy import create_engine
import psycopg2
from pytrends.request import TrendReq
from datetime import datetime
import time

def get_db_connection():
    """
    Create and return database connection
    """
    engine = create_engine(
        'postgresql://postgres:Sophy*Temi06@localhost:5432/ad_placement_db'
    )
    print("Connected to PostgreSQL successfully!")
    return engine
    

def generate_platform_data():
    """
    Auto-generate weekly platform performance data
    with realistic missing values mimicking real ad platform behavior
    """
    # Set weekly seed so data changes every week but is consistent within the same week
    np.random.seed(int(datetime.now().strftime('%Y%W')))
    
    # Define all platform combinations
    platforms = ['TikTok', 'Instagram', 'X', 'Facebook']
    content_types = ['Short Video', 'Carousel', 'Static Image', 'Text Post']
    time_blocks = ['Morning', 'Afternoon', 'Evening', 'Night']
    age_groups = ['18-24', '25-30', '40-50']
    genders = ['Male', 'Female']
    locations = ['Lagos', 'Abuja', 'Port Harcourt', 'Others']

    # Base performance rates per platform (modeled on DataReportal Nigeria 2024)
    base_rates = {
        'TikTok':    {'eng': 0.08, 'conv': 0.04, 'cost': 1200},
        'Instagram': {'eng': 0.06, 'conv': 0.035, 'cost': 1500},
        'X':         {'eng': 0.04, 'conv': 0.025, 'cost': 900},
        'Facebook':  {'eng': 0.05, 'conv': 0.03,  'cost': 1100},
    }

    # Multipliers for time of day
    time_multipliers = {
        'Morning':   0.85,
        'Afternoon': 0.90,
        'Evening':   1.10,
        'Night':     1.25  # Best time for Nigerian Gen Z
    }

    # Multipliers for content type
    content_multipliers = {
        'Short Video':  1.20,
        'Carousel':     1.10,
        'Static Image': 0.90,
        'Text Post':    0.75
    }

    # Realistic missing value probabilities per field
    missing_probs = {
        'engagement_rate': 0.03,  # 3% missing
        'conversion_rate': 0.05,  # 5% missing — conversion harder to track
        'cost_per_result': 0.04,  # 4% missing — cost not always reported
        'impressions':     0.02,  # 2% missing
    }

    rows = []

    # Generate one row per unique combination
    for platform in platforms:
        for content in content_types:
            for time_block in time_blocks:
                for age in age_groups:
                    for gender in genders:
                        for location in locations:

                            base = base_rates[platform]
                            t_mult = time_multipliers[time_block]
                            c_mult = content_multipliers[content]

                            # Calculate metrics with random variation
                            eng_rate = round(base['eng'] * t_mult * c_mult * np.random.uniform(0.85, 1.15), 4)
                            conv_rate = round(base['conv'] * t_mult * c_mult * np.random.uniform(0.85, 1.15), 4)
                            cost = round(base['cost'] * np.random.uniform(0.90, 1.10), 2)
                            impressions = int(np.random.uniform(5000, 50000))

                            # Introduce realistic missing values
                            if np.random.random() < missing_probs['engagement_rate']:
                                eng_rate = None
                            if np.random.random() < missing_probs['conversion_rate']:
                                conv_rate = None
                            if np.random.random() < missing_probs['cost_per_result']:
                                cost = None
                            if np.random.random() < missing_probs['impressions']:
                                impressions = None

                            rows.append({
                                'platform': platform,
                                'content_type': content,
                                'time_block': time_block,
                                'audience_age': age,
                                'audience_gender': gender,
                                'audience_location': location,
                                'engagement_rate': eng_rate,
                                'conversion_rate': conv_rate,
                                'cost_per_result': cost,
                                'impressions': impressions,
                                'week_start_date': pd.Timestamp.now().floor('7D')
                            })

    df_platform = pd.DataFrame(rows)

    # Print missing value report
    print(f"Platform data generated successfully!")
    print(f"   Total rows: {len(df_platform)}")
    print(f"   Week: {df_platform['week_start_date'].iloc[0]}")
    print(f"\nMissing value report:")
    for col in ['engagement_rate', 'conversion_rate', 'cost_per_result', 'impressions']:
        missing = df_platform[col].isna().sum()
        pct = round(missing / len(df_platform) * 100, 1)
        print(f"   {col}: {missing} missing ({pct}%)")

    return df_platform    


def pull_google_trends():
    """
    Pull Google Trends data for Nigerian fintech keywords
    Returns a wide format dataframe
    """
    keywords = ['opay', 'cowrywise', 'piggyvest',
                'send money nigeria', 'mobile banking nigeria']

    pytrends = TrendReq(hl='en-NG', tz=60, timeout=(10, 25))

    # Wait to avoid Google rate limiting (429 error)
    print("Waiting 30 seconds before requesting Google Trends...")
    time.sleep(30)

    try:
        pytrends.build_payload(keywords, geo='NG', timeframe='now 7-d')
        time.sleep(10)

        df_trends = pytrends.interest_over_time()
        df_trends = df_trends.reset_index()
        df_trends['pulled_at'] = pd.Timestamp.now()
        df_trends['week_start_date'] = pd.Timestamp.now().floor('7D')

        print("Google Trends data pulled successfully!")
        print(f"   Rows pulled: {len(df_trends)}")

        return df_trends, keywords

    except Exception as e:
        print(f"Error pulling Google Trends: {e}")
        print("Google may be rate limiting. Wait 15-30 minutes and try again.")
        return None, keywords

def reshape_trends_data(df_trends, keywords):
    """
    Reshape wide format Google Trends data to long format
    ready for PostgreSQL loading
    """
    # Melt wide format (one column per keyword) into long format (one row per keyword)
    df_trends_long = df_trends.melt(
        id_vars=['date', 'pulled_at', 'week_start_date'],
        value_vars=keywords,
        var_name='keyword',
        value_name='search_interest'
    )
    
    # Rename date column to match database schema
    df_trends_long = df_trends_long.rename(columns={'date': 'trend_date'})
    
    # Add region column — all data is Nigeria
    df_trends_long['region'] = 'Nigeria'
    
    # Drop isPartial column added by pytrends (not needed)
    df_trends_long = df_trends_long.drop(columns=['isPartial'], errors='ignore')
    
    # Reorder columns to match raw_google_trends table schema
    df_trends_long = df_trends_long[[
        'trend_date',
        'keyword',
        'search_interest',
        'region',
        'week_start_date',
        'pulled_at'
    ]]
    
    print(f"Trends reshaped successfully!")
    print(f"   Total rows: {len(df_trends_long)}")
    print(f"   Keywords: {df_trends_long['keyword'].unique()}")
    print(f"   Date range: {df_trends_long['trend_date'].min()} → {df_trends_long['trend_date'].max()}")
    
    return df_trends_long


def load_trends_to_postgres(df_trends_long, engine):
    """
    Load reshaped Google Trends data into raw_google_trends table
    """
    try:
        from sqlalchemy import inspect
        
        # Check if table already exists
        inspector = inspect(engine)
        table_exists = 'raw_google_trends' in inspector.get_table_names()

        # Append if table exists, replace if first time
        df_trends_long.to_sql(
            name='raw_google_trends',
            con=engine,
            if_exists='append' if table_exists else 'replace',
            index=False,
            method='multi'
        )
        print(f"Google Trends data loaded!")
        print(f"   Table existed: {table_exists}")
        print(f"   Rows inserted: {len(df_trends_long)}")

    except Exception as e:
        print(f"Error loading Google Trends: {e}")
        

def load_platform_to_postgres(df_platform, engine):
    """
    Load generated platform performance data into raw_platform_performance table
    """
    try:

        # Check if table already exists
        inspector = inspect(engine)
        table_exists = 'raw_platform_performance' in inspector.get_table_names()

        # Append if table exists, replace if first time
        df_platform.to_sql(
            name='raw_platform_performance',
            con=engine,
            if_exists='append' if table_exists else 'replace',
            index=False,
            method='multi'
        )
        print(f"Platform data loaded!")
        print(f"   Table existed: {table_exists}")
        print(f"   Rows inserted: {len(df_platform)}")

    except Exception as e:
        print(f"Error loading platform data: {e}")

def run_stored_procedures():
    """
    Execute staging and mart stored procedures
    to clean and transform newly loaded raw data
    """
    try:
        # Connect using psycopg2 for executing stored procedures
        conn = psycopg2.connect(
            host='localhost',
            database='ad_placement_db',
            user='postgres',
            password='Sophy*Temi06',
            port=5432
        )
        cursor = conn.cursor()

        # Run staging incremental load — cleans raw data into silver layer
        print("Running sp_load_stg_incremental...")
        cursor.execute("CALL sp_load_stg_incremental();")
        conn.commit()
        print("Staging incremental load complete!")

        # Run mart incremental load — calculates PIS scores and recommendations
        print("Running sp_load_mart_incremental...")
        cursor.execute("CALL sp_load_mart_incremental();")
        conn.commit()
        print("Mart incremental load complete!")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Error running stored procedures: {e}")        
        
def run_pipeline():
    """
    Master function that runs the full pipeline in order:
    1. Pull Google Trends data
    2. Generate platform performance data
    3. Load both to raw tables in PostgreSQL
    4. Run stored procedures to clean and build mart layer
    """
    print("PIPELINE STARTED")
    print(f"Run time: {datetime.now()}")

    # Step 1 — Get database connection
    engine = get_db_connection()

    # Step 2 — Pull Google Trends data
    df_trends, keywords = pull_google_trends()

    # Step 3 — Reshape and load Google Trends
    if df_trends is not None:
        df_trends_long = reshape_trends_data(df_trends, keywords)
        load_trends_to_postgres(df_trends_long, engine)
    else:
        print("Skipping Google Trends load — no data pulled.")

    # Step 4 — Generate and load platform performance data
    df_platform = generate_platform_data()
    load_platform_to_postgres(df_platform, engine)

    # Step 5 — Run stored procedures to clean and build mart layer
    run_stored_procedures()
 
    print("PIPELINE COMPLETE")
    print(f"Finished: {datetime.now()}")
   


# Entry point — runs when script is executed directly
if __name__ == "__main__":
    run_pipeline()        