from pyspark.sql import functions as F
from pyspark.sql.types import *
import ast
import re

def parse_nested_with_lists(df, string_column_name):
    """
    Parse a string column that can contain nested dicts and lists
    Lists are expanded to multiple rows
    """
    
    @F.udf(returnType=ArrayType(StructType([
        StructField("top_level_key", StringType(), True),
        StructField("full_path", StringType(), True),
        StructField("value", StringType(), True)
    ])))
    def parse_complex_structure(s):
        if not s:
            return []
        
        result = []
        
        # Pattern to match Key:{'key1':'val1',...} or Key:[...]
        pattern = r'([^:]+?):\s*(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}|\[[^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*\])'
        
        matches = re.findall(pattern, s, re.DOTALL)
        
        for parent_key, structure_str in matches:
            parent_key = parent_key.strip()
            
            try:
                # Parse the structure (dict or list)
                data = ast.literal_eval(structure_str)
                
                # Recursively flatten nested structure with list handling
                def flatten_structure(obj, path=[]):
                    items = []
                    
                    if isinstance(obj, dict):
                        for k, v in obj.items():
                            new_path = path + [k]
                            items.extend(flatten_structure(v, new_path))
                    
                    elif isinstance(obj, list):
                        # For lists, create indexed paths
                        for i, item in enumerate(obj):
                            new_path = path + [f"[{i}]"]
                            items.extend(flatten_structure(item, new_path))
                    
                    else:
                        # Leaf value
                        if path:
                            full_key = f"{parent_key}.{'.'.join(path)}"
                        else:
                            full_key = parent_key
                        
                        items.append({
                            "top_level_key": parent_key,
                            "full_path": full_key,
                            "value": str(obj)
                        })
                    
                    return items
                
                result.extend(flatten_structure(data))
                
            except:
                # If parsing fails, add as a single entry
                result.append({
                    "top_level_key": parent_key,
                    "full_path": parent_key,
                    "value": structure_str
                })
        
        return result
    
    # Apply the UDF and explode
    df_parsed = df.withColumn("parsed_items", parse_complex_structure(F.col(string_column_name)))
    
    df_final = df_parsed.select(
        "*",
        F.explode("parsed_items").alias("item")
    ).select(
        "*",
        F.col("item.top_level_key").alias("top_level_key"),
        F.col("item.full_path").alias("full_path"),
        F.col("item.value").alias("parsed_value")
    ).drop("parsed_items", "item")
    
    return df_final

