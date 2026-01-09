#src/components/data-table/DataTable.tsximport React, { useState, useEffect, useMemo, useRef } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  flexRender,
} from '@tanstack/react-table';
import type { ColumnFiltersState, SortingState, VisibilityState, ColumnDef, Column, Row as TRow } from '@tanstack/react-table';
import { useVirtualizer } from '@tanstack/react-virtual';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Filter, Save, ArrowUpDown, Eye, EyeOff, X, ChevronDown, Plus, Trash2, GripVertical, Check, Loader2, Download } from 'lucide-react';
import { toast } from 'sonner';
import { api, type TableConfig, type ColumnSchema, type SavedVersion, type ColumnConfig } from '@/lib/api';

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

  // Drag-to-fill handlers
  useEffect(() => {
    const handleMouseUp = () => {
      if (isDragging) {
        handleDragEnd();
      }
    };

    const handleMouseMove = (e: MouseEvent) => {
      if (isDragging) {
        const element = document.elementFromPoint(e.clientX, e.clientY);
        if (element) {
          const cell = element.closest('[data-row-id]');
          if (cell) {
            const rowId = cell.getAttribute('data-row-id');
            if (rowId) {
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
  }, [isDragging, dragStart, dragColumn]);

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

  const handleDragEnd = () => {
    if (isDragging && dragStart && dragEnd && dragColumn) {
      const visibleRows = table.getRowModel().rows;
      const startIndex = visibleRows.findIndex(r => r.id === dragStart);
      const endIndex = visibleRows.findIndex(r => r.id === dragEnd);

      if (startIndex !== -1 && endIndex !== -1) {
        const minIndex = Math.min(startIndex, endIndex);
        const maxIndex = Math.max(startIndex, endIndex);
        const startRowData = visibleRows[startIndex].original;
        const fillValue = startRowData[dragColumn];
        const rowsToUpdate = visibleRows.slice(minIndex, maxIndex + 1);

        setData(prev => {
          const newData = prev.map((row) => {
            const shouldUpdate = rowsToUpdate.some(r => r.original === row);
            if (shouldUpdate && row !== startRowData) {
              setModifiedIds(ids => new Set(ids).add(row.id as string | number));
              return { ...row, [dragColumn]: fillValue };
            }
            return row;
          });
          return newData;
        });
      }
    }

    setIsDragging(false);
    setDragStart(null);
    setDragEnd(null);
    setDragColumn(null);
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
      window.URL.revokeObjectURL(url);
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
        <div className="flex items-center gap-2">
          <span className="font-semibold text-xs uppercase tracking-wider text-gray-500">{col.label}</span>
          {col.editable && (
            <Button
              variant="ghost"
              size="sm"
              className="h-6 w-6 p-0 hover:bg-teal-50"
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
      filterFn: 'includesString' as const,
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
          <table className="w-full text-sm text-left" style={{ tableLayout: 'fixed' }}>
            <colgroup>
              {table.getVisibleLeafColumns().map(column => (
                <col key={column.id} style={{ width: '150px', minWidth: '150px' }} />
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
                            px-4 py-3 font-medium text-gray-500 bg-gray-50 whitespace-nowrap border-b border-gray-100 cursor-move transition-all
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
                      return (
                        <th key={header.id} className="px-4 py-2 bg-gray-50/50">
                          {colConfig?.type === 'select' && colConfig.options ? (
                            <Select
                              value={(header.column.getFilterValue() ?? '__all__') as string}
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
                          ) : (
                            <Input
                              placeholder="Filter..."
                              value={(header.column.getFilterValue() ?? '') as string}
                              onChange={(e) => header.column.setFilterValue(e.target.value)}
                              className="h-8 text-xs border-gray-200 focus:ring-teal-300"
                            />
                          )}
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

#src/components/layout/Sidebar.tsx 
import React, { useState, useEffect, useRef } from 'react';
import { Home, LayoutDashboard, Users, Filter, Upload, Loader2, Check, ChevronDown, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import { api } from '@/lib/api';

interface MenuItem {
  id: string;
  label: string;
  icon: React.ElementType;
}

interface SidebarProps {
  activeScreen: string;
  onScreenChange: (screen: string) => void;
  onLoadData: (departments: string[], statuses: string[]) => Promise<void>;
  loading: boolean;
}

const menuItems: MenuItem[] = [
  { id: 'home', label: 'Home', icon: Home },
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'users', label: 'Users', icon: Users }
];

export function Sidebar({ activeScreen, onScreenChange, onLoadData, loading }: SidebarProps) {
  const [availableDepartments, setAvailableDepartments] = useState<string[]>([]);
  const [selectedDepartments, setSelectedDepartments] = useState<string[]>([]);
  const [showDepartmentDropdown, setShowDepartmentDropdown] = useState(false);

  const [availableStatuses, setAvailableStatuses] = useState<string[]>([]);
  const [selectedStatuses, setSelectedStatuses] = useState<string[]>([]);
  const [showStatusDropdown, setShowStatusDropdown] = useState(false);

  const departmentRef = useRef<HTMLDivElement>(null);
  const statusRef = useRef<HTMLDivElement>(null);

  // Load filter options on mount
  useEffect(() => {
    const loadFilters = async () => {
      try {
        const [deptResponse, statusResponse] = await Promise.all([
          api.getDepartments(),
          api.getStatuses()
        ]);
        setAvailableDepartments(deptResponse.departments);
        setAvailableStatuses(statusResponse.statuses);
      } catch (error) {
        console.error('Failed to load filters:', error);
        toast.error('Failed to load filters', { description: 'Please check your connection' });
      }
    };
    loadFilters();
  }, []);

  // Close dropdowns when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (departmentRef.current && !departmentRef.current.contains(event.target as Node)) {
        setShowDepartmentDropdown(false);
      }
      if (statusRef.current && !statusRef.current.contains(event.target as Node)) {
        setShowStatusDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const toggleDepartment = (dept: string) => {
    setSelectedDepartments(prev =>
      prev.includes(dept) ? prev.filter(d => d !== dept) : [...prev, dept]
    );
  };

  const toggleStatus = (status: string) => {
    setSelectedStatuses(prev =>
      prev.includes(status) ? prev.filter(s => s !== status) : [...prev, status]
    );
  };

  const handleLoadData = () => {
    onLoadData(selectedDepartments, selectedStatuses);
  };

  return (
    <div className="w-72 bg-white border-r border-gray-200/80 flex flex-col h-screen">
      {/* Logo Section */}
      <div className="p-6 border-b border-gray-100">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-teal flex items-center justify-center shadow-teal">
            <LayoutDashboard className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-gray-900 tracking-tight">DataFlow</h1>
            <p className="text-xs text-gray-500 font-medium">Management Suite</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1 overflow-y-auto custom-scrollbar">
        <p className="px-3 mb-3 text-[10px] font-semibold text-gray-400 uppercase tracking-widest">
          Navigation
        </p>
        {menuItems.map((item, index) => {
          const Icon = item.icon;
          const isActive = activeScreen === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onScreenChange(item.id)}
              className={`
                w-full flex items-center gap-3 px-4 py-3 rounded-xl
                transition-all duration-200 font-medium text-sm
                animate-slide-up opacity-0
                ${isActive
                  ? 'bg-teal-50 text-teal-700 shadow-sm border border-teal-100'
                  : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                }
              `}
              style={{ animationDelay: `${index * 0.05}s`, animationFillMode: 'forwards' }}
            >
              <div className={`
                w-8 h-8 rounded-lg flex items-center justify-center transition-colors
                ${isActive ? 'bg-teal-100' : 'bg-gray-100 group-hover:bg-gray-200'}
              `}>
                <Icon className={`h-4 w-4 ${isActive ? 'text-teal-600' : 'text-gray-500'}`} />
              </div>
              <span>{item.label}</span>
              {isActive && (
                <div className="ml-auto w-1.5 h-1.5 rounded-full bg-teal-500 animate-pulse-teal" />
              )}
            </button>
          );
        })}
      </nav>

      {/* Filters Section */}
      <div className="p-4 border-t border-gray-100 space-y-4 bg-gray-50/50">
        <p className="px-1 text-[10px] font-semibold text-gray-400 uppercase tracking-widest flex items-center gap-2">
          <Filter className="w-3 h-3" />
          Filters
        </p>

        {/* Department Filter */}
        <div ref={departmentRef} className="relative">
          <button
            onClick={() => setShowDepartmentDropdown(!showDepartmentDropdown)}
            className={`
              w-full flex items-center justify-between px-4 py-2.5
              bg-white border rounded-xl text-sm font-medium
              transition-all duration-200 hover:border-teal-200 hover:shadow-sm
              ${showDepartmentDropdown ? 'border-teal-300 shadow-sm ring-2 ring-teal-100' : 'border-gray-200'}
            `}
          >
            <span className={selectedDepartments.length > 0 ? 'text-teal-700' : 'text-gray-600'}>
              {selectedDepartments.length > 0
                ? `${selectedDepartments.length} dept selected`
                : 'All departments'}
            </span>
            <ChevronDown className={`h-4 w-4 text-gray-400 transition-transform ${showDepartmentDropdown ? 'rotate-180' : ''}`} />
          </button>

          {showDepartmentDropdown && (
            <div className="absolute bottom-full left-0 right-0 mb-2 bg-white border border-gray-200 rounded-xl shadow-xl z-20 overflow-hidden animate-scale-in">
              <div className="p-2 border-b border-gray-100 flex items-center justify-between">
                <span className="text-xs font-semibold text-gray-500 px-2">Departments</span>
                {selectedDepartments.length > 0 && (
                  <button
                    onClick={() => setSelectedDepartments([])}
                    className="text-xs text-teal-600 hover:text-teal-700 font-medium px-2 py-1 rounded hover:bg-teal-50"
                  >
                    Clear
                  </button>
                )}
              </div>
              <div className="max-h-48 overflow-y-auto custom-scrollbar p-1">
                {availableDepartments.map((dept) => (
                  <button
                    key={dept}
                    onClick={() => toggleDepartment(dept)}
                    className={`
                      w-full flex items-center justify-between px-3 py-2 text-sm rounded-lg
                      transition-colors
                      ${selectedDepartments.includes(dept)
                        ? 'bg-teal-50 text-teal-700'
                        : 'text-gray-700 hover:bg-gray-50'
                      }
                    `}
                  >
                    <span>{dept}</span>
                    {selectedDepartments.includes(dept) && (
                      <Check className="h-4 w-4 text-teal-600" />
                    )}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Status Filter */}
        <div ref={statusRef} className="relative">
          <button
            onClick={() => setShowStatusDropdown(!showStatusDropdown)}
            className={`
              w-full flex items-center justify-between px-4 py-2.5
              bg-white border rounded-xl text-sm font-medium
              transition-all duration-200 hover:border-teal-200 hover:shadow-sm
              ${showStatusDropdown ? 'border-teal-300 shadow-sm ring-2 ring-teal-100' : 'border-gray-200'}
            `}
          >
            <span className={selectedStatuses.length > 0 ? 'text-teal-700' : 'text-gray-600'}>
              {selectedStatuses.length > 0
                ? `${selectedStatuses.length} status selected`
                : 'All statuses'}
            </span>
            <ChevronDown className={`h-4 w-4 text-gray-400 transition-transform ${showStatusDropdown ? 'rotate-180' : ''}`} />
          </button>

          {showStatusDropdown && (
            <div className="absolute bottom-full left-0 right-0 mb-2 bg-white border border-gray-200 rounded-xl shadow-xl z-20 overflow-hidden animate-scale-in">
              <div className="p-2 border-b border-gray-100 flex items-center justify-between">
                <span className="text-xs font-semibold text-gray-500 px-2">Statuses</span>
                {selectedStatuses.length > 0 && (
                  <button
                    onClick={() => setSelectedStatuses([])}
                    className="text-xs text-teal-600 hover:text-teal-700 font-medium px-2 py-1 rounded hover:bg-teal-50"
                  >
                    Clear
                  </button>
                )}
              </div>
              <div className="max-h-48 overflow-y-auto custom-scrollbar p-1">
                {availableStatuses.map((status) => (
                  <button
                    key={status}
                    onClick={() => toggleStatus(status)}
                    className={`
                      w-full flex items-center justify-between px-3 py-2 text-sm rounded-lg
                      transition-colors
                      ${selectedStatuses.includes(status)
                        ? 'bg-teal-50 text-teal-700'
                        : 'text-gray-700 hover:bg-gray-50'
                      }
                    `}
                  >
                    <span>{status}</span>
                    {selectedStatuses.includes(status) && (
                      <Check className="h-4 w-4 text-teal-600" />
                    )}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Selected filters chips */}
        {(selectedDepartments.length > 0 || selectedStatuses.length > 0) && (
          <div className="flex flex-wrap gap-1.5">
            {selectedDepartments.map(dept => (
              <span
                key={dept}
                className="inline-flex items-center gap-1 px-2 py-1 bg-teal-100 text-teal-700 text-xs font-medium rounded-lg"
              >
                {dept}
                <button onClick={() => toggleDepartment(dept)} className="hover:text-teal-900">
                  <X className="w-3 h-3" />
                </button>
              </span>
            ))}
            {selectedStatuses.map(status => (
              <span
                key={status}
                className="inline-flex items-center gap-1 px-2 py-1 bg-emerald-100 text-emerald-700 text-xs font-medium rounded-lg"
              >
                {status}
                <button onClick={() => toggleStatus(status)} className="hover:text-emerald-900">
                  <X className="w-3 h-3" />
                </button>
              </span>
            ))}
          </div>
        )}

        {/* Load Data Button */}
        <Button
          onClick={handleLoadData}
          disabled={loading}
          className="w-full gap-2 h-11 bg-gradient-teal hover:opacity-90 text-white font-semibold shadow-teal transition-all duration-200"
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
  );
}

#src/components/ui/button.tsx 
import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg text-sm font-semibold transition-all duration-200 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg:not([class*='size-'])]:size-4 shrink-0 [&_svg]:shrink-0 outline-none focus-visible:ring-2 focus-visible:ring-teal-500/50 focus-visible:ring-offset-2",
  {
    variants: {
      variant: {
        default: "bg-teal-600 text-white hover:bg-teal-700 shadow-sm hover:shadow-md",
        destructive:
          "bg-red-500 text-white hover:bg-red-600 shadow-sm focus-visible:ring-red-500/50",
        outline:
          "border border-gray-200 bg-white text-gray-700 shadow-sm hover:bg-gray-50 hover:border-gray-300 hover:text-gray-900",
        secondary:
          "bg-gray-100 text-gray-700 hover:bg-gray-200",
        ghost:
          "text-gray-600 hover:bg-gray-100 hover:text-gray-900",
        link: "text-teal-600 underline-offset-4 hover:underline hover:text-teal-700",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-8 rounded-md gap-1.5 px-3 text-xs",
        lg: "h-12 rounded-lg px-6 text-base",
        icon: "size-10",
        "icon-sm": "size-8",
        "icon-lg": "size-12",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

function Button({
  className,
  variant,
  size,
  asChild = false,
  ...props
}: React.ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean
  }) {
  const Comp = asChild ? Slot : "button"

  return (
    <Comp
      data-slot="button"
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { Button, buttonVariants }

#rc/components/ui/input.tsx 
import * as React from "react"

import { cn } from "@/lib/utils"

function Input({ className, type, ...props }: React.ComponentProps<"input">) {
  return (
    <input
      type={type}
      data-slot="input"
      className={cn(
        "flex h-10 w-full min-w-0 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm transition-all duration-200",
        "placeholder:text-gray-400",
        "focus:outline-none focus:border-teal-300 focus:ring-2 focus:ring-teal-500/20",
        "disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50 disabled:bg-gray-50",
        "file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-gray-700",
        className
      )}
      {...props}
    />
  )
}

export { Input }

#src/components/ui/select.tsx 
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
        "flex w-full items-center justify-between gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm transition-all duration-200",
        "placeholder:text-gray-400 data-[placeholder]:text-gray-400",
        "focus:outline-none focus:border-teal-300 focus:ring-2 focus:ring-teal-500/20",
        "disabled:cursor-not-allowed disabled:opacity-50 disabled:bg-gray-50",
        "data-[size=default]:h-10 data-[size=sm]:h-8 data-[size=sm]:text-xs",
        "[&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
        className
      )}
      {...props}
    >
      {children}
      <SelectPrimitive.Icon asChild>
        <ChevronDownIcon className="size-4 text-gray-400" />
      </SelectPrimitive.Icon>
    </SelectPrimitive.Trigger>
  )
}

function SelectContent({
  className,
  children,
  position = "popper",
  ...props
}: React.ComponentProps<typeof SelectPrimitive.Content>) {
  return (
    <SelectPrimitive.Portal>
      <SelectPrimitive.Content
        data-slot="select-content"
        className={cn(
          "relative z-50 max-h-[300px] min-w-[8rem] overflow-hidden rounded-xl border border-gray-200 bg-white text-gray-900 shadow-xl",
          "data-[state=open]:animate-in data-[state=closed]:animate-out",
          "data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0",
          "data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95",
          "data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2",
          "data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2",
          position === "popper" && "data-[side=bottom]:translate-y-1 data-[side=top]:-translate-y-1",
          className
        )}
        position={position}
        {...props}
      >
        <SelectScrollUpButton />
        <SelectPrimitive.Viewport
          className={cn(
            "p-1",
            position === "popper" && "h-[var(--radix-select-trigger-height)] w-full min-w-[var(--radix-select-trigger-width)]"
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
      className={cn("px-2 py-1.5 text-xs font-semibold text-gray-500", className)}
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
        "relative flex w-full cursor-pointer items-center gap-2 rounded-lg py-2 pr-8 pl-3 text-sm text-gray-700 outline-none transition-colors",
        "select-none",
        "focus:bg-teal-50 focus:text-teal-700",
        "hover:bg-gray-50",
        "data-[disabled]:pointer-events-none data-[disabled]:opacity-50",
        "[&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
        className
      )}
      {...props}
    >
      <span className="absolute right-2 flex size-4 items-center justify-center">
        <SelectPrimitive.ItemIndicator>
          <CheckIcon className="size-4 text-teal-600" />
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
      className={cn("-mx-1 my-1 h-px bg-gray-100", className)}
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
        "flex cursor-default items-center justify-center py-1 text-gray-400",
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
        "flex cursor-default items-center justify-center py-1 text-gray-400",
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

#src/lib/api.ts 

// API Configuration
const API_BASE_URL = 'http://localhost:8000/api';

// Types
export interface FilterParams {
  departments?: string[];
  statuses?: string[];
}

export interface ColumnSchema {
  name: string;
  label: string;
  type?: string;
  editable?: boolean;
  visible?: boolean;
  options?: string[];
}

export interface TableSchema {
  columns: ColumnSchema[];
}

export interface TableConfig {
  schema: TableSchema | null;
  data: Record<string, unknown>[];
}

export interface ColumnConfig {
  id: string;
  visible: boolean;
}

export interface SavedVersion {
  id: string;
  name: string;
  view_type: string;
  columns: ColumnConfig[];
  created_at: string;
  updated_at: string;
}

export interface SaveResponse {
  success: boolean;
  transaction_id: string;
  records_updated: number;
}

// API Functions
export const api = {
  // Fetch available department filter options
  getDepartments: async (): Promise<{ departments: string[] }> => {
    const response = await fetch(`${API_BASE_URL}/departments`);
    if (!response.ok) throw new Error('Failed to fetch departments');
    return await response.json();
  },

  // Fetch available status filter options
  getStatuses: async (): Promise<{ statuses: string[] }> => {
    const response = await fetch(`${API_BASE_URL}/statuses`);
    if (!response.ok) throw new Error('Failed to fetch statuses');
    return await response.json();
  },

  dashboard: async (filters: FilterParams = {}): Promise<TableConfig> => {
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

  users: async (filters: FilterParams = {}): Promise<TableConfig> => {
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

  saveDashboard: async (data: Record<string, unknown>[]): Promise<SaveResponse> => {
    const response = await fetch(`${API_BASE_URL}/dashboard/save`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ data })
    });
    if (!response.ok) throw new Error('Failed to save dashboard data');
    return await response.json();
  },

  saveUsers: async (data: Record<string, unknown>[]): Promise<SaveResponse> => {
    const response = await fetch(`${API_BASE_URL}/users/save`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ data })
    });
    if (!response.ok) throw new Error('Failed to save users data');
    return await response.json();
  },

  // Version management APIs
  getVersions: async (viewType: string): Promise<{ versions: SavedVersion[] }> => {
    const response = await fetch(`${API_BASE_URL}/versions/${viewType}`);
    if (!response.ok) throw new Error('Failed to fetch versions');
    return await response.json();
  },

  createVersion: async (data: {
    name: string;
    view_type: string;
    columns: ColumnConfig[]
  }): Promise<SavedVersion> => {
    const response = await fetch(`${API_BASE_URL}/versions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!response.ok) throw new Error('Failed to create version');
    return await response.json();
  },

  updateVersion: async (
    versionId: string,
    data: { name?: string; columns?: ColumnConfig[] }
  ): Promise<SavedVersion> => {
    const response = await fetch(`${API_BASE_URL}/versions/${versionId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!response.ok) throw new Error('Failed to update version');
    return await response.json();
  },

  deleteVersion: async (versionId: string): Promise<{ success: boolean }> => {
    const response = await fetch(`${API_BASE_URL}/versions/${versionId}`, {
      method: 'DELETE'
    });
    if (!response.ok) throw new Error('Failed to delete version');
    return await response.json();
  },

  exportData: async (
    tableKey: string,
    option: string,
    data: Record<string, unknown>[]
  ): Promise<Blob> => {
    const response = await fetch(`${API_BASE_URL}/export/${tableKey}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ option, data })
    });
    if (!response.ok) throw new Error('Export failed');
    return await response.blob();
  }
};


#src/lib/utils.ts 
import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

#src/pages/HomePagge.tsx 
import { LayoutDashboard, Users, Download, Sparkles, ArrowRight, Zap, Shield, BarChart3 } from 'lucide-react';

const features = [
  {
    icon: LayoutDashboard,
    title: 'Dashboard Analytics',
    description: 'Real-time insights with powerful filtering and sorting capabilities.',
    color: 'teal',
  },
  {
    icon: Users,
    title: 'User Management',
    description: 'Comprehensive user data with inline editing and bulk operations.',
    color: 'emerald',
  },
  {
    icon: Download,
    title: 'Data Export',
    description: 'Export your data to Excel with customizable column selection.',
    color: 'cyan',
  },
];

const stats = [
  { label: 'Dashboard Records', value: '40+', icon: BarChart3 },
  { label: 'User Accounts', value: '35+', icon: Users },
  { label: 'Export Formats', value: '3', icon: Download },
];

const steps = [
  { number: '01', title: 'Load your data', description: 'Use the sidebar filters to fetch data from the API' },
  { number: '02', title: 'Customize your view', description: 'Toggle columns, apply filters, and sort as needed' },
  { number: '03', title: 'Edit and export', description: 'Make inline edits and export your results' },
];

export function HomePage() {
  return (
    <div className="min-h-full">
      {/* Hero Section */}
      <div className="relative overflow-hidden">
        {/* Background decoration */}
        <div className="absolute inset-0 bg-dot-pattern opacity-40" />
        <div className="absolute top-0 right-0 w-96 h-96 bg-teal-100 rounded-full blur-3xl opacity-30 -translate-y-1/2 translate-x-1/2" />
        <div className="absolute bottom-0 left-0 w-64 h-64 bg-emerald-100 rounded-full blur-3xl opacity-30 translate-y-1/2 -translate-x-1/2" />

        <div className="relative px-8 py-16">
          {/* Badge */}
          <div className="flex justify-center mb-6 animate-slide-up opacity-0" style={{ animationDelay: '0.1s', animationFillMode: 'forwards' }}>
            <span className="inline-flex items-center gap-2 px-4 py-2 bg-teal-50 border border-teal-200 rounded-full text-sm font-medium text-teal-700">
              <Sparkles className="w-4 h-4" />
              Welcome to DataFlow
            </span>
          </div>

          {/* Main heading */}
          <h1 className="text-center text-4xl md:text-5xl font-extrabold text-gray-900 mb-4 animate-slide-up opacity-0" style={{ animationDelay: '0.2s', animationFillMode: 'forwards' }}>
            Your Central Hub for{' '}
            <span className="text-gradient-teal">Data Management</span>
          </h1>

          <p className="text-center text-lg text-gray-600 max-w-2xl mx-auto mb-10 animate-slide-up opacity-0" style={{ animationDelay: '0.3s', animationFillMode: 'forwards' }}>
            Powerful data tables with inline editing, version control, and seamless export capabilities.
            Built for teams who need to move fast.
          </p>

          {/* CTA Buttons */}
          <div className="flex justify-center gap-4 animate-slide-up opacity-0" style={{ animationDelay: '0.4s', animationFillMode: 'forwards' }}>
            <button className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-teal text-white font-semibold rounded-xl shadow-teal hover:opacity-90 transition-opacity">
              Get Started
              <ArrowRight className="w-4 h-4" />
            </button>
            <button className="inline-flex items-center gap-2 px-6 py-3 bg-white text-gray-700 font-semibold rounded-xl border border-gray-200 hover:bg-gray-50 hover:border-gray-300 transition-colors">
              View Documentation
            </button>
          </div>
        </div>
      </div>

      {/* Stats Section */}
      <div className="px-8 py-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 max-w-4xl mx-auto">
          {stats.map((stat, index) => {
            const Icon = stat.icon;
            return (
              <div
                key={stat.label}
                className="bg-white rounded-2xl border border-gray-200 p-6 text-center hover-lift animate-slide-up opacity-0"
                style={{ animationDelay: `${0.5 + index * 0.1}s`, animationFillMode: 'forwards' }}
              >
                <div className="w-12 h-12 rounded-xl bg-teal-50 flex items-center justify-center mx-auto mb-3">
                  <Icon className="w-6 h-6 text-teal-600" />
                </div>
                <p className="text-3xl font-bold text-gray-900 mb-1">{stat.value}</p>
                <p className="text-sm text-gray-500 font-medium">{stat.label}</p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Features Section */}
      <div className="px-8 py-12">
        <div className="text-center mb-10">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Powerful Features</h2>
          <p className="text-gray-600">Everything you need to manage your data effectively</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl mx-auto">
          {features.map((feature, index) => {
            const Icon = feature.icon;
            const colorClasses = {
              teal: 'bg-teal-50 text-teal-600 border-teal-200',
              emerald: 'bg-emerald-50 text-emerald-600 border-emerald-200',
              cyan: 'bg-cyan-50 text-cyan-600 border-cyan-200',
            };
            return (
              <div
                key={feature.title}
                className="group bg-white rounded-2xl border border-gray-200 p-6 hover-lift animate-slide-up opacity-0"
                style={{ animationDelay: `${0.8 + index * 0.1}s`, animationFillMode: 'forwards' }}
              >
                <div className={`w-14 h-14 rounded-xl border flex items-center justify-center mb-4 ${colorClasses[feature.color as keyof typeof colorClasses]}`}>
                  <Icon className="w-7 h-7" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">{feature.title}</h3>
                <p className="text-gray-600 text-sm leading-relaxed">{feature.description}</p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Getting Started Section */}
      <div className="px-8 py-12 bg-gradient-subtle">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-10">
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Getting Started</h2>
            <p className="text-gray-600">Three simple steps to start managing your data</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {steps.map((step, index) => (
              <div
                key={step.number}
                className="relative animate-slide-up opacity-0"
                style={{ animationDelay: `${1.1 + index * 0.1}s`, animationFillMode: 'forwards' }}
              >
                {/* Connector line */}
                {index < steps.length - 1 && (
                  <div className="hidden md:block absolute top-8 left-[calc(100%+12px)] w-[calc(100%-48px)] h-[2px] bg-gradient-to-r from-teal-300 to-emerald-300" />
                )}

                <div className="bg-white rounded-2xl border border-gray-200 p-6">
                  <div className="w-16 h-16 rounded-full bg-gradient-teal flex items-center justify-center mb-4 shadow-teal">
                    <span className="text-xl font-bold text-white">{step.number}</span>
                  </div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">{step.title}</h3>
                  <p className="text-gray-600 text-sm">{step.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Bottom CTA */}
      <div className="px-8 py-16">
        <div className="max-w-3xl mx-auto text-center bg-gradient-teal rounded-3xl p-10 shadow-teal-lg">
          <div className="flex justify-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center">
              <Zap className="w-5 h-5 text-white" />
            </div>
            <div className="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center">
              <Shield className="w-5 h-5 text-white" />
            </div>
          </div>
          <h2 className="text-2xl font-bold text-white mb-3">Ready to dive in?</h2>
          <p className="text-teal-100 mb-6">
            Select Dashboard or Users from the sidebar to start exploring your data.
          </p>
          <div className="flex justify-center gap-2">
            <span className="px-4 py-2 bg-white/20 text-white text-sm font-medium rounded-lg">
              40 Dashboard Records
            </span>
            <span className="px-4 py-2 bg-white/20 text-white text-sm font-medium rounded-lg">
              35 User Accounts
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

#src/App.tsx 
import { useState } from 'react';
import { Loader2 } from 'lucide-react';
import { Toaster, toast } from 'sonner';
import { Sidebar } from '@/components/layout/Sidebar';
import { HomePage } from '@/pages/HomePage';
import { DataTable } from '@/components/data-table/DataTable';
import { api, type TableConfig } from '@/lib/api';

function App() {
  const [activeScreen, setActiveScreen] = useState('home');
  const [loading, setLoading] = useState(false);
  const [tableConfig, setTableConfig] = useState<Record<string, TableConfig>>({
    dashboard: { schema: null, data: [] },
    users: { schema: null, data: [] }
  });

  const loadDataFromAPI = async (departments: string[], statuses: string[]) => {
    setLoading(true);
    try {
      const filters = { departments, statuses };

      const [dashboardResponse, usersResponse] = await Promise.all([
        api.dashboard(filters),
        api.users(filters)
      ]);

      setTableConfig({
        dashboard: dashboardResponse,
        users: usersResponse
      });

      // Build filter info message
      const filterParts = [];
      if (departments.length > 0) {
        filterParts.push(`${departments.length} department${departments.length > 1 ? 's' : ''}`);
      }
      if (statuses.length > 0) {
        filterParts.push(`${statuses.length} status${statuses.length > 1 ? 'es' : ''}`);
      }

      const filterInfo = filterParts.length > 0 ? ` with ${filterParts.join(' and ')}` : '';
      toast.success('Data loaded successfully', {
        description: `Loaded ${dashboardResponse.data.length} dashboard records and ${usersResponse.data.length} users${filterInfo}`
      });
    } catch (error) {
      toast.error('Failed to load data', {
        description: 'Please make sure the backend is running at localhost:8000'
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (tableKey: string, modifiedRecords: Record<string, unknown>[]) => {
    if (!modifiedRecords || modifiedRecords.length === 0) {
      toast.info('No changes to save');
      return;
    }

    setLoading(true);
    try {
      let response;
      if (tableKey === 'dashboard') {
        response = await api.saveDashboard(modifiedRecords);
      } else if (tableKey === 'users') {
        response = await api.saveUsers(modifiedRecords);
      }

      if (response?.success) {
        toast.success('Changes saved successfully', {
          description: `Updated ${response.records_updated} record${response.records_updated > 1 ? 's' : ''}`
        });
      }
    } catch (error) {
      toast.error('Failed to save changes', {
        description: 'Please make sure the backend is running'
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-screen bg-gray-50/50">
      {/* Sidebar */}
      <Sidebar
        activeScreen={activeScreen}
        onScreenChange={setActiveScreen}
        onLoadData={loadDataFromAPI}
        loading={loading}
      />

      {/* Main Content */}
      <div className="flex-1 overflow-auto">
        <div className="p-8">
          {/* Header */}
          <div className="mb-8 animate-fade-in">
            <h2 className="text-2xl font-bold text-gray-900 tracking-tight">
              {activeScreen === 'home' && 'Welcome Back'}
              {activeScreen === 'dashboard' && 'Dashboard'}
              {activeScreen === 'users' && 'Users Management'}
            </h2>
            <p className="text-gray-500 mt-1">
              {activeScreen === 'home' && 'Your central hub for data management'}
              {activeScreen === 'dashboard' && 'View and manage dashboard analytics with powerful filtering'}
              {activeScreen === 'users' && 'Manage user accounts with inline editing and export'}
            </p>
          </div>

          {/* Loading State */}
          {loading && (
            <div className="flex items-center justify-center p-16 bg-white rounded-2xl border border-gray-200 shadow-sm">
              <div className="text-center">
                <div className="w-16 h-16 rounded-full bg-teal-50 flex items-center justify-center mx-auto mb-4">
                  <Loader2 className="h-8 w-8 animate-spin text-teal-600" />
                </div>
                <p className="text-gray-600 font-medium">Loading data from API...</p>
                <p className="text-gray-400 text-sm mt-1">This may take a moment</p>
              </div>
            </div>
          )}

          {/* Home Page */}
          {!loading && activeScreen === 'home' && (
            <HomePage />
          )}

          {/* Dashboard Table */}
          {!loading && activeScreen === 'dashboard' && (
            <DataTable
              tableKey="dashboard"
              config={tableConfig.dashboard}
              onSave={handleSave}
            />
          )}

          {/* Users Table */}
          {!loading && activeScreen === 'users' && (
            <DataTable
              tableKey="users"
              config={tableConfig.users}
              onSave={handleSave}
            />
          )}
        </div>
      </div>

      {/* Toast */}
      <Toaster position="bottom-right" richColors closeButton />
    </div>
  );
}

export default App;


#src/index.css 
/* Google Fonts - must be first */
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

@import "tailwindcss";

@layer base {
  :root {
    /* Typography */
    --font-sans: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
    --font-mono: 'IBM Plex Mono', 'Menlo', monospace;

    /* Verdant SaaS Color Palette */
    --background: 250 250 250;
    --foreground: 15 23 42;

    --card: 255 255 255;
    --card-foreground: 15 23 42;

    --popover: 255 255 255;
    --popover-foreground: 15 23 42;

    /* Teal Primary */
    --primary: 13 148 136;
    --primary-foreground: 255 255 255;
    --primary-hover: 15 118 110;
    --primary-light: 204 251 241;
    --primary-glow: 13 148 136;

    --secondary: 241 245 249;
    --secondary-foreground: 51 65 85;

    --muted: 241 245 249;
    --muted-foreground: 100 116 139;

    --accent: 240 253 244;
    --accent-foreground: 15 23 42;

    --destructive: 239 68 68;
    --destructive-foreground: 255 255 255;

    --success: 16 185 129;
    --success-foreground: 255 255 255;

    --warning: 245 158 11;
    --warning-foreground: 255 255 255;

    --border: 229 231 235;
    --border-accent: 209 250 229;
    --input: 229 231 235;
    --ring: 13 148 136;

    --radius: 0.75rem;
    --radius-sm: 0.5rem;
    --radius-lg: 1rem;
  }

  * {
    border-color: rgb(var(--border));
  }

  body {
    margin: 0;
    min-height: 100vh;
    font-family: var(--font-sans);
    background-color: rgb(var(--background));
    color: rgb(var(--foreground));
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    line-height: 1.6;
  }

  /* Custom selection color */
  ::selection {
    background-color: rgb(var(--primary-light));
    color: rgb(var(--foreground));
  }
}

@layer utilities {
  /* Glass effect cards */
  .glass-card {
    background: rgba(255, 255, 255, 0.95);
    backdrop-filter: blur(10px);
    border: 1px solid rgb(var(--border));
    box-shadow:
      0 1px 3px rgba(0, 0, 0, 0.04),
      0 4px 12px rgba(13, 148, 136, 0.06);
  }

  /* Teal glow shadow */
  .shadow-teal {
    box-shadow:
      0 4px 14px rgba(13, 148, 136, 0.12),
      0 1px 3px rgba(0, 0, 0, 0.04);
  }

  .shadow-teal-lg {
    box-shadow:
      0 8px 24px rgba(13, 148, 136, 0.15),
      0 2px 6px rgba(0, 0, 0, 0.04);
  }

  /* Hover lift effect */
  .hover-lift {
    transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1),
                box-shadow 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  }

  .hover-lift:hover {
    transform: translateY(-2px);
    box-shadow:
      0 8px 24px rgba(13, 148, 136, 0.15),
      0 2px 6px rgba(0, 0, 0, 0.04);
  }

  /* Gradient backgrounds */
  .bg-gradient-teal {
    background: linear-gradient(135deg, rgb(var(--primary)) 0%, rgb(16, 185, 129) 100%);
  }

  .bg-gradient-subtle {
    background: linear-gradient(180deg, rgba(240, 253, 244, 0.5) 0%, rgba(255, 255, 255, 0) 100%);
  }

  /* Dot grid pattern */
  .bg-dot-pattern {
    background-image: radial-gradient(circle, rgb(var(--border)) 1px, transparent 1px);
    background-size: 24px 24px;
  }

  /* Monospace font for data */
  .font-mono {
    font-family: var(--font-mono);
  }

  /* Text gradient */
  .text-gradient-teal {
    background: linear-gradient(135deg, rgb(var(--primary)) 0%, rgb(16, 185, 129) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  /* Custom scrollbar */
  .custom-scrollbar::-webkit-scrollbar {
    width: 8px;
    height: 8px;
  }

  .custom-scrollbar::-webkit-scrollbar-track {
    background: rgb(var(--muted));
    border-radius: 4px;
  }

  .custom-scrollbar::-webkit-scrollbar-thumb {
    background: rgb(var(--primary) / 0.3);
    border-radius: 4px;
    transition: background 0.2s;
  }

  .custom-scrollbar::-webkit-scrollbar-thumb:hover {
    background: rgb(var(--primary) / 0.5);
  }

  /* Firefox scrollbar */
  .custom-scrollbar {
    scrollbar-width: thin;
    scrollbar-color: rgb(var(--primary) / 0.3) rgb(var(--muted));
  }
}

/* Animations */
@keyframes fade-in {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

@keyframes slide-up {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes slide-in-right {
  from {
    opacity: 0;
    transform: translateX(100%);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

@keyframes slide-out-right {
  from {
    opacity: 1;
    transform: translateX(0);
  }
  to {
    opacity: 0;
    transform: translateX(100%);
  }
}

@keyframes scale-in {
  from {
    opacity: 0;
    transform: scale(0.95);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

@keyframes pulse-teal {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(13, 148, 136, 0.4);
  }
  50% {
    box-shadow: 0 0 0 8px rgba(13, 148, 136, 0);
  }
}

@keyframes shimmer {
  0% {
    background-position: -200% 0;
  }
  100% {
    background-position: 200% 0;
  }
}

/* Animation utilities */
.animate-fade-in {
  animation: fade-in 0.3s ease-out forwards;
}

.animate-slide-up {
  animation: slide-up 0.4s cubic-bezier(0.4, 0, 0.2, 1) forwards;
}

.animate-slide-in-right {
  animation: slide-in-right 0.3s cubic-bezier(0.4, 0, 0.2, 1) forwards;
}

.animate-slide-out-right {
  animation: slide-out-right 0.2s cubic-bezier(0.4, 0, 0.2, 1) forwards;
}

.animate-scale-in {
  animation: scale-in 0.2s cubic-bezier(0.4, 0, 0.2, 1) forwards;
}

.animate-pulse-teal {
  animation: pulse-teal 2s infinite;
}

/* Staggered animations */
.stagger-1 { animation-delay: 0.05s; }
.stagger-2 { animation-delay: 0.1s; }
.stagger-3 { animation-delay: 0.15s; }
.stagger-4 { animation-delay: 0.2s; }
.stagger-5 { animation-delay: 0.25s; }
.stagger-6 { animation-delay: 0.3s; }

/* Loading skeleton */
.skeleton {
  background: linear-gradient(
    90deg,
    rgb(var(--muted)) 25%,
    rgb(var(--muted) / 0.5) 50%,
    rgb(var(--muted)) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

/* Focus ring */
.focus-ring {
  outline: none;
}

.focus-ring:focus-visible {
  outline: 2px solid rgb(var(--primary));
  outline-offset: 2px;
}

/* Transition utilities */
.transition-all-200 {
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.transition-colors-200 {
  transition: color 0.2s, background-color 0.2s, border-color 0.2s;
}

#src/main.tsx 
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

#package.json 
{
    "name": "shacnui",
    "private": true,
    "version": "0.0.0",
    "type": "module",
    "scripts": {
      "dev": "vite",
      "build": "tsc -b && vite build",
      "lint": "eslint .",
      "preview": "vite preview"
    },
    "dependencies": {
      "@radix-ui/react-select": "^2.2.6",
      "@radix-ui/react-slot": "^1.2.4",
      "@tailwindcss/vite": "^4.1.17",
      "@tanstack/react-table": "^8.21.3",
      "@tanstack/react-virtual": "^3.13.12",
      "class-variance-authority": "^0.7.1",
      "clsx": "^2.1.1",
      "lucide-react": "^0.553.0",
      "react": "^19.2.0",
      "react-dom": "^19.2.0",
      "sonner": "^2.0.7",
      "tailwind-merge": "^3.4.0"
    },
    "devDependencies": {
      "@eslint/js": "^9.39.1",
      "@types/node": "^24.10.0",
      "@types/react": "^19.2.2",
      "@types/react-dom": "^19.2.2",
      "@vitejs/plugin-react": "^5.1.0",
      "autoprefixer": "^10.4.22",
      "eslint": "^9.39.1",
      "eslint-plugin-react-hooks": "^7.0.1",
      "eslint-plugin-react-refresh": "^0.4.24",
      "globals": "^16.5.0",
      "postcss": "^8.5.6",
      "tailwindcss": "^4.1.17",
      "tw-animate-css": "^1.4.0",
      "typescript": "~5.9.3",
      "typescript-eslint": "^8.46.3",
      "vite": "^7.2.2"
    }
  }

#eslint.config.js 

import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
  },
])

#package.json: 
{
    "name": "shacnui",
    "private": true,
    "version": "0.0.0",
    "type": "module",
    "scripts": {
      "dev": "vite",
      "build": "tsc -b && vite build",
      "lint": "eslint .",
      "preview": "vite preview"
    },
    "dependencies": {
      "@radix-ui/react-select": "^2.2.6",
      "@radix-ui/react-slot": "^1.2.4",
      "@tailwindcss/vite": "^4.1.17",
      "@tanstack/react-table": "^8.21.3",
      "@tanstack/react-virtual": "^3.13.12",
      "class-variance-authority": "^0.7.1",
      "clsx": "^2.1.1",
      "lucide-react": "^0.553.0",
      "react": "^19.2.0",
      "react-dom": "^19.2.0",
      "sonner": "^2.0.7",
      "tailwind-merge": "^3.4.0"
    },
    "devDependencies": {
      "@eslint/js": "^9.39.1",
      "@types/node": "^24.10.0",
      "@types/react": "^19.2.2",
      "@types/react-dom": "^19.2.2",
      "@vitejs/plugin-react": "^5.1.0",
      "autoprefixer": "^10.4.22",
      "eslint": "^9.39.1",
      "eslint-plugin-react-hooks": "^7.0.1",
      "eslint-plugin-react-refresh": "^0.4.24",
      "globals": "^16.5.0",
      "postcss": "^8.5.6",
      "tailwindcss": "^4.1.17",
      "tw-animate-css": "^1.4.0",
      "typescript": "~5.9.3",
      "typescript-eslint": "^8.46.3",
      "vite": "^7.2.2"
    }
  }

#index.html 
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>shacnui</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>

#tsconfig.app.json 
{
    "compilerOptions": {
      
      "tsBuildInfoFile": "./node_modules/.tmp/tsconfig.app.tsbuildinfo",
      "target": "ES2022",
      "useDefineForClassFields": true,
      "lib": ["ES2022", "DOM", "DOM.Iterable"],
      "module": "ESNext",
      "types": ["vite/client"],
      "skipLibCheck": true,
      "baseUrl": ".",
      "paths": {
        "@/*": [
          "./src/*"
        ]
      },
      /* Bundler mode */
      "moduleResolution": "bundler",
      "allowImportingTsExtensions": true,
      "verbatimModuleSyntax": true,
      "moduleDetection": "force",
      "noEmit": true,
      "jsx": "react-jsx",
  
      /* Linting */
      "strict": true,
      "noUnusedLocals": true,
      "noUnusedParameters": true,
      "erasableSyntaxOnly": true,
      "noFallthroughCasesInSwitch": true,
      "noUncheckedSideEffectImports": true
    },
    "include": ["src"]
  }

#tsconfig.json 
{
    "files": [],
    "references": [
      { "path": "./tsconfig.app.json" },
      { "path": "./tsconfig.node.json" }
    ],
    "compilerOptions": {
      "baseUrl": ".",
      "paths": {
        "@/*": ["./src/*"]
      }
    }
  }

#tsconfig.node.json
{
    "compilerOptions": {
      "tsBuildInfoFile": "./node_modules/.tmp/tsconfig.node.tsbuildinfo",
      "target": "ES2023",
      "lib": ["ES2023"],
      "module": "ESNext",
      "types": ["node"],
      "skipLibCheck": true,
  
      /* Bundler mode */
      "moduleResolution": "bundler",
      "allowImportingTsExtensions": true,
      "verbatimModuleSyntax": true,
      "moduleDetection": "force",
      "noEmit": true,
  
      /* Linting */
      "strict": true,
      "noUnusedLocals": true,
      "noUnusedParameters": true,
      "erasableSyntaxOnly": true,
      "noFallthroughCasesInSwitch": true,
      "noUncheckedSideEffectImports": true
    },
    "include": ["vite.config.ts"]
  }

  #vite.config.ts 
  import { defineConfig } from 'vite'
import path from "path"
import tailwindcss from "@tailwindcss/vite"
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
})
