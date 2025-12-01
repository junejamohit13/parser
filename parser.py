#crud.py

# Dashboard Version CRUD operations

def get_dashboard_versions(
    db: Session,
    view_type: str,
    user_id: str = 'default'
) -> List[models.DashboardVersion]:
    """Get all dashboard versions for a user and view type"""
    return db.query(models.DashboardVersion).filter(
        models.DashboardVersion.user_id == user_id,
        models.DashboardVersion.view_type == view_type
    ).order_by(models.DashboardVersion.name).all()


def get_dashboard_version(
    db: Session,
    version_id: uuid.UUID
) -> Optional[models.DashboardVersion]:
    """Get a specific dashboard version by ID"""
    return db.query(models.DashboardVersion).filter(
        models.DashboardVersion.id == version_id
    ).first()


def create_dashboard_version(
    db: Session,
    version_data: schemas.DashboardVersionCreate,
    user_id: str = 'default'
) -> models.DashboardVersion:
    """Create a new dashboard version"""
    # Convert columns to list of dicts for JSONB storage
    columns_json = [col.model_dump() for col in version_data.columns]

    version = models.DashboardVersion(
        user_id=user_id,
        view_type=version_data.view_type,
        name=version_data.name,
        columns=columns_json
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    return version


def update_dashboard_version(
    db: Session,
    version_id: uuid.UUID,
    version_data: schemas.DashboardVersionUpdate
) -> Optional[models.DashboardVersion]:
    """Update an existing dashboard version"""
    version = db.query(models.DashboardVersion).filter(
        models.DashboardVersion.id == version_id
    ).first()

    if not version:
        return None

    if version_data.name is not None:
        version.name = version_data.name

    if version_data.columns is not None:
        version.columns = [col.model_dump() for col in version_data.columns]

    db.commit()
    db.refresh(version)
    return version


def delete_dashboard_version(
    db: Session,
    version_id: uuid.UUID
) -> bool:
    """Delete a dashboard version"""
    version = db.query(models.DashboardVersion).filter(
        models.DashboardVersion.id == version_id
    ).first()

    if not version:
        return False

    db.delete(version)
    db.commit()
    return True


#main.py

def generate_zip(files: dict[str, BytesIO]) -> BytesIO:
    """
    Generate a ZIP file containing multiple files
    files: dict mapping filename -> BytesIO content
    """
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for filename, content in files.items():
            content.seek(0)
            zip_file.writestr(filename, content.read())
    zip_buffer.seek(0)
    return zip_buffer


# Dashboard Version API Endpoints

@app.get("/api/versions/{view_type}")
def get_versions(
    view_type: str,
    db: Session = Depends(get_db)
):
    """Get all saved versions for a view type (dashboard or users)"""
    versions = crud.get_dashboard_versions(db, view_type)
    # Convert columns from JSONB to ColumnConfig objects
    result = []
    for v in versions:
        result.append({
            "id": str(v.id),
            "name": v.name,
            "view_type": v.view_type,
            "columns": v.columns,  # Already a list of dicts from JSONB
            "created_at": v.created_at.isoformat(),
            "updated_at": v.updated_at.isoformat()
        })
    return {"versions": result}


@app.post("/api/versions")
def create_version(
    request: schemas.DashboardVersionCreate,
    db: Session = Depends(get_db)
):
    """Create a new saved version"""
    try:
        version = crud.create_dashboard_version(db, request)
        return {
            "id": str(version.id),
            "name": version.name,
            "view_type": version.view_type,
            "columns": version.columns,
            "created_at": version.created_at.isoformat(),
            "updated_at": version.updated_at.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/versions/{version_id}")
def update_version(
    version_id: str,
    request: schemas.DashboardVersionUpdate,
    db: Session = Depends(get_db)
):
    """Update an existing saved version"""
    try:
        from uuid import UUID
        version = crud.update_dashboard_version(db, UUID(version_id), request)
        if not version:
            raise HTTPException(status_code=404, detail="Version not found")
        return {
            "id": str(version.id),
            "name": version.name,
            "view_type": version.view_type,
            "columns": version.columns,
            "created_at": version.created_at.isoformat(),
            "updated_at": version.updated_at.isoformat()
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid version ID")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/versions/{version_id}")
def delete_version(
    version_id: str,
    db: Session = Depends(get_db)
):
    """Delete a saved version"""
    try:
        from uuid import UUID
        success = crud.delete_dashboard_version(db, UUID(version_id))
        if not success:
            raise HTTPException(status_code=404, detail="Version not found")
        return {"success": True}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid version ID")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/export/{table_key}")
def export_data(
    table_key: str,
    request: schemas.ExportRequest
):
    """
    Export data to ZIP containing Excel file(s) with column filtering based on option
    """
    try:
        print(f"[EXPORT] Table: {table_key}, Option: {request.option}")
        print(f"[EXPORT] Received {len(request.data)} rows")
        if request.data:
            print(f"[EXPORT] First row keys: {list(request.data[0].keys())}")

        # Filter columns based on the selected option
        filtered_data, columns = filter_columns_by_option(
            request.data,
            request.option,
            table_key
        )

        print(f"[EXPORT] After column filter: {len(filtered_data)} rows, {len(columns)} columns")
        print(f"[EXPORT] Columns: {columns}")

        # Generate Excel file
        excel_file = generate_excel(filtered_data, columns, table_key)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        excel_filename = f"{table_key}_export_{request.option}_{timestamp}.xlsx"

        # Create ZIP containing the Excel file
        files_to_zip = {
            excel_filename: excel_file
        }
        zip_file = generate_zip(files_to_zip)

        zip_filename = f"{table_key}_export_{request.option}_{timestamp}.zip"

        # Return as streaming response
        return StreamingResponse(
            zip_file,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={zip_filename}"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")
#models.py

class DashboardVersion(Base):
    __tablename__ = "dashboard_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), nullable=False, default='default')
    view_type = Column(String(50), nullable=False)  # 'dashboard' or 'users'
    name = Column(String(100), nullable=False)
    columns = Column(JSONB, nullable=False)  # Array of {id, visible} objects
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

#schemas.py


class ExportRequest(BaseModel):
    option: str  # 'all', 'filtered', 'selected'
    data: List[dict]  # The visible table data from frontend


# Dashboard Version Schemas
class ColumnConfig(BaseModel):
    id: str
    visible: bool


class DashboardVersionCreate(BaseModel):
    name: str
    view_type: str  # 'dashboard' or 'users'
    columns: List[ColumnConfig]


class DashboardVersionUpdate(BaseModel):
    name: Optional[str] = None
    columns: Optional[List[ColumnConfig]] = None


class DashboardVersionResponse(BaseModel):
    id: UUID
    name: str
    view_type: str
    columns: List[ColumnConfig]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DashboardVersionListResponse(BaseModel):
    versions: List[DashboardVersionResponse]

#app.tsx
import React, { useState, useEffect, useMemo, useRef } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  flexRender,
  createColumnHelper,
} from '@tanstack/react-table';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { LayoutDashboard, Users, Settings, Filter, Download, X, Upload, Check, Loader2, Save, ArrowUpDown, Eye, EyeOff, Home, ChevronDown, Plus, Trash2, GripVertical } from 'lucide-react';

