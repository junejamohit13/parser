# Databricks SCD Type 2 Implementation using MERGE
from datetime import datetime

# Configuration
SOURCE_SCHEMA = "bronze"
SOURCE_TABLE = "source_customers"
TARGET_SCHEMA = "silver"
TARGET_TABLE = "dim_customers"

# Define business keys and columns to track
BUSINESS_KEY = "customer_id"
SCD_COLUMNS = ["customer_name", "email", "address", "city", "state", "zip_code"]

# Capture timestamp once for consistency
current_ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

# Create target table if not exists
spark.sql(f"""
CREATE TABLE IF NOT EXISTS {TARGET_SCHEMA}.{TARGET_TABLE} (
    customer_id BIGINT,
    customer_name STRING,
    email STRING,
    address STRING,
    city STRING,
    state STRING,
    zip_code STRING,
    effective_start_date TIMESTAMP,
    effective_end_date TIMESTAMP,
    is_current BOOLEAN,
    version INT
)
USING DELTA
""")

# Create temporary view with the source data and consistent timestamp
spark.sql(f"""
CREATE OR REPLACE TEMPORARY VIEW source_with_ts AS
SELECT 
    *,
    timestamp('{current_ts}') as merge_time
FROM {SOURCE_SCHEMA}.{SOURCE_TABLE}
""")

# SCD Type 2 MERGE statement
merge_query = f"""
MERGE INTO {TARGET_SCHEMA}.{TARGET_TABLE} AS target
USING source_with_ts AS source
ON source.{BUSINESS_KEY} = target.{BUSINESS_KEY} 
   AND target.is_current = true

-- Close existing record when data changes
WHEN MATCHED AND (
    {' OR '.join([f'source.{col} != target.{col}' for col in SCD_COLUMNS])}
) THEN 
    UPDATE SET
        target.effective_end_date = source.merge_time,
        target.is_current = false

-- Insert new records
WHEN NOT MATCHED THEN
    INSERT (
        {BUSINESS_KEY},
        {', '.join(SCD_COLUMNS)},
        effective_start_date,
        effective_end_date,
        is_current,
        version
    )
    VALUES (
        source.{BUSINESS_KEY},
        {', '.join([f'source.{col}' for col in SCD_COLUMNS])},
        source.merge_time,
        timestamp('9999-12-31 23:59:59'),
        true,
        1
    )
"""

# Execute the merge
spark.sql(merge_query)

# Insert new versions for changed records
insert_new_versions = f"""
INSERT INTO {TARGET_SCHEMA}.{TARGET_TABLE}
SELECT 
    s.{BUSINESS_KEY},
    {', '.join([f's.{col}' for col in SCD_COLUMNS])},
    timestamp('{current_ts}') as effective_start_date,
    timestamp('9999-12-31 23:59:59') as effective_end_date,
    true as is_current,
    t.version + 1 as version
FROM {SOURCE_SCHEMA}.{SOURCE_TABLE} s
INNER JOIN {TARGET_SCHEMA}.{TARGET_TABLE} t
    ON s.{BUSINESS_KEY} = t.{BUSINESS_KEY}
WHERE t.effective_end_date = timestamp('{current_ts}')
    AND ({' OR '.join([f's.{col} != t.{col}' for col in SCD_COLUMNS])})
"""

spark.sql(insert_new_versions)

# Clean up temporary view
spark.sql("DROP VIEW IF EXISTS source_with_ts")

print(f"SCD Type 2 load completed for {TARGET_SCHEMA}.{TARGET_TABLE}")
