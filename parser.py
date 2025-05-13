from pyspark.sql import functions as F
from pyspark.sql.types import *
import ast
import re

def parse_nested_dict_string_with_parent(df, string_column_name):
    """
    Parse a string column with structure like Key:{'key1':'val1',...} Key2:{'key2':'val2'...}
    into flattened key-value pairs with separate parent key column
    """
    
    # UDF to parse the complex string structure
    @F.udf(returnType=ArrayType(StructType([
        StructField("parent_key", StringType(), True),
        StructField("full_key", StringType(), True),
        StructField("value", StringType(), True)
    ])))
    def parse_string_to_kv_pairs(s):
        if not s:
            return []
        
        result = []
        
        # Pattern to match Key:{'key1':'val1',...}
        pattern = r'([^:]+?):\s*(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})'
        
        matches = re.findall(pattern, s, re.DOTALL)
        
        for parent_key, dict_str in matches:
            parent_key = parent_key.strip()
            
            try:
                # Try to parse the dictionary string
                # Replace single quotes with double quotes for JSON parsing
                json_str = dict_str.replace("'", '"')
                data = json.loads(json_str)
            except:
                try:
                    # If JSON parsing fails, try with ast.literal_eval
                    data = ast.literal_eval(dict_str)
                except:
                    # If both fail, add as raw value
                    result.append({
                        "parent_key": parent_key,
                        "full_key": parent_key,
                        "value": dict_str
                    })
                    continue
            
            # Recursively flatten the nested dictionary
            def flatten_dict(d, prefix=''):
                items = []
                for k, v in d.items():
                    new_key = f"{prefix}.{k}" if prefix else k
                    full_key = f"{parent_key}.{new_key}"
                    
                    if isinstance(v, dict):
                        items.extend(flatten_dict(v, new_key))
                    else:
                        items.append({
                            "parent_key": parent_key,
                            "full_key": full_key,
                            "value": str(v)
                        })
                return items
            
            result.extend(flatten_dict(data))
        
        return result
    
    # Apply the UDF to create an array of key-value pairs
    df_with_kv = df.withColumn("kv_pairs", parse_string_to_kv_pairs(F.col(string_column_name)))
    
    # Explode the array to create separate rows for each key-value pair
    df_exploded = df_with_kv.select(
        "*",
        F.explode("kv_pairs").alias("parsed_kv")  # Changed alias to avoid conflict
    ).select(
        "*",
        F.col("parsed_kv.parent_key").alias("parent_key"),
        F.col("parsed_kv.full_key").alias("parsed_key"),
        F.col("parsed_kv.value").alias("parsed_value")
    )
    
    return df_exploded

