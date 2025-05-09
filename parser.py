from pyspark.sql import SparkSession
from pyspark.sql.functions import col, explode, udf, to_json
from pyspark.sql.types import StringType, ArrayType, StructType, StructField, MapType
import re
import json
import pandas as pd

# Initialize Spark Session
spark = SparkSession.builder.appName("DictStringParser").getOrCreate()

# Sample data
sample_data = [
    ("row1", "abcd: {'key1':'value1', 'key2':{'nested1':'nestedval1'}} defg:{'key3':'value3', 'key4':{'nested2':'nestedval2'}}"),
    ("row2", "xyz: {'keyA':'valueA', 'keyB':'valueB'} pqr:{'keyC':{'deep1':{'deeper1':'deepest1'}}}"),
    ("row3", "single: {'simple':'value', 'list':[1,2,3]} empty:{}"),
]
schema = ["id", "complex_column"]
sample_df = spark.createDataFrame(sample_data, schema)

print("Original DataFrame:")
sample_df.show(truncate=False)

# Improved parser function that handles the JSON string better
def parse_complex_string(input_string):
    """Parse a complex string containing embedded dictionaries"""
    if input_string is None:
        return []
        
    # Find all dictionary-like structures with their prefixes
    pattern = r'(\w+):\s*(\{.*?\})'
    
    # Using regex to find all matches
    matches = re.finditer(pattern, input_string, re.DOTALL)
    
    result = []
    for match in matches:
        prefix = match.group(1)
        dict_str = match.group(2)
        
        # More careful JSON string preparation
        # Step 1: Replace single quotes with double quotes, but be careful with nested quotes
        dict_str = dict_str.replace("'", '"')
        
        # Step 2: Fix common JSON formatting issues
        # Replace any incorrectly formatted JSON like {"key":"value",} with proper format
        dict_str = re.sub(r',\s*}', '}', dict_str)
        
        try:
            # Parse the dictionary string
            parsed_dict = json.loads(dict_str)
            result.append({
                "prefix": prefix,
                "data": parsed_dict
            })
        except json.JSONDecodeError as e:
            print(f"Error parsing dictionary with prefix {prefix}: {e}")
            # Try a more manual approach for problematic JSON
            try:
                # Get key-value pairs manually
                manual_dict = {}
                # Simple pattern to extract key-value pairs
                kv_pattern = r'"([^"]+)"\s*:\s*"([^"]+)"'
                for kv_match in re.finditer(kv_pattern, dict_str):
                    k, v = kv_match.groups()
                    manual_dict[k] = v
                    
                # Also try to get numeric values
                num_pattern = r'"([^"]+)"\s*:\s*(\d+)'
                for num_match in re.finditer(num_pattern, dict_str):
                    k, v = num_match.groups()
                    manual_dict[k] = int(v)
                    
                result.append({
                    "prefix": prefix,
                    "data": manual_dict
                })
            except Exception:
                # If all else fails, just store the raw string
                result.append({
                    "prefix": prefix,
                    "data": {"raw_string": dict_str}
                })
            
    return result

# Step 3: Register UDF
parse_schema = ArrayType(
    StructType([
        StructField("prefix", StringType(), True),
        StructField("data", MapType(StringType(), StringType(), True), True)
    ])
)

parse_udf = udf(parse_complex_string, parse_schema)

# Step 4: Apply parser and explode results
parsed_df = sample_df.withColumn("parsed_data", parse_udf(col("complex_column")))
exploded_df = parsed_df.withColumn("parsed", explode("parsed_data"))

# Extract prefix and data
result_df = exploded_df.select(
    "id",
    col("parsed.prefix").alias("dict_prefix"),
    col("parsed.data").alias("dict_content")
)

print("\nExploded DataFrame with one dictionary per row:")
result_df.show(truncate=False)

# Since we're having trouble with the PySpark approach, let's extract directly in Python
# Collect the original data and process it completely in Python
collected_original = sample_df.collect()

# Completely manual parsing approach
def parse_string_to_dicts(complex_str):
    """Parse the complex string fully in Python"""
    results = []
    
    # Extract prefix and dictionary pairs
    pattern = r'(\w+):\s*(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})'
    matches = re.finditer(pattern, complex_str)
    
    for match in matches:
        prefix = match.group(1)
        dict_str = match.group(2)
        
        # Parse the dictionary string manually
        parsed_dict = {}
        
        # Replace single quotes with double quotes for standard JSON
        normalized_str = dict_str.replace("'", '"')
        
        try:
            # Try standard JSON parsing first
            parsed_dict = json.loads(normalized_str)
        except json.JSONDecodeError:
            # If that fails, use a more forgiving approach
            # Extract key-value pairs using regex
            key_val_pattern = r'"([^"]+)"\s*:\s*(?:"([^"]+)"|(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})|(\[[^\[\]]*\])|(\d+))'
            for kv_match in re.finditer(key_val_pattern, normalized_str):
                key = kv_match.group(1)
                # Check which value group matched
                if kv_match.group(2):  # String value
                    val = kv_match.group(2)
                elif kv_match.group(3):  # Nested dict
                    try:
                        val = json.loads(kv_match.group(3))
                    except:
                        val = kv_match.group(3)  # Keep as string if parsing fails
                elif kv_match.group(4):  # List
                    try:
                        val = json.loads(kv_match.group(4))
                    except:
                        val = kv_match.group(4)  # Keep as string if parsing fails
                elif kv_match.group(5):  # Number
                    val = int(kv_match.group(5))
                else:
                    val = None
                
                parsed_dict[key] = val
        
        results.append((prefix, parsed_dict))
    
    return results

# Process each row completely in Python
all_rows = []
for row in collected_original:
    id_val = row["id"]
    complex_str = row["complex_column"]
    
    # Parse the string to get all dictionaries
    parsed_dicts = parse_string_to_dicts(complex_str)
    
    for prefix, dict_data in parsed_dicts:
        # Start with base fields
        result_row = {
            "id": id_val,
            "dict_prefix": prefix
        }
        
        # Flatten dictionary recursively
        def flatten_dict(d, parent_key=''):
            items = {}
            for k, v in d.items():
                new_key = f"{parent_key}_{k}" if parent_key else k
                
                if isinstance(v, dict) and v:
                    nested_items = flatten_dict(v, new_key)
                    items.update(nested_items)
                else:
                    items[new_key] = v
            return items
        
        # Add flattened fields
        flattened = flatten_dict(dict_data)
        result_row.update(flattened)
        
        all_rows.append(result_row)

# Step 8: Create a DataFrame from processed rows
# First determine all possible columns
all_columns = set()
for row in all_rows:
    all_columns.update(row.keys())

# Ensure all rows have all columns (fill with None for missing values)
normalized_rows = []
for row in all_rows:
    normalized_row = {col: row.get(col) for col in all_columns}
    normalized_rows.append(normalized_row)

# Create DataFrame
final_df = spark.createDataFrame(normalized_rows)

print("\nFinal flattened DataFrame from manual parsing:")
final_df.show(truncate=False)
final_df.printSchema()

print("\nProcessing completed successfully!")