// API Configuration
const API_BASE_URL = 'http://localhost:8000/api';

// API Functions
const api = {
  // Fetch available department filter options
  getDepartments: async () => {
    const response = await fetch(`${API_BASE_URL}/departments`);
    if (!response.ok) throw new Error('Failed to fetch departments');
    return await response.json();
  },

  // Fetch available status filter options
  getStatuses: async () => {
    const response = await fetch(`${API_BASE_URL}/statuses`);
    if (!response.ok) throw new Error('Failed to fetch statuses');
    return await response.json();
  },

  dashboard: async (filters = {}) => {
    const params = new URLSearchParams();
    if (filters.departments && filters.departments.length > 0) {
      params.append('departments', filters.departments.join(','));
    }
    if (filters.statuses && filters.statuses.length > 0) {
      params.append('statuses', filters.statuses.join(','));
    }

    const url = `${API_BASE_URL}/dashboard${params.toString() ? '?' + params.toString() : ''}`;
    const response = await fetch(url);
    if (!response.ok) throw new Error('Failed to fetch dashboard data');
    return await response.json();
  },

  users: async (filters = {}) => {
    const params = new URLSearchParams();
    if (filters.departments && filters.departments.length > 0) {
      params.append('departments', filters.departments.join(','));
    }
    if (filters.statuses && filters.statuses.length > 0) {
      params.append('statuses', filters.statuses.join(','));
    }

    const url = `${API_BASE_URL}/users${params.toString() ? '?' + params.toString() : ''}`;
    const response = await fetch(url);
    if (!response.ok) throw new Error('Failed to fetch users data');
    return await response.json();
  },

  saveDashboard: async (data) => {
    const response = await fetch(`${API_BASE_URL}/dashboard/save`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ data })
    });
    if (!response.ok) throw new Error('Failed to save dashboard data');
    return await response.json();
  },

  saveUsers: async (data) => {
    const response = await fetch(`${API_BASE_URL}/users/save`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ data })
    });
    if (!response.ok) throw new Error('Failed to save users data');
    return await response.json();
  },
 //start
  // Version management APIs
  getVersions: async (viewType: string) => {
    const response = await fetch(`${API_BASE_URL}/versions/${viewType}`);
    if (!response.ok) throw new Error('Failed to fetch versions');
    return await response.json();
  },

  createVersion: async (data: { name: string; view_type: string; columns: Array<{ id: string; visible: boolean }> }) => {
    const response = await fetch(`${API_BASE_URL}/versions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!response.ok) throw new Error('Failed to create version');
    return await response.json();
  },

  updateVersion: async (versionId: string, data: { name?: string; columns?: Array<{ id: string; visible: boolean }> }) => {
    const response = await fetch(`${API_BASE_URL}/versions/${versionId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!response.ok) throw new Error('Failed to update version');
    return await response.json();
  },

  deleteVersion: async (versionId: string) => {
    const response = await fetch(`${API_BASE_URL}/versions/${versionId}`, {
      method: 'DELETE'
    });
    if (!response.ok) throw new Error('Failed to delete version');
    return await response.json();
  }
};

// Types for versions
interface ColumnConfig {
  id: string;
  visible: boolean;
}

interface SavedVersion {
  id: string;
  name: string;
  view_type: string;
  columns: ColumnConfig[];
  created_at: string;
  updated_at: string;
}

