def parse_complex_string_column(df, column_name):
    """
    Parse a complex string column containing embedded dictionaries like:
    'abcd: {'key1':'value1',...} defg:{<another dict>}'
    
    Args:
        df: Spark DataFrame
        column_name: Name of the column containing the complex strings
        
    Returns:
        Spark DataFrame with the parsed and flattened data
    """
    # Collect the data to process in Python
    collected_data = df.select("*").collect()
    
    # Process each row
    all_rows = []
    for row in collected_data:
        row_dict = row.asDict()
        id_columns = {k: v for k, v in row_dict.items() if k != column_name}
        complex_str = row_dict[column_name]
        
        if not complex_str:
            # Handle empty strings
            flattened_row = id_columns.copy()
            flattened_row["dict_prefix"] = None
            all_rows.append(flattened_row)
            continue
            
        # Extract prefix and dictionary pairs
        pattern = r'(\w+):\s*(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})'
        matches = re.finditer(pattern, complex_str)
        
        found_match = False
        for match in matches:
            found_match = True
            prefix = match.group(1)
            dict_str = match.group(2)
            
            # Replace single quotes with double quotes for standard JSON
            normalized_str = dict_str.replace("'", '"')
            
            # Initialize dictionary to store parsed data
            parsed_dict = {}
            
            try:
                # Try standard JSON parsing first
                parsed_dict = json.loads(normalized_str)
            except json.JSONDecodeError:
                # If that fails, use a more forgiving approach
                # Extract key-value pairs using regex
                key_val_pattern = r'"([^"]+)"\s*:\s*(?:"([^"]+)"|(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})|(\[[^\[\]]*\])|(\d+)|true|false|null)'
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
            
            # Start with base fields
            result_row = id_columns.copy()
            result_row["dict_prefix"] = prefix
            
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
            flattened = flatten_dict(parsed_dict)
            result_row.update(flattened)
            
            all_rows.append(result_row)
        
        # Handle case where no dictionary was found
        if not found_match:
            flattened_row = id_columns.copy()
            flattened_row["dict_prefix"] = None
            all_rows.append(flattened_row)
    
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
    return spark.createDataFrame(normalized_rows)
