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