const DataTable = ({ tableKey, config, onDataChange, onSave }) => {
  const [data, setData] = useState(config?.data || []);
  const modifiedRecordIdsRef = useRef(new Set());
  const [, forceUpdate] = useState({});
  const [columnVisibility, setColumnVisibility] = useState({});
  const [columnFilters, setColumnFilters] = useState([]);
  const [sorting, setSorting] = useState([]);
  const [columnOrder, setColumnOrder] = useState<string[]>([]);//version management
  const [showColumnSelector, setShowColumnSelector] = useState(false);
  const [exportOption, setExportOption] = useState('all');
  const [loading, setLoading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState(null);
  const [dragEnd, setDragEnd] = useState(null);
  const [dragColumn, setDragColumn] = useState(null);
  const [draggedColumn, setDraggedColumn] = useState<string | null>(null);//version
  const [dragOverColumn, setDragOverColumn] = useState<string | null>(null);//version

  // Version management state
  const [savedVersions, setSavedVersions] = useState<SavedVersion[]>([]);
  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(null);
  const [showVersionDropdown, setShowVersionDropdown] = useState(false);
  const [showSaveVersionInput, setShowSaveVersionInput] = useState(false);
  const [newVersionName, setNewVersionName] = useState('');
  const [versionLoading, setVersionLoading] = useState(false);

  // Column panel drag state
  const [panelDraggedColumn, setPanelDraggedColumn] = useState<string | null>(null);
  const [panelDragOverColumn, setPanelDragOverColumn] = useState<string | null>(null);
//end 
  useEffect(() => {
    if (config?.data) {
      setData(config.data);
      modifiedRecordIdsRef.current = new Set(); // Reset modified records when new data loads
      console.log('[RESET] Modified IDs cleared on new data load');
      // Set initial visibility from schema
      const initialVisibility = {};
      config.schema?.columns?.forEach(col => {
        if (col.visible === false) {
          initialVisibility[col.name] = false;
        }
      });
      setColumnVisibility(initialVisibility);
      // Set initial column order from schema //version
      if (config.schema?.columns) {
        setColumnOrder(config.schema.columns.map(col => col.name));
      }
    }//version
  }, [config]);

  // Load saved versions when component mounts or tableKey changes
  useEffect(() => {
    loadVersions();
  }, [tableKey]);

  const loadVersions = async () => {
    try {
      const response = await api.getVersions(tableKey);
      setSavedVersions(response.versions || []);
    } catch (error) {
      console.error('Failed to load versions:', error);
    }
  };

  const getCurrentColumnConfig = (): ColumnConfig[] => {
    // Get current column order and visibility
    const allColumns = table.getAllLeafColumns();
    return allColumns.map(col => ({
      id: col.id,
      visible: col.getIsVisible()
    }));
  };

  const applyVersion = (version: SavedVersion) => {
    // Apply column visibility
    const newVisibility: Record<string, boolean> = {};
    version.columns.forEach(col => {
      newVisibility[col.id] = col.visible;
    });
    setColumnVisibility(newVisibility);

    // Apply column order
    const newOrder = version.columns.map(col => col.id);
    setColumnOrder(newOrder);

    setSelectedVersionId(version.id);
    setShowVersionDropdown(false);
  };

  const handleSaveNewVersion = async () => {
    if (!newVersionName.trim()) return;

    setVersionLoading(true);
    try {
      const columns = getCurrentColumnConfig();
      const newVersion = await api.createVersion({
        name: newVersionName.trim(),
        view_type: tableKey,
        columns
      });
      setSavedVersions(prev => [...prev, newVersion]);
      setSelectedVersionId(newVersion.id);
      setNewVersionName('');
      setShowSaveVersionInput(false);
    } catch (error) {
      console.error('Failed to save version:', error);
      alert('Failed to save version');
    } finally {
      setVersionLoading(false);
    }
  };

  const handleUpdateVersion = async () => {
    if (!selectedVersionId) return;

    setVersionLoading(true);
    try {
      const columns = getCurrentColumnConfig();
      const updatedVersion = await api.updateVersion(selectedVersionId, { columns });
      setSavedVersions(prev =>
        prev.map(v => v.id === selectedVersionId ? updatedVersion : v)
      );
    } catch (error) {
      console.error('Failed to update version:', error);
      alert('Failed to update version');
    } finally {
      setVersionLoading(false);
    }
  };

  const handleDeleteVersion = async (versionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('Are you sure you want to delete this version?')) return;

    setVersionLoading(true);
    try {
      await api.deleteVersion(versionId);
      setSavedVersions(prev => prev.filter(v => v.id !== versionId));
      if (selectedVersionId === versionId) {
        setSelectedVersionId(null);
      }
    } catch (error) {
      console.error('Failed to delete version:', error);
      alert('Failed to delete version');
    } finally {
      setVersionLoading(false);
    }
  };

  const resetToDefault = () => {
    // Reset to schema defaults
    const initialVisibility = {};
    config.schema?.columns?.forEach(col => {
      if (col.visible === false) {
        initialVisibility[col.name] = false;
      }
    });
    setColumnVisibility(initialVisibility);
    setColumnOrder(config.schema?.columns?.map(col => col.name) || []);
    setSelectedVersionId(null);
    setShowVersionDropdown(false);
  };

  const selectedVersion = savedVersions.find(v => v.id === selectedVersionId);

  // Column panel drag handlers
  const handlePanelColumnDragStart = (columnId: string) => {
    setPanelDraggedColumn(columnId);
  };

  const handlePanelColumnDragOver = (e: React.DragEvent, columnId: string) => {
    e.preventDefault();
    if (panelDraggedColumn && panelDraggedColumn !== columnId) {
      setPanelDragOverColumn(columnId);
    }
  };

  const handlePanelColumnDrop = (targetColumnId: string) => {
    if (panelDraggedColumn && panelDraggedColumn !== targetColumnId) {
      const currentOrder = table.getAllLeafColumns().map(col => col.id);
      const draggedIndex = currentOrder.indexOf(panelDraggedColumn);
      const targetIndex = currentOrder.indexOf(targetColumnId);

      const newOrder = [...currentOrder];
      newOrder.splice(draggedIndex, 1);
      newOrder.splice(targetIndex, 0, panelDraggedColumn);

      setColumnOrder(newOrder);
    }
    setPanelDraggedColumn(null);
    setPanelDragOverColumn(null);
  };

  const handlePanelColumnDragEnd = () => {
    setPanelDraggedColumn(null);
    setPanelDragOverColumn(null);
  };

  // Close version dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (showVersionDropdown && !(event.target as Element).closest('.version-dropdown')) {
        setShowVersionDropdown(false);
        setShowSaveVersionInput(false);
        setNewVersionName('');
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showVersionDropdown]);

  useEffect(() => {
    const handleMouseUp = () => {
      if (isDragging) {
        handleDragEnd();
      }
    };

    const handleMouseMove = (e) => {
      if (isDragging) {
        // Find the cell element under the cursor
        const element = document.elementFromPoint(e.clientX, e.clientY);
        if (element) {
          const cell = element.closest('[data-row-id]');
          if (cell) {
            const rowId = cell.getAttribute('data-row-id');
            if (rowId) {
              handleDragOver(rowId);
            }
          }
        }
      }
    };

    document.addEventListener('mouseup', handleMouseUp);
    document.addEventListener('mousemove', handleMouseMove);
    return () => {
      document.removeEventListener('mouseup', handleMouseUp);
      document.removeEventListener('mousemove', handleMouseMove);
    };
  }, [isDragging, dragStart, dragEnd, dragColumn, data]);

  const updateData = (rowIndex, columnId, value) => {
    console.log(`[UPDATE DATA] Row Index: ${rowIndex}, Column: ${columnId}, Value: ${value}`);
    const newData = data.map((row, index) => {
      if (index === rowIndex) {
        console.log(`[ROW DATA]`, row);
        console.log(`[ROW ID]`, row.id, 'Type:', typeof row.id);

        // Mark this record as modified
        modifiedRecordIdsRef.current.add(row.id);
        console.log(`[MODIFIED] Record ID: ${row.id}, Field: ${columnId}, New Value: ${value}`);
        console.log('[MODIFIED SET UPDATED]', Array.from(modifiedRecordIdsRef.current));
        forceUpdate({}); // Force re-render to update Save button
        return { ...row, [columnId]: value };
      }
      return row;
    });
    setData(newData);
    // Don't call onDataChange here - it causes re-render that resets tracking
    // onDataChange(tableKey, newData);
  };

  const handleDragStart = (rowId, columnId, value) => {
    setIsDragging(true);
    setDragStart(rowId);
    setDragEnd(rowId);
    setDragColumn(columnId);
  };

  const handleDragOver = (rowId) => {
    if (isDragging) {
      setDragEnd(rowId);
    }
  };

  const handleDragEnd = () => {
    if (isDragging && dragStart !== null && dragEnd !== null && dragColumn) {
      // Get the filtered rows from the table
      const visibleRows = table.getRowModel().rows;

      // Find the indices in the visible rows
      const startIndex = visibleRows.findIndex(r => r.id === dragStart);
      const endIndex = visibleRows.findIndex(r => r.id === dragEnd);

      if (startIndex === -1 || endIndex === -1) {
        setIsDragging(false);
        setDragStart(null);
        setDragEnd(null);
        setDragColumn(null);
        return;
      }

      const minIndex = Math.min(startIndex, endIndex);
      const maxIndex = Math.max(startIndex, endIndex);

      // Get the fill value from the starting row's original data
      const startRowData = visibleRows[startIndex].original;
      const fillValue = startRowData[dragColumn];

      // Get the IDs of all rows in the drag range
      const rowsToUpdate = visibleRows.slice(minIndex, maxIndex + 1);

      // Update only the rows in the visible range
      const newData = data.map((row) => {
        const shouldUpdate = rowsToUpdate.some(r => r.original === row);
        if (shouldUpdate && row !== startRowData) {
          // Mark this record as modified
          modifiedRecordIdsRef.current.add(row.id);
          console.log('[DRAG MODIFIED]', row.id);
          return { ...row, [dragColumn]: fillValue };
        }
        return row;
      });

      console.log('[DRAG] Total modified IDs:', Array.from(modifiedRecordIdsRef.current));
      setData(newData);
      // Don't call onDataChange here - it causes re-render that resets tracking
      // onDataChange(tableKey, newData);
      forceUpdate({}); // Force re-render to update Save button
    }

    setIsDragging(false);
    setDragStart(null);
    setDragEnd(null);
    setDragColumn(null);
  };

  const columns = useMemo(() => {
    if (!config?.schema) return [];

    return config.schema.columns.map(col => {
      const columnDef = {
        accessorKey: col.name,
        header: ({ column }) => (
          <div className="flex items-center gap-2">
            <span className="font-semibold text-xs uppercase tracking-wider text-gray-500">{col.label}</span>
            {col.editable && (
              <Button
                variant="ghost"
                size="sm"
                className="h-6 w-6 p-0 hover:bg-gray-100"
                onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
              >
                <ArrowUpDown className="h-3 w-3 text-gray-400" />
              </Button>
            )}
          </div>
        ),
        cell: ({ row, column }) => {
          const value = row.getValue(column.id);
          const rowId = row.id;

          // Check if this row is in the drag range
          const visibleRows = table.getRowModel().rows;
          const startIndex = visibleRows.findIndex(r => r.id === dragStart);
          const endIndex = visibleRows.findIndex(r => r.id === dragEnd);
          const currentIndex = visibleRows.findIndex(r => r.id === rowId);

          const isInDragRange = isDragging &&
            dragColumn === column.id &&
            startIndex !== -1 &&
            endIndex !== -1 &&
            currentIndex !== -1 &&
            currentIndex >= Math.min(startIndex, endIndex) &&
            currentIndex <= Math.max(startIndex, endIndex);

          if (!col.editable) {
            return <div className="px-2 py-1">{value}</div>;
          }

          if (col.type === 'select') {
            return (
              <div className={`relative group ${isInDragRange ? 'bg-blue-100' : ''}`}>
                <Select
                  value={value}
                  onValueChange={(newValue) => updateData(row.index, column.id, newValue)}
                >
                  <SelectTrigger className="border-0 focus:ring-1 h-8">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-white">
                    {col.options?.map(option => (
                      <SelectItem key={option} value={option}>{option}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <div
                  className="absolute bottom-0 right-0 w-3 h-3 bg-blue-600 cursor-ns-resize opacity-0 group-hover:opacity-100 transition-opacity z-10"
                  onMouseDown={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    handleDragStart(rowId, column.id, value);
                  }}
                  style={{ borderRadius: '0 0 3px 0' }}
                  title="Drag to fill down"
                />
              </div>
            );
          }

          return (
            <div className={`relative group ${isInDragRange ? 'bg-blue-100' : ''}`}>
              <Input
                value={value}
                onChange={(e) => updateData(row.index, column.id, e.target.value)}
                className="border-0 focus-visible:ring-1 h-8"
              />
              <div
                className="absolute bottom-0 right-0 w-3 h-3 bg-blue-600 cursor-ns-resize opacity-0 group-hover:opacity-100 transition-opacity z-10"
                onMouseDown={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  handleDragStart(rowId, column.id, value);
                }}
                style={{ borderRadius: '0 0 3px 0' }}
                title="Drag to fill down"
              />
            </div>
          );
        },
        filterFn: 'includesString',
      };

      return columnDef;
    });
  }, [config, data]);

  const table = useReactTable({
    data,
    columns,
    state: {
      columnVisibility,
      columnFilters,
      sorting,
      columnOrder,
    },
    onColumnVisibilityChange: setColumnVisibility,
    onColumnFiltersChange: setColumnFilters,
    onSortingChange: setSorting,
    onColumnOrderChange: setColumnOrder,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

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

  // Column drag and drop handlers
  const handleColumnDragStart = (columnId: string) => {
    setDraggedColumn(columnId);
  };

  const handleColumnDragOver = (e: React.DragEvent, columnId: string) => {
    e.preventDefault();
    if (draggedColumn && draggedColumn !== columnId) {
      setDragOverColumn(columnId);
    }
  };

  const handleColumnDrop = (targetColumnId: string) => {
    if (draggedColumn && draggedColumn !== targetColumnId) {
      const currentOrder = table.getAllLeafColumns().map(col => col.id);
      const draggedIndex = currentOrder.indexOf(draggedColumn);
      const targetIndex = currentOrder.indexOf(targetColumnId);

      const newOrder = [...currentOrder];
      newOrder.splice(draggedIndex, 1);
      newOrder.splice(targetIndex, 0, draggedColumn);

      setColumnOrder(newOrder);
    }
    setDraggedColumn(null);
    setDragOverColumn(null);
  };

  const handleColumnDragEnd = () => {
    setDraggedColumn(null);
    setDragOverColumn(null);
  };

  const visibleCount = table.getAllLeafColumns().filter(col => col.getIsVisible()).length;
  const totalCount = table.getAllLeafColumns().length;

  if (!config?.schema) {
    return (
      <div className="border rounded-lg bg-white p-8 text-center">
        <p className="text-gray-500">No data loaded. Click "Load Data" to fetch from API.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Version Selector Row */}
      <div className="flex items-center gap-3 bg-white p-3 rounded-lg border border-gray-200 shadow-sm">
        <span className="text-sm font-medium text-gray-700">View:</span>
        <div className="relative version-dropdown">
          <button
            onClick={() => setShowVersionDropdown(!showVersionDropdown)}
            className="flex items-center gap-2 px-3 py-1.5 border border-gray-300 rounded-md text-sm hover:bg-gray-50 min-w-[160px]"
          >
            <span className="flex-1 text-left truncate">
              {selectedVersion ? selectedVersion.name : 'Default View'}
            </span>
            <ChevronDown className="h-4 w-4 text-gray-500 flex-shrink-0" />
          </button>

          {showVersionDropdown && (
            <div className="absolute left-0 top-full mt-1 bg-white border border-gray-200 rounded-lg shadow-xl z-20 min-w-[220px] py-1">
              {/* Default View option */}
              <button
                onClick={() => resetToDefault()}
                className={`w-full flex items-center justify-between px-3 py-2 text-sm hover:bg-gray-50 ${!selectedVersionId ? 'bg-blue-50 text-blue-700' : 'text-gray-700'}`}
              >
                <span>Default View</span>
                {!selectedVersionId && <Check className="h-4 w-4" />}
              </button>

              {savedVersions.length > 0 && (
                <div className="border-t border-gray-100 my-1" />
              )}

              {/* Saved versions */}
              {savedVersions.map(version => (
                <button
                  key={version.id}
                  onClick={() => applyVersion(version)}
                  className={`w-full flex items-center justify-between px-3 py-2 text-sm hover:bg-gray-50 group ${selectedVersionId === version.id ? 'bg-blue-50 text-blue-700' : 'text-gray-700'}`}
                >
                  <span className="truncate flex-1 text-left">{version.name}</span>
                  <div className="flex items-center gap-1">
                    {selectedVersionId === version.id && <Check className="h-4 w-4" />}
                    <button
                      onClick={(e) => handleDeleteVersion(version.id, e)}
                      className="p-1 hover:bg-red-100 rounded opacity-0 group-hover:opacity-100 transition-opacity"
                      title="Delete version"
                    >
                      <Trash2 className="h-3 w-3 text-red-500" />
                    </button>
                  </div>
                </button>
              ))}

              <div className="border-t border-gray-100 my-1" />

              {/* Save new version */}
              {showSaveVersionInput ? (
                <div className="px-3 py-2">
                  <div className="flex gap-2">
                    <Input
                      value={newVersionName}
                      onChange={(e) => setNewVersionName(e.target.value)}
                      placeholder="Version name..."
                      className="h-8 text-sm"
                      autoFocus
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') handleSaveNewVersion();
                        if (e.key === 'Escape') {
                          setShowSaveVersionInput(false);
                          setNewVersionName('');
                        }
                      }}
                    />
                    <Button
                      size="sm"
                      onClick={handleSaveNewVersion}
                      disabled={!newVersionName.trim() || versionLoading}
                      className="h-8 px-2"
                    >
                      {versionLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
                    </Button>
                  </div>
                </div>
              ) : (
                <button
                  onClick={() => setShowSaveVersionInput(true)}
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm text-blue-600 hover:bg-blue-50"
                >
                  <Plus className="h-4 w-4" />
                  Save current as new...
                </button>
              )}
            </div>
          )}
        </div>

        {/* Update current version button */}
        {selectedVersionId && (
          <Button
            variant="outline"
            size="sm"
            onClick={handleUpdateVersion}
            disabled={versionLoading}
            className="gap-1 text-xs"
          >
            {versionLoading ? <Loader2 className="h-3 w-3 animate-spin" /> : <Save className="h-3 w-3" />}
            Update
          </Button>
        )}
      </div>

      {/* Controls */}
      <div className="flex items-center justify-between bg-white p-4 rounded-lg border border-gray-200 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="bg-blue-50 p-2 rounded-full">
            <Filter className="h-4 w-4 text-blue-600" />
          </div>
          <div>
            <h3 className="text-sm font-medium text-gray-900">Filters</h3>
            <p className="text-xs text-gray-500">Use the column headers to filter data</p>
          </div>
        </div>
        <div className="flex gap-3 items-center">
          <div className="relative">
            <Button
              onClick={() => setShowColumnSelector(!showColumnSelector)}
              variant="outline"
              className="gap-2 border-gray-200 text-gray-700 hover:bg-gray-50 hover:text-gray-900"
            >
              <Eye className="h-4 w-4 text-gray-500" />
              Columns <span className="bg-gray-100 px-1.5 py-0.5 rounded-full text-xs font-medium text-gray-600">{visibleCount}/{totalCount}</span>
            </Button>

            {showColumnSelector && (
              <div className="absolute right-0 top-full mt-2 bg-white border border-gray-200 rounded-lg shadow-xl p-4 z-20 min-w-[300px] animate-in fade-in zoom-in-95 duration-200">
                <div className="flex items-center justify-between mb-3 pb-3 border-b border-gray-100">
                  <div>
                    <span className="font-semibold text-sm">Manage Columns</span>
                    <p className="text-[10px] text-gray-400 mt-0.5">Drag to reorder, check to show/hide</p>
                  </div>
                  <button onClick={() => setShowColumnSelector(false)} className="text-gray-400 hover:text-gray-600">
                    <X className="h-4 w-4" />
                  </button>
                </div>
                <div className="space-y-0.5 max-h-[400px] overflow-y-auto custom-scrollbar">
                  {table.getAllLeafColumns().map(column => {
                    const colConfig = config.schema.columns.find(c => c.name === column.id);
                    const isDragging = panelDraggedColumn === column.id;
                    const isDropTarget = panelDragOverColumn === column.id;
                    return (
                      <div
                        key={column.id}
                        draggable
                        onDragStart={() => handlePanelColumnDragStart(column.id)}
                        onDragOver={(e) => handlePanelColumnDragOver(e, column.id)}
                        onDrop={() => handlePanelColumnDrop(column.id)}
                        onDragEnd={handlePanelColumnDragEnd}
                        className={`flex items-center gap-2 p-2 rounded-md transition-all cursor-move ${
                          isDragging ? 'opacity-50 bg-blue-50' : 'hover:bg-gray-50'
                        } ${isDropTarget ? 'border-t-2 border-blue-500' : ''}`}
                      >
                        <GripVertical className="h-4 w-4 text-gray-300 flex-shrink-0" />
                        <label className="flex items-center gap-2 flex-1 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={column.getIsVisible()}
                            onChange={column.getToggleVisibilityHandler()}
                            className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                            onClick={(e) => e.stopPropagation()}
                          />
                          <span className={`text-sm flex-1 ${column.getIsVisible() ? 'text-gray-700' : 'text-gray-400'}`}>
                            {colConfig?.label || column.id}
                          </span>
                        </label>
                        {!column.getIsVisible() && (
                          <EyeOff className="h-3 w-3 text-gray-300 flex-shrink-0" />
                        )}
                      </div>
                    );
                  })}
                </div>
                <div className="mt-3 pt-3 border-t border-gray-100 flex justify-between items-center">
                  <span className="text-xs text-gray-500">{visibleCount} visible</span>
                  <Button size="sm" variant="ghost" className="h-7 text-xs" onClick={() => setShowColumnSelector(false)}>Done</Button>
                </div>
              </div>
            )}
          </div>
          <Button
            onClick={() => {
              const modifiedRecords = data.filter(record => modifiedRecordIdsRef.current.has(record.id));
              const recordsToSave = modifiedRecords.length > 0 ? modifiedRecords : data;
              onSave(tableKey, recordsToSave);
              modifiedRecordIdsRef.current = new Set();
              forceUpdate({});
            }}
            className={`gap-2 text-white transition-all ${modifiedRecordIdsRef.current.size > 0 ? 'bg-blue-600 hover:bg-blue-700 shadow-md shadow-blue-200' : 'bg-gray-900 hover:bg-gray-800'}`}
          >
            <Save className="h-4 w-4" />
            Save Changes {modifiedRecordIdsRef.current.size > 0 && <span className="bg-white/20 px-1.5 py-0.5 rounded text-xs font-medium">{modifiedRecordIdsRef.current.size}</span>}
          </Button>
        </div>
      </div>

      {/* Table */}
      <div className="border border-gray-200 rounded-lg bg-white shadow-sm overflow-hidden">
        <div className="overflow-x-auto overflow-y-auto max-h-[600px]">
          <table className="w-full text-sm text-left">
            <thead className="bg-gray-50/50 border-b border-gray-200 sticky top-0 z-10 backdrop-blur-sm">
              {table.getHeaderGroups().map(headerGroup => (
                <React.Fragment key={headerGroup.id}>
                  <tr>
                    {headerGroup.headers.map(header => {
                      const isDragging = draggedColumn === header.column.id;
                      const isDropTarget = dragOverColumn === header.column.id;
                      return (
                        <th
                          key={header.id}
                          draggable
                          onDragStart={() => handleColumnDragStart(header.column.id)}
                          onDragOver={(e) => handleColumnDragOver(e, header.column.id)}
                          onDrop={() => handleColumnDrop(header.column.id)}
                          onDragEnd={handleColumnDragEnd}
                          className={`px-4 py-3 font-medium text-gray-500 bg-gray-50/80 min-w-[150px] whitespace-nowrap border-b border-gray-100 cursor-move transition-all ${
                            isDragging ? 'opacity-50 bg-blue-100' : ''
                          } ${isDropTarget ? 'border-l-4 border-l-blue-500' : ''}`}
                        >
                          {flexRender(header.column.columnDef.header, header.getContext())}
                        </th>
                      );
                    })}
                  </tr>
                  <tr>
                    {headerGroup.headers.map(header => {
                      const colConfig = config.schema.columns.find(c => c.name === header.column.id);
                      return (
                        <th key={header.id} className="px-4 py-2 bg-gray-50">
                          {colConfig?.editable && colConfig.type === 'select' ? (
                            <Select
                              value={(header.column.getFilterValue() ?? '__all__') as string}
                              onValueChange={(value) => header.column.setFilterValue(value === '__all__' ? undefined : value)}
                            >
                              <SelectTrigger className="h-8 text-xs">
                                <SelectValue placeholder="All" />
                              </SelectTrigger>
                              <SelectContent className="bg-white">
                                <SelectItem value="__all__">All</SelectItem>
                                {colConfig.options?.map(option => (
                                  <SelectItem key={option} value={option}>{option}</SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          ) : colConfig?.editable ? (
                            <Input
                              placeholder="Filter..."
                              value={(header.column.getFilterValue() ?? '') as string}
                              onChange={(e) => header.column.setFilterValue(e.target.value)}
                              className="h-8 text-xs"
                            />
                          ) : null}
                        </th>
                      );
                    })}
                  </tr>
                </React.Fragment>
              ))}
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {table.getRowModel().rows.map(row => (
                <tr key={row.id} className="hover:bg-gray-50/80 transition-colors group">
                  {row.getVisibleCells().map(cell => (
                    <td key={cell.id} className="px-4 py-2.5 border-r border-transparent group-hover:border-gray-100 last:border-r-0" data-row-id={row.id}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Export Section for Users Table */}
      {tableKey === 'users' && (
        <div className="border rounded-lg bg-white p-6">
          <h4 className="text-base font-semibold mb-4">Export Options</h4>
          <div className="space-y-4">
            <div className="space-y-3">
              {['all', 'filtered', 'selected'].map(option => (
                <label key={option} className="flex items-center gap-3 cursor-pointer p-3 border rounded-lg hover:bg-gray-50">
                  <input
                    type="radio"
                    name="exportOption"
                    value={option}
                    checked={exportOption === option}
                    onChange={(e) => setExportOption(e.target.value)}
                    className="w-4 h-4"
                  />
                  <div>
                    <span className="text-sm font-medium">Export {option.charAt(0).toUpperCase() + option.slice(1)} Data</span>
                    <p className="text-xs text-gray-500">
                      {option === 'all' && `Download all ${data.length} records`}
                      {option === 'filtered' && `Download ${table.getRowModel().rows.length} filtered records`}
                      {option === 'selected' && 'Choose specific columns to export'}
                    </p>
                  </div>
                </label>
              ))}
            </div>
            <Button onClick={handleExport} className="w-full gap-2 h-12" disabled={loading}>
              {loading ? (
                <>
                  <Loader2 className="h-5 w-5 animate-spin" />
                  Exporting...
                </>
              ) : (
                <>
                  <Download className="h-5 w-5" />
                  Export to Excel
                </>
              )}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
};

const App = () => {
  const [activeScreen, setActiveScreen] = useState('home');
  const [loading, setLoading] = useState(false);
  const [tableConfig, setTableConfig] = useState({
    dashboard: { schema: null, data: [] },
    users: { schema: null, data: [] }
  });
  const [availableDepartments, setAvailableDepartments] = useState([]);
  const [selectedDepartments, setSelectedDepartments] = useState([]);
  const [showDepartmentDropdown, setShowDepartmentDropdown] = useState(false);
  const [availableStatuses, setAvailableStatuses] = useState([]);
  const [selectedStatuses, setSelectedStatuses] = useState([]);
  const [showStatusDropdown, setShowStatusDropdown] = useState(false);

  const menuItems = [
    { id: 'home', label: 'Home', icon: Home },
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'users', label: 'Users', icon: Users }
  ];

  const loadDepartments = async () => {
    try {
      const response = await api.getDepartments();
      setAvailableDepartments(response.departments);
    } catch (error) {
      console.error('Error loading departments:', error);
      alert('Failed to load departments. Make sure the backend is running.');
    }
  };

  const loadStatuses = async () => {
    try {
      const response = await api.getStatuses();
      setAvailableStatuses(response.statuses);
    } catch (error) {
      console.error('Error loading statuses:', error);
      alert('Failed to load statuses. Make sure the backend is running.');
    }
  };

  const loadDataFromAPI = async () => {
    setLoading(true);
    const newConfig = { ...tableConfig };

    try {
      const filters = {
        departments: selectedDepartments,
        statuses: selectedStatuses
      };

      // Always load both dashboard and users data
      const dashboardResponse = await api.dashboard(filters);
      const usersResponse = await api.users(filters);

      newConfig['dashboard'] = dashboardResponse;
      newConfig['users'] = usersResponse;

      setTableConfig(newConfig);

      // Build filter info message
      const filterParts = [];
      if (selectedDepartments.length > 0) {
        filterParts.push(`Departments: ${selectedDepartments.join(', ')}`);
      }
      if (selectedStatuses.length > 0) {
        filterParts.push(`Status: ${selectedStatuses.join(', ')}`);
      }
      const filterInfo = filterParts.length > 0 ? ` (${filterParts.join(' | ')})` : '';

      alert(`Successfully loaded data${filterInfo}`);
    } catch (error) {
      console.error('Error loading data:', error);
      alert('Error loading data from API. Make sure the backend is running.');
    } finally {
      setLoading(false);
    }
  };

  const handleDataChange = (tableKey, newData) => {
    setTableConfig(prev => ({
      ...prev,
      [tableKey]: {
        ...prev[tableKey],
        data: newData
      }
    }));
  };

  const handleSave = async (tableKey, modifiedRecords) => {
    setLoading(true);
    console.log('=== HANDLE SAVE ===');
    console.log('Table:', tableKey);
    console.log('Records to save:', modifiedRecords);
    console.log('Count:', modifiedRecords?.length || 0);

    try {
      if (!modifiedRecords || modifiedRecords.length === 0) {
        console.log('No records to save');
        alert('No changes to save');
        setLoading(false);
        return;
      }

      console.log('Calling API to save records...');
      let response;
      if (tableKey === 'dashboard') {
        response = await api.saveDashboard(modifiedRecords);
      } else if (tableKey === 'users') {
        response = await api.saveUsers(modifiedRecords);
      }

      console.log('API Response:', response);
      if (response && response.success) {
        alert(`Data saved successfully!\nTransaction ID: ${response.transaction_id}\nRecords updated: ${response.records_updated}`);
        console.log('✅ Save successful!');
      }
    } catch (error) {
      console.error('❌ Save error:', error);
      alert('Failed to save data. Make sure the backend is running.');
    } finally {
      setLoading(false);
    }
  };

  const toggleDepartment = (department) => {
    setSelectedDepartments(prev =>
      prev.includes(department) ? prev.filter(d => d !== department) : [...prev, department]
    );
  };

  const toggleStatus = (status) => {
    setSelectedStatuses(prev =>
      prev.includes(status) ? prev.filter(s => s !== status) : [...prev, status]
    );
  };

  // Load filter options on app start
  useEffect(() => {
    loadDepartments();
    loadStatuses();
  }, []);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (showDepartmentDropdown && !event.target.closest('.department-dropdown')) {
        setShowDepartmentDropdown(false);
      }
      if (showStatusDropdown && !event.target.closest('.status-dropdown')) {
        setShowStatusDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showDepartmentDropdown, showStatusDropdown]);

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <div className="w-64 bg-white border-r border-gray-200 flex flex-col">
        <div className="p-6 border-b border-gray-200">
          <h1 className="text-xl font-bold text-gray-900">Data Manager</h1>
        </div>

        <nav className="flex-1 p-4 space-y-1">
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeScreen === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveScreen(item.id)}
                className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-md transition-all duration-200 font-medium text-sm ${isActive
                  ? 'bg-blue-50 text-blue-700 shadow-sm border border-blue-100'
                  : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                  }`}
              >
                <Icon className={`h-4 w-4 ${isActive ? 'text-blue-600' : 'text-gray-400'}`} />
                {item.label}
              </button>
            );
          })}
        </nav>

        <div className="p-4 border-t border-gray-200 space-y-3">
          {/* Department Filter */}
          <div>
            <label className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-2 block">
              Department Filter
            </label>
            <div className="relative department-dropdown">
              <button
                onClick={() => setShowDepartmentDropdown(!showDepartmentDropdown)}
                className="w-full flex items-center justify-between px-4 py-2 border border-gray-300 rounded-lg text-sm hover:bg-gray-50"
              >
                <span className="text-gray-700">
                  {selectedDepartments.length > 0
                    ? `${selectedDepartments.length} dept(s) selected`
                    : 'All departments'}
                </span>
                <Filter className="h-4 w-4 text-gray-500" />
              </button>

              {showDepartmentDropdown && (
                <div className="absolute bottom-full left-0 right-0 mb-2 bg-white border border-gray-200 rounded-lg shadow-lg p-2 z-10 max-h-60 overflow-y-auto">
                  <div className="mb-2 px-3 py-2 border-b">
                    <button
                      onClick={() => setSelectedDepartments([])}
                      className="text-xs text-blue-600 hover:text-blue-800 font-medium"
                    >
                      Clear All
                    </button>
                  </div>
                  {availableDepartments.map((dept) => (
                    <button
                      key={dept}
                      onClick={() => toggleDepartment(dept)}
                      className="w-full flex items-center justify-between px-3 py-2 text-sm hover:bg-gray-50 rounded"
                    >
                      <span className="text-gray-700">{dept}</span>
                      {selectedDepartments.includes(dept) && (
                        <Check className="h-4 w-4 text-blue-600" />
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Status Filter */}
          <div>
            <label className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-2 block">
              Status Filter
            </label>
            <div className="relative status-dropdown">
              <button
                onClick={() => setShowStatusDropdown(!showStatusDropdown)}
                className="w-full flex items-center justify-between px-4 py-2 border border-gray-300 rounded-lg text-sm hover:bg-gray-50"
              >
                <span className="text-gray-700">
                  {selectedStatuses.length > 0
                    ? `${selectedStatuses.length} status(es) selected`
                    : 'All statuses'}
                </span>
                <Filter className="h-4 w-4 text-gray-500" />
              </button>

              {showStatusDropdown && (
                <div className="absolute bottom-full left-0 right-0 mb-2 bg-white border border-gray-200 rounded-lg shadow-lg p-2 z-10 max-h-60 overflow-y-auto">
                  <div className="mb-2 px-3 py-2 border-b">
                    <button
                      onClick={() => setSelectedStatuses([])}
                      className="text-xs text-blue-600 hover:text-blue-800 font-medium"
                    >
                      Clear All
                    </button>
                  </div>
                  {availableStatuses.map((status) => (
                    <button
                      key={status}
                      onClick={() => toggleStatus(status)}
                      className="w-full flex items-center justify-between px-3 py-2 text-sm hover:bg-gray-50 rounded"
                    >
                      <span className="text-gray-700">{status}</span>
                      {selectedStatuses.includes(status) && (
                        <Check className="h-4 w-4 text-blue-600" />
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          <Button
            onClick={() => loadDataFromAPI()}
            disabled={loading}
            className="w-full gap-2"
          >
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Loading...
              </>
            ) : (
              <>
                <Upload className="h-4 w-4" />
                Load Data
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-auto">
        <div className="p-8">
          <div className="mb-6">
            <h2 className="text-2xl font-bold text-gray-900">
              {activeScreen === 'home' && 'Home'}
              {activeScreen === 'dashboard' && 'Dashboard'}
              {activeScreen === 'users' && 'Users Management'}
            </h2>
            <p className="text-gray-500 mt-1">
              {activeScreen === 'home' && 'Welcome to Data Manager - Your central hub for managing data'}
              {activeScreen === 'dashboard' && 'Powered by TanStack Table - Column visibility, filtering, sorting'}
              {activeScreen === 'users' && 'Advanced table features with export capabilities'}
            </p>
          </div>

          {loading && (
            <div className="flex items-center justify-center p-12">
              <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
              <span className="ml-3 text-gray-600">Loading data from API...</span>
            </div>
          )}

          {!loading && activeScreen === 'dashboard' && (
            <DataTable
              tableKey="dashboard"
              config={tableConfig.dashboard}
              onDataChange={handleDataChange}
              onSave={handleSave}
            />
          )}

          {!loading && activeScreen === 'users' && (
            <DataTable
              tableKey="users"
              config={tableConfig.users}
              onDataChange={handleDataChange}
              onSave={handleSave}
            />
          )}

          {!loading && activeScreen === 'home' && (
            <div className="border rounded-lg bg-white p-8">
              <h1>Welcome to Data Manager</h1>
              <p>This is your central hub for managing data.</p>

              <h2>Features</h2>
              <ul>
                <li>Dashboard Analytics</li>
                <li>User Management</li>
                <li>Data Export</li>
              </ul>

              <h3>Getting Started</h3>
              <ol>
                <li>Load your data using the sidebar</li>
                <li>Customize your view with filters</li>
                <li>Edit and export your results</li>
              </ol>

              <p><strong>Quick Stats:</strong> 40 dashboard records, 35 user accounts</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
export default App;


#index.css
@import "tailwindcss";

@layer base {
  :root {
    font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    line-height: 1.5;
    font-weight: 400;

    /* Professional Slate Theme */
    --background: 0 0% 100%;
    --foreground: 222.2 84% 4.9%;
    
    --card: 0 0% 100%;
    --card-foreground: 222.2 84% 4.9%;
    
    --popover: 0 0% 100%;
    --popover-foreground: 222.2 84% 4.9%;
    
    /* Indigo Primary */
    --primary: 226 70% 55.5%;
    --primary-foreground: 210 40% 98%;
    
    --secondary: 210 40% 96.1%;
    --secondary-foreground: 222.2 47.4% 11.2%;
    
    --muted: 210 40% 96.1%;
    --muted-foreground: 215.4 16.3% 46.9%;
    
    --accent: 210 40% 96.1%;
    --accent-foreground: 222.2 47.4% 11.2%;
    
    --destructive: 0 84.2% 60.2%;
    --destructive-foreground: 210 40% 98%;
    
    --border: 214.3 31.8% 91.4%;
    --input: 214.3 31.8% 91.4%;
    --ring: 226 70% 55.5%;
    
    --radius: 0.5rem;
  }

  body {
    margin: 0;
    min-height: 100vh;
    background-color: #f8fafc; /* Slate-50 */
    color: hsl(var(--foreground));
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
  }
}

@layer utilities {
  .glass-panel {
    @apply bg-white/80 backdrop-blur-sm border border-white/20 shadow-sm;
  }
}


#select.tsx
import * as React from "react"
import * as SelectPrimitive from "@radix-ui/react-select"
import { CheckIcon, ChevronDownIcon, ChevronUpIcon } from "lucide-react"

import { cn } from "@/lib/utils"

function Select({
  ...props
}: React.ComponentProps<typeof SelectPrimitive.Root>) {
  return <SelectPrimitive.Root data-slot="select" {...props} />
}

function SelectGroup({
  ...props
}: React.ComponentProps<typeof SelectPrimitive.Group>) {
  return <SelectPrimitive.Group data-slot="select-group" {...props} />
}

function SelectValue({
  ...props
}: React.ComponentProps<typeof SelectPrimitive.Value>) {
  return <SelectPrimitive.Value data-slot="select-value" {...props} />
}

function SelectTrigger({
  className,
  size = "default",
  children,
  ...props
}: React.ComponentProps<typeof SelectPrimitive.Trigger> & {
  size?: "sm" | "default"
}) {
  return (
    <SelectPrimitive.Trigger
      data-slot="select-trigger"
      data-size={size}
      className={cn(
        "border-input data-[placeholder]:text-muted-foreground [&_svg:not([class*='text-'])]:text-muted-foreground focus-visible:border-ring focus-visible:ring-ring/50 aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive dark:bg-input/30 dark:hover:bg-input/50 flex w-full items-center justify-between gap-2 rounded-md border bg-transparent px-3 py-2 text-sm whitespace-nowrap shadow-xs transition-[color,box-shadow] outline-none focus-visible:ring-[3px] disabled:cursor-not-allowed disabled:opacity-50 data-[size=default]:h-9 data-[size=sm]:h-8 *:data-[slot=select-value]:line-clamp-1 *:data-[slot=select-value]:flex *:data-[slot=select-value]:items-center *:data-[slot=select-value]:gap-2 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
        className
      )}
      {...props}
    >
      {children}
      <SelectPrimitive.Icon asChild>
        <ChevronDownIcon className="size-4 opacity-50" />
      </SelectPrimitive.Icon>
    </SelectPrimitive.Trigger>
  )
}

function SelectContent({
  className,
  children,
  position = "popper",
  align = "center",
  ...props
}: React.ComponentProps<typeof SelectPrimitive.Content>) {
  return (
    <SelectPrimitive.Portal>
      <SelectPrimitive.Content
        data-slot="select-content"
        className={cn(
          "bg-white text-gray-900 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2 data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2 relative z-50 max-h-(--radix-select-content-available-height) min-w-[8rem] origin-(--radix-select-content-transform-origin) overflow-x-hidden overflow-y-auto rounded-md border border-gray-200 shadow-lg",
          position === "popper" &&
            "data-[side=bottom]:translate-y-1 data-[side=left]:-translate-x-1 data-[side=right]:translate-x-1 data-[side=top]:-translate-y-1",
          className
        )}
        position={position}
        align={align}
        {...props}
      >
        <SelectScrollUpButton />
        <SelectPrimitive.Viewport
          className={cn(
            "p-1 bg-white",
            position === "popper" &&
              "h-[var(--radix-select-trigger-height)] w-full min-w-[var(--radix-select-trigger-width)] scroll-my-1"
          )}
        >
          {children}
        </SelectPrimitive.Viewport>
        <SelectScrollDownButton />
      </SelectPrimitive.Content>
    </SelectPrimitive.Portal>
  )
}

function SelectLabel({
  className,
  ...props
}: React.ComponentProps<typeof SelectPrimitive.Label>) {
  return (
    <SelectPrimitive.Label
      data-slot="select-label"
      className={cn("text-muted-foreground px-2 py-1.5 text-xs", className)}
      {...props}
    />
  )
}

function SelectItem({
  className,
  children,
  ...props
}: React.ComponentProps<typeof SelectPrimitive.Item>) {
  return (
    <SelectPrimitive.Item
      data-slot="select-item"
      className={cn(
        "focus:bg-accent focus:text-accent-foreground [&_svg:not([class*='text-'])]:text-muted-foreground relative flex w-full cursor-default items-center gap-2 rounded-sm py-1.5 pr-8 pl-2 text-sm outline-hidden select-none data-[disabled]:pointer-events-none data-[disabled]:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4 *:[span]:last:flex *:[span]:last:items-center *:[span]:last:gap-2 bg-white hover:bg-gray-100",
        className
      )}
      {...props}
    >
      <span className="absolute right-2 flex size-3.5 items-center justify-center">
        <SelectPrimitive.ItemIndicator>
          <CheckIcon className="size-4" />
        </SelectPrimitive.ItemIndicator>
      </span>
      <SelectPrimitive.ItemText>{children}</SelectPrimitive.ItemText>
    </SelectPrimitive.Item>
  )
}

function SelectSeparator({
  className,
  ...props
}: React.ComponentProps<typeof SelectPrimitive.Separator>) {
  return (
    <SelectPrimitive.Separator
      data-slot="select-separator"
      className={cn("bg-border pointer-events-none -mx-1 my-1 h-px", className)}
      {...props}
    />
  )
}

function SelectScrollUpButton({
  className,
  ...props
}: React.ComponentProps<typeof SelectPrimitive.ScrollUpButton>) {
  return (
    <SelectPrimitive.ScrollUpButton
      data-slot="select-scroll-up-button"
      className={cn(
        "flex cursor-default items-center justify-center py-1",
        className
      )}
      {...props}
    >
      <ChevronUpIcon className="size-4" />
    </SelectPrimitive.ScrollUpButton>
  )
}

function SelectScrollDownButton({
  className,
  ...props
}: React.ComponentProps<typeof SelectPrimitive.ScrollDownButton>) {
  return (
    <SelectPrimitive.ScrollDownButton
      data-slot="select-scroll-down-button"
      className={cn(
        "flex cursor-default items-center justify-center py-1",
        className
      )}
      {...props}
    >
      <ChevronDownIcon className="size-4" />
    </SelectPrimitive.ScrollDownButton>
  )
}

export {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectScrollDownButton,
  SelectScrollUpButton,
  SelectSeparator,
  SelectTrigger,
  SelectValue,
}

