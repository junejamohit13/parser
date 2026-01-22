import React, { useState, useEffect, useMemo, useRef } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  flexRender,
} from '@tanstack/react-table';
import type { ColumnFiltersState, SortingState, VisibilityState, ColumnDef, Column, Row as TRow, FilterFn } from '@tanstack/react-table';
import { useVirtualizer } from '@tanstack/react-virtual';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Filter, Save, ArrowUpDown, Eye, EyeOff, X, ChevronDown, Plus, Trash2, GripVertical, Check, Loader2, Download } from 'lucide-react';
import { toast } from 'sonner';
import { api, type TableConfig, type ColumnSchema, type SavedVersion, type ColumnConfig } from '@/lib/api';

// Custom filter types
interface NumberRangeFilter {
  min?: number;
  max?: number;
}

interface DateMultiSelectFilter {
  selectedDates: string[];
}

// Custom filter functions
const numberRangeFilter: FilterFn<Record<string, unknown>> = (row, columnId, filterValue: NumberRangeFilter) => {
  const value = row.getValue(columnId) as number;
  if (value === null || value === undefined) return false;

  const { min, max } = filterValue;
  if (min !== undefined && value < min) return false;
  if (max !== undefined && value > max) return false;
  return true;
};

const dateMultiSelectFilter: FilterFn<Record<string, unknown>> = (row, columnId, filterValue: DateMultiSelectFilter) => {
  const value = row.getValue(columnId) as string;
  if (!value) return false;

  const { selectedDates } = filterValue;
  if (!selectedDates || selectedDates.length === 0) return true;

  // Normalize the date for comparison (just the date part)
  const rowDate = new Date(value).toISOString().split('T')[0];
  return selectedDates.includes(rowDate);
};

const booleanFilter: FilterFn<Record<string, unknown>> = (row, columnId, filterValue: string) => {
  if (filterValue === '__all__' || filterValue === '') return true;
  const value = row.getValue(columnId);
  if (filterValue === 'true') return value === true || value === 'true' || value === 1 || value === '1';
  if (filterValue === 'false') return value === false || value === 'false' || value === 0 || value === '0';
  return true;
};

interface DataTableProps {
  tableKey: string;
  config: TableConfig;
  onSave: (tableKey: string, records: Record<string, unknown>[]) => void;
}

