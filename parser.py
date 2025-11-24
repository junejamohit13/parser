const handleExport = async () => {
    setLoading(true);
    try {
      // Get the visible rows from the table (what user sees)
      const visibleRows = table.getRowModel().rows.map(row => row.original);

      // Send visible data and selected radio option to backend
      const response = await fetch(`${API_BASE_URL}/export/${tableKey}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          option: exportOption, // The radio button option selected
          data: visibleRows     // The visible table data
        })
      });

      if (!response.ok) throw new Error('Export failed');

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${tableKey}_export_${Date.now()}.xlsx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      alert('Export successful!');
    } catch (error) {
      console.error('Export error:', error);
      alert('Export failed. Make sure the backend is running.');
    } finally {
      setLoading(false);
    }
  };
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
def generate_excel(data: List[dict], columns: List[str], table_key: str) -> BytesIO:
    """
    Generate an Excel file from the provided data
    """
    wb = Workbook()
    ws = wb.active
    ws.title = table_key.capitalize()

    # Header styling
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=12)
    header_alignment = Alignment(horizontal="center", vertical="center")

    # Write headers
    for col_idx, column in enumerate(columns, start=1):
        cell = ws.cell(row=1, column=col_idx)
        # Convert camelCase or snake_case to Title Case
        # e.g., "lastLogin" -> "Last Login", "hire_date" -> "Hire Date"
        import re
        # Insert space before uppercase letters (camelCase) then title case
        header_text = re.sub(r'([a-z])([A-Z])', r'\1 \2', column)
        header_text = header_text.replace('_', ' ').title()
        cell.value = header_text
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = header_alignment

    # Write data rows
    for row_idx, row_data in enumerate(data, start=2):
        for col_idx, column in enumerate(columns, start=1):
            value = row_data.get(column, '')
            ws.cell(row=row_idx, column=col_idx, value=str(value) if value is not None else '')

    # Auto-adjust column widths
    for column in ws.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 50)  # Cap at 50
        ws.column_dimensions[column_letter].width = adjusted_width

    # Save to BytesIO
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output
@app.post("/api/export/{table_key}")
def export_data(
    table_key: str,
    request: schemas.ExportRequest
):
    """
    Export visible table data to Excel with column filtering based on option
    """
    try:
        # Filter columns based on the selected radio option
        filtered_data, columns = filter_columns_by_option(
            request.data,
            request.option,
            table_key
        )

        # Generate Excel file with styling
        excel_file = generate_excel(filtered_data, columns, table_key)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{table_key}_export_{request.option}_{timestamp}.xlsx"

        # Return Excel file for download
        return StreamingResponse(
            excel_file,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")