# Alternative approach with more detailed parsing
def parse_with_hierarchy(df, string_column_name):
    """
    Parse with complete hierarchy information
    """
    
    @F.udf(returnType=ArrayType(StructType([
        StructField("top_level_key", StringType(), True),
        StructField("nested_path", StringType(), True),
        StructField("full_path", StringType(), True),
        StructField("value", StringType(), True)
    ])))
    def parse_hierarchical(s):
        if not s:
            return []
        
        result = []
        
        # State machine approach for parsing
        i = 0
        while i < len(s):
            # Skip whitespace
            while i < len(s) and s[i].isspace():
                i += 1
            
            if i >= len(s):
                break
            
            # Find the top-level key (everything before ':')
            key_start = i
            while i < len(s) and s[i] != ':':
                i += 1
            
            if i >= len(s):
                break
                
            top_level_key = s[key_start:i].strip()
            i += 1  # Skip ':'
            
            # Skip whitespace after ':'
            while i < len(s) and s[i].isspace():
                i += 1
            
            # Now we should have a '{'
            if i >= len(s) or s[i] != '{':
                continue
                
            # Find matching closing brace
            brace_count = 0
            dict_start = i
            
            while i < len(s):
                if s[i] == '{':
                    brace_count += 1
                elif s[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        break
                i += 1
            
            if brace_count != 0:
                continue
                
            i += 1  # Include the closing brace
            dict_str = s[dict_start:i]
            
            try:
                # Parse the dictionary
                data = ast.literal_eval(dict_str)
                
                # Flatten nested structure with hierarchy
                def flatten_with_hierarchy(obj, path=[]):
                    items = []
                    
                    if isinstance(obj, dict):
                        for k, v in obj.items():
                            new_path = path + [k]
                            if isinstance(v, dict):
                                items.extend(flatten_with_hierarchy(v, new_path))
                            else:
                                nested_path = '.'.join(new_path)
                                full_path = f"{top_level_key}.{nested_path}"
                                
                                items.append({
                                    "top_level_key": top_level_key,
                                    "nested_path": nested_path,
                                    "full_path": full_path,
                                    "value": str(v)
                                })
                    
                    return items
                
                result.extend(flatten_with_hierarchy(data))
                
            except:
                # If parsing fails, add as a single entry
                result.append({
                    "top_level_key": top_level_key,
                    "nested_path": "",
                    "full_path": top_level_key,
                    "value": dict_str
                })
        
        return result
    
    # Create the parsed columns - FIXED VERSION
    df_parsed = df.withColumn("parsed_data", parse_hierarchical(F.col(string_column_name)))
    
    # Explode the array with different alias to avoid conflict
    df_exploded = df_parsed.select(
        "*",
        F.explode("parsed_data").alias("exploded_data")  # Changed alias
    )
    
    # Now select the final columns
    df_final = df_exploded.select(
        "*",
        F.col("exploded_data.top_level_key").alias("top_level_key"),
        F.col("exploded_data.nested_path").alias("nested_path"),
        F.col("exploded_data.full_path").alias("full_path"),
        F.col("exploded_data.value").alias("parsed_value")
    ).drop("parsed_data", "exploded_data")
    
    return df_final

# Alternative approach: drop the intermediate column before selecting
def parse_with_hierarchy_v2(df, string_column_name):
    """
    Alternative version that avoids the ambiguity error
    """
    
    @F.udf(returnType=ArrayType(StructType([
        StructField("top_level_key", StringType(), True),
        StructField("nested_path", StringType(), True),
        StructField("full_path", StringType(), True),
        StructField("value", StringType(), True)
    ])))
    def parse_hierarchical(s):
        # Same implementation as above
        if not s:
            return []
        
        result = []
        
        # State machine approach for parsing
        i = 0
        while i < len(s):
            # Skip whitespace
            while i < len(s) and s[i].isspace():
                i += 1
            
            if i >= len(s):
                break
            
            # Find the top-level key (everything before ':')
            key_start = i
            while i < len(s) and s[i] != ':':
                i += 1
            
            if i >= len(s):
                break
                
            top_level_key = s[key_start:i].strip()
            i += 1  # Skip ':'
            
            # Skip whitespace after ':'
            while i < len(s) and s[i].isspace():
                i += 1
            
            # Now we should have a '{'
            if i >= len(s) or s[i] != '{':
                continue
                
            # Find matching closing brace
            brace_count = 0
            dict_start = i
            
            while i < len(s):
                if s[i] == '{':
                    brace_count += 1
                elif s[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        break
                i += 1
            
            if brace_count != 0:
                continue
                
            i += 1  # Include the closing brace
            dict_str = s[dict_start:i]
            
            try:
                # Parse the dictionary
                data = ast.literal_eval(dict_str)
                
                # Flatten nested structure with hierarchy
                def flatten_with_hierarchy(obj, path=[]):
                    items = []
                    
                    if isinstance(obj, dict):
                        for k, v in obj.items():
                            new_path = path + [k]
                            if isinstance(v, dict):
                                items.extend(flatten_with_hierarchy(v, new_path))
                            else:
                                nested_path = '.'.join(new_path)
                                full_path = f"{top_level_key}.{nested_path}"
                                
                                items.append({
                                    "top_level_key": top_level_key,
                                    "nested_path": nested_path,
                                    "full_path": full_path,
                                    "value": str(v)
                                })
                    
                    return items
                
                result.extend(flatten_with_hierarchy(data))
                
            except:
                # If parsing fails, add as a single entry
                result.append({
                    "top_level_key": top_level_key,
                    "nested_path": "",
                    "full_path": top_level_key,
                    "value": dict_str
                })
        
        return result
    
    # Create temporary column with parsed data
    df_temp = df.withColumn("_parsed_data", parse_hierarchical(F.col(string_column_name)))
    
    # Explode and select in one step to avoid ambiguity
    df_final = df_temp.selectExpr(
        "*",
        "explode(_parsed_data) as parsed_struct"
    ).selectExpr(
        "*",
        "parsed_struct.top_level_key as top_level_key",
        "parsed_struct.nested_path as nested_path",
        "parsed_struct.full_path as full_path",
        "parsed_struct.value as parsed_value"
    ).drop("_parsed_data", "parsed_struct")
    
    return df_final

# Example usage with sample data:
if __name__ == "__main__":
    from pyspark.sql import SparkSession
    
    spark = SparkSession.builder.appName("ParseNestedDicts").getOrCreate()
    
    # Sample data with nested dictionaries and spaces
    sample_data = [
        ("Key1:{'user name':'John Doe','details':{'age':'30','city':'New York, NY'}} Key2:{'product':'laptop,mouse','price':'1000'}",),
        ("MainKey:{'level1':{'level2':{'value':'nested,value'},'another':'test'}} SecondKey:{'simple':'value'}",)
    ]
    
    # Note: renamed the column from "data" to "input_data" to avoid confusion
    df = spark.createDataFrame(sample_data, ["input_data"])
    
    print("Using parse_nested_dict_string_with_parent:")
    result1 = parse_nested_dict_string_with_parent(df, "input_data")
    result1.show(truncate=False)
    
    print("\nUsing parse_with_hierarchy (fixed):")
    result2 = parse_with_hierarchy(df, "input_data")
    result2.show(truncate=False)
    
    print("\nUsing parse_with_hierarchy_v2:")
    result3 = parse_with_hierarchy_v2(df, "input_data")
    result3.show(truncate=False)
