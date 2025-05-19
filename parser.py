def parse_with_hierarchical_groups(df, string_column_name):
    """
    Advanced parser with hierarchical grouping identifiers
    Provides multiple levels of grouping
    """
    
    @F.udf(returnType=ArrayType(StructType([
        StructField("top_level_key", StringType(), True),
        StructField("full_path", StringType(), True),
        StructField("value", StringType(), True),
        StructField("row_id", StringType(), True),              # ID for the input row
        StructField("structure_id", StringType(), True),        # ID for the top-level structure
        StructField("parent_path", StringType(), True),         # Parent path
        StructField("object_type", StringType(), True),         # Type: dict, list, list_item, or value
        StructField("list_object_id", StringType(), True),      # ID for list objects
        StructField("list_item_index", IntegerType(), True)     # Index within list
    ])))
    def parse_with_hierarchy(s):
        if not s:
            return []
        
        result = []
        # Create a unique ID for this input row
        row_id = hashlib.md5(s.encode()).hexdigest()[:8]
        
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
            structure_id = f"{row_id}_{top_level_key}"
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
                object_type = "dict"
            elif s[i] == '[':
                # List
                closing_char = ']'
                object_type = "list"
            else:
                # Simple value
                simple_value_end = i
                while simple_value_end < len(s) and s[simple_value_end] not in " \t\n":
                    simple_value_end += 1
                
                result.append({
                    "top_level_key": top_level_key,
                    "full_path": top_level_key,
                    "value": s[i:simple_value_end].strip(),
                    "row_id": row_id,
                    "structure_id": structure_id,
                    "parent_path": "",
                    "object_type": "value",
                    "list_object_id": "",
                    "list_item_index": None
                })
                
                i = simple_value_end
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
                
                # Hierarchical flattening with detailed grouping
                def flatten_hierarchical(obj, path="", parent_path="", obj_type="", list_id="", list_idx=None):
                    items = []
                    
                    current_path = path
                    
                    if isinstance(obj, dict):
                        for k, v in obj.items():
                            new_path = f"{path}.{k}" if path else f"{top_level_key}.{k}"
                            
                            if isinstance(v, dict):
                                new_obj_type = "dict"
                                new_list_id = list_id
                                new_list_idx = None
                            elif isinstance(v, list):
                                new_obj_type = "list"
                                new_list_id = f"{structure_id}_{new_path}"
                                new_list_idx = None
                            else:
                                # Add leaf value
                                items.append({
                                    "top_level_key": top_level_key,
                                    "full_path": new_path,
                                    "value": str(v),
                                    "row_id": row_id,
                                    "structure_id": structure_id,
                                    "parent_path": current_path if current_path else top_level_key,
                                    "object_type": "value",
                                    "list_object_id": list_id,
                                    "list_item_index": list_idx
                                })
                                continue
                            
                            # Recurse for nested objects
                            items.extend(flatten_hierarchical(
                                v, new_path, current_path if current_path else top_level_key,
                                new_obj_type, new_list_id, new_list_idx
                            ))
                    
                    elif isinstance(obj, list):
                        # Process list items
                        for i, item in enumerate(obj):
                            new_path = f"{path}.[{i}]" if path else f"{top_level_key}.[{i}]"
                            
                            if isinstance(item, (dict, list)):
                                # Recurse with list item info
                                new_obj_type = "dict" if isinstance(item, dict) else "list"
                                items.extend(flatten_hierarchical(
                                    item, new_path, current_path if current_path else top_level_key,
                                    f"{new_obj_type}_in_list", list_id, i
                                ))
                            else:
                                # Add leaf list item
                                items.append({
                                    "top_level_key": top_level_key,
                                    "full_path": new_path,
                                    "value": str(item),
                                    "row_id": row_id,
                                    "structure_id": structure_id,
                                    "parent_path": current_path if current_path else top_level_key,
                                    "object_type": "list_item",
                                    "list_object_id": list_id,
                                    "list_item_index": i
                                })
                    
                    else:
                        # Should only happen for top-level scalar values
                        items.append({
                            "top_level_key": top_level_key,
                            "full_path": path if path else top_level_key,
                            "value": str(obj),
                            "row_id": row_id,
                            "structure_id": structure_id,
                            "parent_path": parent_path,
                            "object_type": obj_type,
                            "list_object_id": list_id,
                            "list_item_index": list_idx
                        })
                    
                    return items
                
                # Start recursion with top-level object info
                result.extend(flatten_hierarchical(
                    data, "", "", object_type, 
                    f"{structure_id}" if object_type == "list" else "", None
                ))
                
            except:
                # If parsing fails, add as a single entry
                result.append({
                    "top_level_key": top_level_key,
                    "full_path": top_level_key,
                    "value": struct_str,
                    "row_id": row_id,
                    "structure_id": structure_id,
                    "parent_path": "",
                    "object_type": "unparsed",
                    "list_object_id": "",
                    "list_item_index": None
                })
        
        return result
    
    # Apply the UDF and explode
    df_parsed = df.withColumn("parsed_items", parse_with_hierarchy(F.col(string_column_name)))
    
    df_final = df_parsed.select(
        "*",
        F.explode("parsed_items").alias("item")
    ).select(
        "*",
        F.col("item.top_level_key").alias("top_level_key"),
        F.col("item.full_path").alias("full_path"),
        F.col("item.value").alias("parsed_value"),
        F.col("item.row_id").alias("row_id"),
        F.col("item.structure_id").alias("structure_id"),
        F.col("item.parent_path").alias("parent_path"),
        F.col("item.object_type").alias("object_type"),
        F.col("item.list_object_id").alias("list_object_id"),
        F.col("item.list_item_index").alias("list_item_index")
    ).drop("parsed_items", "item")
    
    return df_final