export function DataTable({ tableKey, config, onSave }: DataTableProps) {
  const [data, setData] = useState<Record<string, unknown>[]>(config?.data || []);
  const [modifiedIds, setModifiedIds] = useState<Set<number | string>>(new Set());
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({});
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
  const [sorting, setSorting] = useState<SortingState>([]);
  const [columnOrder, setColumnOrder] = useState<string[]>([]);
  const [showColumnSelector, setShowColumnSelector] = useState(false);
  const [exportOption, setExportOption] = useState('all');
  const [loading, setLoading] = useState(false);

  // Drag-to-fill state
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState<string | null>(null);
  const [dragEnd, setDragEnd] = useState<string | null>(null);
  const [dragColumn, setDragColumn] = useState<string | null>(null);

  // Refs to track latest drag state for event handlers (avoids stale closures)
  const dragStateRef = useRef({ isDragging: false, dragStart: null as string | null, dragEnd: null as string | null, dragColumn: null as string | null });

  // Column drag state
  const [draggedColumn, setDraggedColumn] = useState<string | null>(null);
  const [dragOverColumn, setDragOverColumn] = useState<string | null>(null);
  const [panelDraggedColumn, setPanelDraggedColumn] = useState<string | null>(null);
  const [panelDragOverColumn, setPanelDragOverColumn] = useState<string | null>(null);

  // Version management state
  const [savedVersions, setSavedVersions] = useState<SavedVersion[]>([]);
  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(null);
  const [showVersionDropdown, setShowVersionDropdown] = useState(false);
  const [showSaveVersionInput, setShowSaveVersionInput] = useState(false);
  const [newVersionName, setNewVersionName] = useState('');
  const [versionLoading, setVersionLoading] = useState(false);

  const tableContainerRef = useRef<HTMLDivElement>(null);
  const tableRef = useRef<ReturnType<typeof useReactTable<Record<string, unknown>>> | null>(null);

  // Sync data when config changes
  useEffect(() => {
    if (config?.data) {
      setData(config.data);
      setModifiedIds(new Set());

      const initialVisibility: VisibilityState = {};
      config.schema?.columns?.forEach((col: ColumnSchema) => {
        if (col.visible === false) {
          initialVisibility[col.name] = false;
        }
      });
      setColumnVisibility(initialVisibility);

      if (config.schema?.columns) {
        setColumnOrder(config.schema.columns.map((col: ColumnSchema) => col.name));
      }
    }
  }, [config]);

  // Load versions
  useEffect(() => {
    loadVersions();
  }, [tableKey]);

  const loadVersions = async () => {
    try {
      const response = await api.getVersions(tableKey);
      setSavedVersions(response.versions || []);
    } catch (error) {
      // Silently fail - versions are optional
    }
  };

  // Close dropdowns on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (showVersionDropdown && !(event.target as Element).closest('.version-dropdown')) {
        setShowVersionDropdown(false);
        setShowSaveVersionInput(false);
        setNewVersionName('');
      }
      if (showColumnSelector && !(event.target as Element).closest('.column-selector')) {
        setShowColumnSelector(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showVersionDropdown, showColumnSelector]);

  // Keep drag state ref in sync
  useEffect(() => {
    dragStateRef.current = { isDragging, dragStart, dragEnd, dragColumn };
  }, [isDragging, dragStart, dragEnd, dragColumn]);

  // Drag-to-fill handlers - uses refs to avoid stale closures
  useEffect(() => {
    const handleMouseUp = () => {
      const state = dragStateRef.current;
      if (state.isDragging && state.dragStart && state.dragEnd && state.dragColumn && tableRef.current) {
        const visibleRows = tableRef.current.getRowModel().rows;
        const startIndex = visibleRows.findIndex(r => r.id === state.dragStart);
        const endIndex = visibleRows.findIndex(r => r.id === state.dragEnd);

        if (startIndex !== -1 && endIndex !== -1) {
          const minIndex = Math.min(startIndex, endIndex);
          const maxIndex = Math.max(startIndex, endIndex);
          const startRowData = visibleRows[startIndex].original;
          const fillValue = startRowData[state.dragColumn!];
          const rowsToUpdate = visibleRows.slice(minIndex, maxIndex + 1);

          setData(prev => {
            const newData = prev.map((row) => {
              const shouldUpdate = rowsToUpdate.some(r => r.original === row);
              if (shouldUpdate && row !== startRowData) {
                setModifiedIds(ids => new Set(ids).add(row.id as string | number));
                return { ...row, [state.dragColumn!]: fillValue };
              }
              return row;
            });
            return newData;
          });
        }

        // Reset drag state
        setIsDragging(false);
        setDragStart(null);
        setDragEnd(null);
        setDragColumn(null);
      }
    };

    const handleMouseMove = (e: MouseEvent) => {
      if (dragStateRef.current.isDragging) {
        const element = document.elementFromPoint(e.clientX, e.clientY);
        if (element) {
          const cell = element.closest('[data-row-id]');
          if (cell) {
            const rowId = cell.getAttribute('data-row-id');
            if (rowId && rowId !== dragStateRef.current.dragEnd) {
              setDragEnd(rowId);
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
  }, []);

  const updateData = (rowIndex: number, columnId: string, value: unknown) => {
    setData(prev => {
      const newData = [...prev];
      const row = newData[rowIndex];
      if (row) {
        newData[rowIndex] = { ...row, [columnId]: value };
        setModifiedIds(ids => new Set(ids).add(row.id as string | number));
      }
      return newData;
    });
  };

  const handleDragStart = (rowId: string, columnId: string) => {
    setIsDragging(true);
    setDragStart(rowId);
    setDragEnd(rowId);
    setDragColumn(columnId);
  };

  // Version management functions
  const getCurrentColumnConfig = (): ColumnConfig[] => {
    const allColumns = table.getAllLeafColumns();
    return allColumns.map(col => ({
      id: col.id,
      visible: col.getIsVisible()
    }));
  };

  const applyVersion = (version: SavedVersion) => {
    const newVisibility: Record<string, boolean> = {};
    version.columns.forEach(col => {
      newVisibility[col.id] = col.visible;
    });
    setColumnVisibility(newVisibility);
    setColumnOrder(version.columns.map(col => col.id));
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
      toast.success('Version saved', { description: `"${newVersionName.trim()}" created successfully` });
    } catch (error) {
      toast.error('Failed to save version', { description: 'Please try again' });
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
      toast.success('Version updated', { description: 'Changes saved successfully' });
    } catch (error) {
      toast.error('Failed to update version', { description: 'Please try again' });
    } finally {
      setVersionLoading(false);
    }
  };

  const handleDeleteVersion = async (versionId: string, e: React.MouseEvent) => {
    e.stopPropagation();

    setVersionLoading(true);
    try {
      await api.deleteVersion(versionId);
      setSavedVersions(prev => prev.filter(v => v.id !== versionId));
      if (selectedVersionId === versionId) {
        setSelectedVersionId(null);
      }
      toast.success('Version deleted');
    } catch (error) {
      toast.error('Failed to delete version', { description: 'Please try again' });
    } finally {
      setVersionLoading(false);
    }
  };

  const resetToDefault = () => {
    const initialVisibility: VisibilityState = {};
    config.schema?.columns?.forEach((col: ColumnSchema) => {
      if (col.visible === false) {
        initialVisibility[col.name] = false;
      }
    });
    setColumnVisibility(initialVisibility);
    setColumnOrder(config.schema?.columns?.map((col: ColumnSchema) => col.name) || []);
    setSelectedVersionId(null);
    setShowVersionDropdown(false);
  };

  // Column drag handlers
  const handleColumnDragStart = (columnId: string) => setDraggedColumn(columnId);

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

  // Panel column drag handlers
  const handlePanelColumnDragStart = (columnId: string) => setPanelDraggedColumn(columnId);

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

  // Export handler
  const handleExport = async () => {
    setLoading(true);
    try {
      const visibleRows = table.getRowModel().rows.map(row => row.original);
      const blob = await api.exportData(tableKey, exportOption, visibleRows);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${tableKey}_export_${Date.now()}.xlsx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url)
      ;
      document.body.removeChild(a);
      toast.success('Export successful', { description: 'Your file is downloading' });
    } catch (error) {
      toast.error('Export failed', { description: 'Please make sure the backend is running' });
    } finally {
      setLoading(false);
    }
  };

  // Save handler
  const handleSave = () => {
    const modifiedRecords = data.filter(record => modifiedIds.has(record.id as string | number));
    const recordsToSave = modifiedRecords.length > 0 ? modifiedRecords : data;
    onSave(tableKey, recordsToSave);
    setModifiedIds(new Set());
  };

  // Define columns
  const columns = useMemo((): ColumnDef<Record<string, unknown>>[] => {
    if (!config?.schema) return [];

    return config.schema.columns.map((col: ColumnSchema): ColumnDef<Record<string, unknown>> => ({
      accessorKey: col.name,
      header: ({ column }: { column: Column<Record<string, unknown>> }) => (
        <div className="flex items-center gap-2 min-w-0">
          <span
            className="font-semibold text-xs uppercase tracking-wider text-gray-500 truncate"
            title={col.label}
          >
            {col.label}
          </span>
          {col.editable && (
            <Button
              variant="ghost"
              size="sm"
              className="h-6 w-6 p-0 hover:bg-teal-50 flex-shrink-0"
              onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
            >
              <ArrowUpDown className="h-3 w-3 text-gray-400" />
            </Button>
          )}
        </div>
      ),
      cell: ({ row, column }: { row: TRow<Record<string, unknown>>; column: Column<Record<string, unknown>> }) => {
        const value = row.getValue(column.id) as string;
        const rowId = row.id;

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
          return <div className="px-2 py-1 text-gray-700">{value}</div>;
        }

        if (col.type === 'select') {
          return (
            <div className={`relative group ${isInDragRange ? 'bg-teal-50 rounded' : ''}`}>
              <Select
                value={value}
                onValueChange={(newValue) => updateData(row.index, column.id, newValue)}
              >
                <SelectTrigger className="border-0 focus:ring-1 focus:ring-teal-300 h-8 bg-transparent">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {col.options?.map(option => (
                    <SelectItem key={option} value={option}>{option}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <div
                className="absolute bottom-0 right-0 w-3 h-3 bg-teal-500 cursor-ns-resize opacity-0 group-hover:opacity-100 transition-opacity z-10 rounded-tl"
                onMouseDown={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  handleDragStart(rowId, column.id);
                }}
                title="Drag to fill down"
              />
            </div>
          );
        }

        return (
          <div className={`relative group ${isInDragRange ? 'bg-teal-50 rounded' : ''}`}>
            <Input
              value={value}
              onChange={(e) => updateData(row.index, column.id, e.target.value)}
              className="border-0 focus-visible:ring-1 focus-visible:ring-teal-300 h-8 bg-transparent"
            />
            <div
              className="absolute bottom-0 right-0 w-3 h-3 bg-teal-500 cursor-ns-resize opacity-0 group-hover:opacity-100 transition-opacity z-10 rounded-tl"
              onMouseDown={(e) => {
                e.preventDefault();
                e.stopPropagation();
                handleDragStart(rowId, column.id);
              }}
              title="Drag to fill down"
            />
          </div>
        );
      },
      filterFn: col.type === 'number' ? numberRangeFilter :
               col.type === 'date' ? dateMultiSelectFilter :
               col.type === 'boolean' ? booleanFilter :
               'includesString',
    }));
  }, [config, dragStart, dragEnd, dragColumn, isDragging]);

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

  // Store table reference for drag-to-fill handlers
  tableRef.current = table;

  const { rows } = table.getRowModel();

  const rowVirtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => tableContainerRef.current,
    estimateSize: () => 45,
    overscan: 10,
  });

  const visibleCount = table.getAllLeafColumns().filter(col => col.getIsVisible()).length;
  const totalCount = table.getAllLeafColumns().length;
  const selectedVersion = savedVersions.find(v => v.id === selectedVersionId);

  if (!config?.schema) {
    return (
      <div className="bg-white rounded-2xl border border-gray-200 p-12 text-center">
        <div className="w-16 h-16 rounded-full bg-gray-100 flex items-center justify-center mx-auto mb-4">
          <Filter className="w-8 h-8 text-gray-400" />
        </div>
        <h3 className="text-lg font-semibold text-gray-900 mb-2">No data loaded</h3>
        <p className="text-gray-500">Use the sidebar to load data from the API</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Version Selector */}
      <div className="flex items-center gap-3 bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
        <span className="text-sm font-medium text-gray-600">View:</span>
        <div className="relative version-dropdown">
          <button
            onClick={() => setShowVersionDropdown(!showVersionDropdown)}
            className={`
              flex items-center gap-2 px-4 py-2 border rounded-lg text-sm font-medium min-w-[180px]
              transition-all duration-200
              ${showVersionDropdown ? 'border-teal-300 ring-2 ring-teal-100' : 'border-gray-200 hover:border-teal-200'}
            `}
          >
            <span className="flex-1 text-left truncate text-gray-700">
              {selectedVersion ? selectedVersion.name : 'Default View'}
            </span>
            <ChevronDown className={`h-4 w-4 text-gray-400 transition-transform ${showVersionDropdown ? 'rotate-180' : ''}`} />
          </button>

          {showVersionDropdown && (
            <div className="absolute left-0 top-full mt-2 bg-white border border-gray-200 rounded-xl shadow-xl z-20 min-w-[240px] py-2 animate-scale-in">
              <button
                onClick={resetToDefault}
                className={`w-full flex items-center justify-between px-4 py-2.5 text-sm hover:bg-gray-50 ${!selectedVersionId ? 'bg-teal-50 text-teal-700' : 'text-gray-700'}`}
              >
                <span>Default View</span>
                {!selectedVersionId && <Check className="h-4 w-4" />}
              </button>

              {savedVersions.length > 0 && <div className="border-t border-gray-100 my-2" />}

              {savedVersions.map(version => (
                <button
                  key={version.id}
                  onClick={() => applyVersion(version)}
                  className={`w-full flex items-center justify-between px-4 py-2.5 text-sm hover:bg-gray-50 group ${selectedVersionId === version.id ? 'bg-teal-50 text-teal-700' : 'text-gray-700'}`}
                >
                  <span className="truncate flex-1 text-left">{version.name}</span>
                  <div className="flex items-center gap-1">
                    {selectedVersionId === version.id && <Check className="h-4 w-4" />}
                    <button
                      onClick={(e) => handleDeleteVersion(version.id, e)}
                      className="p-1 hover:bg-red-100 rounded opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      <Trash2 className="h-3 w-3 text-red-500" />
                    </button>
                  </div>
                </button>
              ))}

              <div className="border-t border-gray-100 my-2" />

              {showSaveVersionInput ? (
                <div className="px-3 py-2">
                  <div className="flex gap-2">
                    <Input
                      value={newVersionName}
                      onChange={(e) => setNewVersionName(e.target.value)}
                      placeholder="Version name..."
                      className="h-9 text-sm"
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
                      className="h-9 px-3 bg-teal-600 hover:bg-teal-700"
                    >
                      {versionLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
                    </Button>
                  </div>
                </div>
              ) : (
                <button
                  onClick={() => setShowSaveVersionInput(true)}
                  className="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-teal-600 hover:bg-teal-50"
                >
                  <Plus className="h-4 w-4" />
                  Save current as new...
                </button>
              )}
            </div>
          )}
        </div>

        {selectedVersionId && (
          <Button
            variant="outline"
            size="sm"
            onClick={handleUpdateVersion}
            disabled={versionLoading}
            className="gap-1 text-xs border-teal-200 text-teal-700 hover:bg-teal-50"
          >
            {versionLoading ? <Loader2 className="h-3 w-3 animate-spin" /> : <Save className="h-3 w-3" />}
            Update
          </Button>
        )}
      </div>

      {/* Controls Row */}
      <div className="flex items-center justify-between bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-teal-50 flex items-center justify-center">
            <Filter className="h-5 w-5 text-teal-600" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-gray-900">Filters</h3>
            <p className="text-xs text-gray-500">Use column headers to filter data</p>
          </div>
        </div>

        <div className="flex gap-3 items-center">
          {/* Column Selector */}
          <div className="relative column-selector">
            <Button
              onClick={() => setShowColumnSelector(!showColumnSelector)}
              variant="outline"
              className="gap-2 border-gray-200 text-gray-700 hover:bg-gray-50 hover:border-teal-200"
            >
              <Eye className="h-4 w-4 text-gray-500" />
              Columns
              <span className="bg-teal-50 text-teal-700 px-2 py-0.5 rounded-full text-xs font-semibold">
                {visibleCount}/{totalCount}
              </span>
            </Button>

            {showColumnSelector && (
              <div className="absolute right-0 top-full mt-2 bg-white border border-gray-200 rounded-xl shadow-xl p-4 z-20 min-w-[320px] animate-scale-in">
                <div className="flex items-center justify-between mb-4 pb-3 border-b border-gray-100">
                  <div>
                    <span className="font-semibold text-sm text-gray-900">Manage Columns</span>
                    <p className="text-[11px] text-gray-400 mt-0.5">Drag to reorder, toggle visibility</p>
                  </div>
                  <button onClick={() => setShowColumnSelector(false)} className="text-gray-400 hover:text-gray-600 p-1 hover:bg-gray-100 rounded">
                    <X className="h-4 w-4" />
                  </button>
                </div>

                <div className="space-y-1 max-h-[400px] overflow-y-auto custom-scrollbar">
                  {table.getAllLeafColumns().map(column => {
                    const colConfig = config.schema?.columns.find((c: ColumnSchema) => c.name === column.id);
                    const isDraggingThis = panelDraggedColumn === column.id;
                    const isDropTarget = panelDragOverColumn === column.id;
                    return (
                      <div
                        key={column.id}
                        draggable
                        onDragStart={() => handlePanelColumnDragStart(column.id)}
                        onDragOver={(e) => handlePanelColumnDragOver(e, column.id)}
                        onDrop={() => handlePanelColumnDrop(column.id)}
                        onDragEnd={handlePanelColumnDragEnd}
                        className={`
                          flex items-center gap-2 p-2.5 rounded-lg transition-all cursor-move
                          ${isDraggingThis ? 'opacity-50 bg-teal-50' : 'hover:bg-gray-50'}
                          ${isDropTarget ? 'border-t-2 border-teal-500' : ''}
                        `}
                      >
                        <GripVertical className="h-4 w-4 text-gray-300 flex-shrink-0" />
                        <label className="flex items-center gap-2 flex-1 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={column.getIsVisible()}
                            onChange={column.getToggleVisibilityHandler()}
                            className="w-4 h-4 rounded border-gray-300 text-teal-600 focus:ring-teal-500"
                            onClick={(e) => e.stopPropagation()}
                          />
                          <span className={`text-sm flex-1 ${column.getIsVisible() ? 'text-gray-700' : 'text-gray-400'}`}>
                            {colConfig?.label || column.id}
                          </span>
                        </label>
                        {!column.getIsVisible() && (
                          <EyeOff className="h-3.5 w-3.5 text-gray-300 flex-shrink-0" />
                        )}
                      </div>
                    );
                  })}
                </div>

                <div className="mt-4 pt-3 border-t border-gray-100 flex justify-between items-center">
                  <span className="text-xs text-gray-500">{visibleCount} visible</span>
                  <Button size="sm" variant="ghost" className="h-8 text-xs" onClick={() => setShowColumnSelector(false)}>Done</Button>
                </div>
              </div>
            )}
          </div>

          {/* Save Button */}
          <Button
            onClick={handleSave}
            className={`
              gap-2 text-white transition-all
              ${modifiedIds.size > 0
                ? 'bg-teal-600 hover:bg-teal-700 shadow-teal'
                : 'bg-gray-900 hover:bg-gray-800'
              }
            `}
          >
            <Save className="h-4 w-4" />
            Save Changes
            {modifiedIds.size > 0 && (
              <span className="bg-white/20 px-2 py-0.5 rounded-full text-xs font-semibold">
                {modifiedIds.size}
              </span>
            )}
          </Button>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
        <div
          ref={tableContainerRef}
          className="overflow-auto max-h-[600px] custom-scrollbar"
        >
          <table className="text-sm text-left" style={{ minWidth: '100%' }}>
            <colgroup>
              {table.getVisibleLeafColumns().map(column => (
                <col key={column.id} style={{ minWidth: '180px' }} />
              ))}
            </colgroup>

            <thead className="bg-gray-50/80 border-b border-gray-200 sticky top-0 z-10 backdrop-blur-sm">
              {table.getHeaderGroups().map(headerGroup => (
                <React.Fragment key={headerGroup.id}>
                  <tr>
                    {headerGroup.headers.map(header => {
                      const isDraggingThis = draggedColumn === header.column.id;
                      const isDropTarget = dragOverColumn === header.column.id;
                      return (
                        <th
                          key={header.id}
                          draggable
                          onDragStart={() => handleColumnDragStart(header.column.id)}
                          onDragOver={(e) => handleColumnDragOver(e, header.column.id)}
                          onDrop={() => handleColumnDrop(header.column.id)}
                          onDragEnd={handleColumnDragEnd}
                          className={`
                            px-4 py-3 font-medium text-gray-500 bg-gray-50 border-b border-gray-100 cursor-move transition-all
                            ${isDraggingThis ? 'opacity-50 bg-teal-100' : ''}
                            ${isDropTarget ? 'border-l-4 border-l-teal-500' : ''}
                          `}
                        >
                          {flexRender(header.column.columnDef.header, header.getContext())}
                        </th>
                      );
                    })}
                  </tr>
                  <tr>
                    {headerGroup.headers.map(header => {
                      const colConfig = config.schema?.columns.find((c: ColumnSchema) => c.name === header.column.id);
                      const filterValue = header.column.getFilterValue();

                      // Number range filter
                      if (colConfig?.type === 'number') {
                        const rangeValue = (filterValue as NumberRangeFilter) || {};
                        return (
                          <th key={header.id} className="px-2 py-2 bg-gray-50/50">
                            <div className="flex gap-1">
                              <Input
                                type="number"
                                placeholder="Min"
                                value={rangeValue.min ?? ''}
                                onChange={(e) => {
                                  const min = e.target.value ? Number(e.target.value) : undefined;
                                  header.column.setFilterValue({ ...rangeValue, min });
                                }}
                                className="h-8 text-xs border-gray-200 focus:ring-teal-300 w-1/2"
                              />
                              <Input
                                type="number"
                                placeholder="Max"
                                value={rangeValue.max ?? ''}
                                onChange={(e) => {
                                  const max = e.target.value ? Number(e.target.value) : undefined;
                                  header.column.setFilterValue({ ...rangeValue, max });
                                }}
                                className="h-8 text-xs border-gray-200 focus:ring-teal-300 w-1/2"
                              />
                            </div>
                          </th>
                        );
                      }

                      // Date multi-select filter
                      if (colConfig?.type === 'date') {
                        const multiSelectValue = (filterValue as DateMultiSelectFilter) || { selectedDates: [] };
                        const uniqueDates = [...new Set(
                          data
                            .map(row => row[header.column.id] as string)
                            .filter(Boolean)
                            .map(d => new Date(d).toISOString().split('T')[0])
                        )].sort();

                        return (
                          <th key={header.id} className="px-2 py-2 bg-gray-50/50">
                            <div className="relative">
                              <Select
                                value={multiSelectValue.selectedDates.length > 0 ? 'custom' : '__all__'}
                                onValueChange={(value) => {
                                  if (value === '__all__') {
                                    header.column.setFilterValue(undefined);
                                  }
                                }}
                              >
                                <SelectTrigger className="h-8 text-xs border-gray-200 focus:ring-teal-300">
                                  <SelectValue>
                                    {multiSelectValue.selectedDates.length > 0
                                      ? `${multiSelectValue.selectedDates.length} selected`
                                      : 'All dates'}
                                  </SelectValue>
                                </SelectTrigger>
                                <SelectContent className="max-h-[300px]">
                                  <div className="p-2 border-b border-gray-100">
                                    <button
                                      className="w-full text-left text-xs text-teal-600 hover:text-teal-700 font-medium"
                                      onClick={(e) => {
                                        e.preventDefault();
                                        header.column.setFilterValue(undefined);
                                      }}
                                    >
                                      Clear all
                                    </button>
                                  </div>
                                  <div className="py-1 max-h-[200px] overflow-y-auto">
                                    {uniqueDates.map(date => {
                                      const isSelected = multiSelectValue.selectedDates.includes(date);
                                      const displayDate = new Date(date + 'T00:00:00').toLocaleDateString('en-US', {
                                        year: 'numeric',
                                        month: 'short',
                                        day: 'numeric'
                                      });
                                      return (
                                        <div
                                          key={date}
                                          className="flex items-center gap-2 px-3 py-1.5 hover:bg-gray-50 cursor-pointer"
                                          onClick={(e) => {
                                            e.preventDefault();
                                            e.stopPropagation();
                                            const newDates = isSelected
                                              ? multiSelectValue.selectedDates.filter(d => d !== date)
                                              : [...multiSelectValue.selectedDates, date];
                                            header.column.setFilterValue(
                                              newDates.length > 0 ? { selectedDates: newDates } : undefined
                                            );
                                          }}
                                        >
                                          <div className={`w-4 h-4 rounded border flex items-center justify-center ${isSelected ? 'bg-teal-600 border-teal-600' : 'border-gray-300'}`}>
                                            {isSelected && <Check className="h-3 w-3 text-white" />}
                                          </div>
                                          <span className="text-xs text-gray-700">{displayDate}</span>
                                        </div>
                                      );
                                    })}
                                  </div>
                                </SelectContent>
                              </Select>
                            </div>
                          </th>
                        );
                      }

                      // Boolean filter
                      if (colConfig?.type === 'boolean') {
                        return (
                          <th key={header.id} className="px-4 py-2 bg-gray-50/50">
                            <Select
                              value={(filterValue as string) ?? '__all__'}
                              onValueChange={(value) => header.column.setFilterValue(value === '__all__' ? undefined : value)}
                            >
                              <SelectTrigger className="h-8 text-xs border-gray-200 focus:ring-teal-300">
                                <SelectValue placeholder="All" />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="__all__">All</SelectItem>
                                <SelectItem value="true">Yes</SelectItem>
                                <SelectItem value="false">No</SelectItem>
                              </SelectContent>
                            </Select>
                          </th>
                        );
                      }

                      // Select filter (dropdown with options)
                      if (colConfig?.type === 'select' && colConfig.options) {
                        return (
                          <th key={header.id} className="px-4 py-2 bg-gray-50/50">
                            <Select
                              value={(filterValue as string) ?? '__all__'}
                              onValueChange={(value) => header.column.setFilterValue(value === '__all__' ? undefined : value)}
                            >
                              <SelectTrigger className="h-8 text-xs border-gray-200 focus:ring-teal-300">
                                <SelectValue placeholder="All" />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="__all__">All</SelectItem>
                                {colConfig.options?.map((option: string) => (
                                  <SelectItem key={option} value={option}>{option}</SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          </th>
                        );
                      }

                      // Default: text filter
                      return (
                        <th key={header.id} className="px-4 py-2 bg-gray-50/50">
                          <Input
                            placeholder="Filter..."
                            value={(filterValue as string) ?? ''}
                            onChange={(e) => header.column.setFilterValue(e.target.value || undefined)}
                            className="h-8 text-xs border-gray-200 focus:ring-teal-300"
                          />
                        </th>
                      );
                    })}
                  </tr>
                </React.Fragment>
              ))}
            </thead>

            <tbody>
              {rowVirtualizer.getVirtualItems().length > 0 && (
                <tr style={{ height: `${rowVirtualizer.getVirtualItems()[0]?.start ?? 0}px` }}>
                  <td colSpan={table.getVisibleLeafColumns().length} />
                </tr>
              )}
              {rowVirtualizer.getVirtualItems().map(virtualRow => {
                const row = rows[virtualRow.index];
                const isModified = modifiedIds.has(row.original.id as string | number);
                return (
                  <tr
                    key={row.id}
                    className={`
                      hover:bg-teal-50/50 transition-colors group
                      ${isModified ? 'bg-amber-50/50' : ''}
                    `}
                    style={{ height: `${virtualRow.size}px` }}
                  >
                    {row.getVisibleCells().map(cell => (
                      <td
                        key={cell.id}
                        className="px-4 py-2.5 border-b border-gray-100 group-hover:border-teal-100"
                        data-row-id={row.id}
                      >
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    ))}
                  </tr>
                );
              })}
              {rowVirtualizer.getVirtualItems().length > 0 && (
                <tr style={{
                  height: `${rowVirtualizer.getTotalSize() - (rowVirtualizer.getVirtualItems()[rowVirtualizer.getVirtualItems().length - 1]?.end ?? 0)}px`
                }}>
                  <td colSpan={table.getVisibleLeafColumns().length} />
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Row count */}
      <div className="flex items-center justify-between bg-white px-4 py-3 rounded-xl border border-gray-200 shadow-sm text-sm">
        <span className="text-gray-600">
          Showing <span className="font-semibold text-gray-900">{rows.length}</span> of{' '}
          <span className="font-semibold text-gray-900">{data.length}</span> records
          {rows.length !== data.length && (
            <span className="ml-2 text-teal-600 font-medium">(filtered)</span>
          )}
        </span>
        {modifiedIds.size > 0 && (
          <span className="text-amber-600 font-medium">
            {modifiedIds.size} unsaved change{modifiedIds.size > 1 ? 's' : ''}
          </span>
        )}
      </div>

      {/* Export Section for Users Table */}
      {tableKey === 'users' && (
        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
          <h4 className="text-base font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Download className="w-5 h-5 text-teal-600" />
            Export Options
          </h4>
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {['all', 'filtered', 'selected'].map(option => (
                <label
                  key={option}
                  className={`
                    flex items-center gap-3 cursor-pointer p-4 border rounded-xl transition-all
                    ${exportOption === option
                      ? 'border-teal-300 bg-teal-50 ring-2 ring-teal-100'
                      : 'border-gray-200 hover:border-teal-200 hover:bg-gray-50'
                    }
                  `}
                >
                  <input
                    type="radio"
                    name="exportOption"
                    value={option}
                    checked={exportOption === option}
                    onChange={(e) => setExportOption(e.target.value)}
                    className="w-4 h-4 text-teal-600 focus:ring-teal-500"
                  />
                  <div>
                    <span className="text-sm font-medium text-gray-900 capitalize">{option}</span>
                    <p className="text-xs text-gray-500">
                      {option === 'all' && `${data.length} records`}
                      {option === 'filtered' && `${rows.length} records`}
                      {option === 'selected' && 'Choose columns'}
                    </p>
                  </div>
                </label>
              ))}
            </div>
            <Button
              onClick={handleExport}
              className="w-full gap-2 h-12 bg-gradient-teal hover:opacity-90 text-white font-semibold shadow-teal"
              disabled={loading}
            >
              {loading ? (
                <>
                  <Loader2 className="h-5 w-5 animate-spin" />
                  Exporting...
                </>
              ) : (
                <>
                  <Download className="h-5 h-5" />
                  Export to Excel
                </>
              )}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