def parse_with_advanced_list_handling(df, string_column_name):
    """
    Advanced parser that handles complex nested structures with lists and dicts
    Provides more detailed path information
    """
    
    @F.udf(returnType=ArrayType(StructType([
        StructField("top_level_key", StringType(), True),
        StructField("path_elements", ArrayType(StringType()), True),  # Array of path elements
        StructField("full_path", StringType(), True),
        StructField("path_type", StringType(), True),  # "dict_key" or "list_index"
        StructField("value", StringType(), True),
        StructField("value_type", StringType(), True)  # Type of the value
    ])))
    def parse_advanced(s):
        if not s:
            return []
        
        result = []
        
        # Parse top-level structures
        i = 0
        while i < len(s):
            # Skip whitespace
            while i < len(s) and s[i].isspace():
                i += 1
            
            if i >= len(s):
                break
            
            # Find the top-level key
            key_start = i
            while i < len(s) and s[i] != ':':
                i += 1
            
            if i >= len(s):
                break
                
            top_level_key = s[key_start:i].strip()
            i += 1  # Skip ':'
            
            # Skip whitespace
            while i < len(s) and s[i].isspace():
                i += 1
            
            if i >= len(s):
                break
            
            # Determine structure type and find closing delimiter
            if s[i] == '{':
                # Dictionary
                closing_char = '}'
            elif s[i] == '[':
                # List
                closing_char = ']'
            else:
                continue
            
            # Find matching closing delimiter
            delimiter_count = 0
            struct_start = i
            
            while i < len(s):
                if s[i] in '{[':
                    delimiter_count += 1
                elif s[i] in '}]':
                    delimiter_count -= 1
                    if delimiter_count == 0:
                        break
                i += 1
            
            if delimiter_count != 0:
                continue
                
            i += 1  # Include the closing delimiter
            struct_str = s[struct_start:i]
            
            try:
                # Parse the structure
                data = ast.literal_eval(struct_str)
                
                # Advanced flattening with type information
                def flatten_advanced(obj, path_elements=[], path_types=[]):
                    items = []
                    
                    if isinstance(obj, dict):
                        for k, v in obj.items():
                            new_path_elements = path_elements + [k]
                            new_path_types = path_types + ["dict_key"]
                            
                            if isinstance(v, (dict, list)):
                                items.extend(flatten_advanced(v, new_path_elements, new_path_types))
                            else:
                                full_path = f"{top_level_key}.{'.'.join(new_path_elements)}"
                                
                                items.append({
                                    "top_level_key": top_level_key,
                                    "path_elements": new_path_elements,
                                    "full_path": full_path,
                                    "path_type": "dict_key",
                                    "value": str(v),
                                    "value_type": type(v).__name__
                                })
                    
                    elif isinstance(obj, list):
                        for i, item in enumerate(obj):
                            index_str = f"[{i}]"
                            new_path_elements = path_elements + [index_str]
                            new_path_types = path_types + ["list_index"]
                            
                            if isinstance(item, (dict, list)):
                                items.extend(flatten_advanced(item, new_path_elements, new_path_types))
                            else:
                                full_path = f"{top_level_key}.{'.'.join(new_path_elements)}"
                                
                                items.append({
                                    "top_level_key": top_level_key,
                                    "path_elements": new_path_elements,
                                    "full_path": full_path,
                                    "path_type": "list_index",
                                    "value": str(item),
                                    "value_type": type(item).__name__
                                })
                    
                    else:
                        # Handle case where top level is neither dict nor list
                        full_path = top_level_key if not path_elements else f"{top_level_key}.{'.'.join(path_elements)}"
                        
                        items.append({
                            "top_level_key": top_level_key,
                            "path_elements": path_elements,
                            "full_path": full_path,
                            "path_type": "value",
                            "value": str(obj),
                            "value_type": type(obj).__name__
                        })
                    
                    return items
                
                result.extend(flatten_advanced(data))
                
            except:
                # If parsing fails, add as a single entry
                result.append({
                    "top_level_key": top_level_key,
                    "path_elements": [],
                    "full_path": top_level_key,
                    "path_type": "error",
                    "value": struct_str,
                    "value_type": "unparsed"
                })
        
        return result
    
    # Apply the UDF and explode
    df_parsed = df.withColumn("parsed_items", parse_advanced(F.col(string_column_name)))
    
    df_final = df_parsed.select(
        "*",
        F.explode("parsed_items").alias("item")
    ).select(
        "*",
        F.col("item.top_level_key").alias("top_level_key"),
        F.col("item.path_elements").alias("path_elements"),
        F.col("item.full_path").alias("full_path"),
        F.col("item.path_type").alias("path_type"),
        F.col("item.value").alias("parsed_value"),
        F.col("item.value_type").alias("value_type")
    ).drop("parsed_items", "item")
    
    return df_final

# Example usage with sample data including lists:
if __name__ == "__main__":
    from pyspark.sql import SparkSession
    
    spark = SparkSession.builder.appName("ParseNestedDictsWithLists").getOrCreate()
    
    # Sample data with lists and nested structures
    sample_data = [
        # Basic dict with list
        ("Key1:{'items':['item1','item2','item3'],'count':3} Key2:{'values':[1,2,3]}",),
        
        # Nested lists and dicts
        ("Data:{'users':[{'name':'John','scores':[85,90,92]},{'name':'Jane','scores':[88,91,95]}]}",),
        
        # List at top level
        ("ListKey:['value1','value2',{'nested':'dict'},['nested','list']]",),
        
        # Mixed complex structure
        ("Complex:{'matrix':[[1,2,3],[4,5,6]],'metadata':{'rows':2,'cols':3},'tags':['2d','numeric']}",)
    ]
    
    df = spark.createDataFrame(sample_data, ["input_data"])
    
    print("Using parse_nested_with_lists:")
    result1 = parse_nested_with_lists(df, "input_data")
    result1.show(truncate=False)
    
    print("\nUsing parse_with_advanced_list_handling (with detailed path info):")
    result2 = parse_with_advanced_list_handling(df, "input_data")
    result2.show(truncate=False)
    
    # Show just a subset of columns for cleaner output
    print("\nSimplified view:")
    result2.select("top_level_key", "full_path", "parsed_value").show(truncate=False)
