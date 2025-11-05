import React, { useState, useEffect, useMemo } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  flexRender,
  createColumnHelper,
} from '@tanstack/react-table';
import { Button, Input, Select, Radio, Space } from 'antd';
import { LayoutDashboard, Users, Settings, Filter, Download, X, Upload, Check, Loader2, Save, ArrowUpDown, Eye, EyeOff } from 'lucide-react';
import { dataService, mockDataService } from './services/api';
import 'antd/dist/reset.css';
import './App.css';
import axios from 'axios';

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: process.env.REACT_APP_API_BASE_URL || 'https://api.example.com',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor - add auth token, etc.
apiClient.interceptors.request.use(
  (config) => {
    // Add authorization token if available
    const token = localStorage.getItem('authToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor - handle errors globally
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    // Handle common errors
    if (error.response?.status === 401) {
      // Unauthorized - redirect to login
      console.error('Unauthorized access - please login');
      // window.location.href = '/login';
    } else if (error.response?.status === 500) {
      console.error('Server error:', error.response.data);
    }
    return Promise.reject(error);
  }
);

// API Service functions
export const dataService = {
  // Fetch table data with schema
  fetchTableData: async (tableKey: string) => {
    const response = await apiClient.get(`/tables/${tableKey}`);
    return response.data;
  },

  // Save modified rows
  saveTableData: async (tableKey: string, modifiedRows: any[]) => {
    const response = await apiClient.post(`/tables/${tableKey}/save`, {
      modifiedRows,
      totalRows: modifiedRows.length,
    });
    return response.data;
  },

  // Export table data
  exportTableData: async (tableKey: string, filters: any, exportOption: string) => {
    const response = await apiClient.post(
      `/tables/${tableKey}/export`,
      { filters, option: exportOption },
      { responseType: 'blob' } // Important for file downloads
    );
    return response.data;
  },
};

// Mock API responses (for development/testing)
export const mockDataService = {
  dashboard: async () => {
    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 800));

    return {
      schema: {
        columns: [
          { name: 'id', label: 'ID', type: 'text', editable: false, visible: true },
          { name: 'name', label: 'Full Name', type: 'text', editable: true, visible: true },
          { name: 'status', label: 'Status', type: 'select', editable: true, options: ['Active', 'Inactive', 'Pending'], visible: true },
          { name: 'department', label: 'Department', type: 'select', editable: true, options: ['Sales', 'Marketing', 'IT', 'HR', 'Finance', 'Operations', 'Legal'], visible: true },
          { name: 'salary', label: 'Salary', type: 'text', editable: true, visible: true },
          { name: 'hireDate', label: 'Hire Date', type: 'text', editable: true, visible: false },
          { name: 'location', label: 'Office Location', type: 'select', editable: true, options: ['New York', 'San Francisco', 'London', 'Tokyo', 'Remote'], visible: true },
          { name: 'manager', label: 'Manager', type: 'text', editable: true, visible: false },
          { name: 'phone', label: 'Phone', type: 'text', editable: true, visible: false },
          { name: 'employeeType', label: 'Employment Type', type: 'select', editable: true, options: ['Full-Time', 'Part-Time', 'Contract', 'Intern'], visible: true }
        ]
      },
      data: Array.from({ length: 40 }, (_, i) => ({
        id: i + 1,
        name: `Employee ${i + 1}`,
        status: ['Active', 'Inactive', 'Pending'][i % 3],
        department: ['Sales', 'Marketing', 'IT', 'HR', 'Finance'][i % 5],
        salary: `${50000 + i * 1000}`,
        hireDate: `2020-0${(i % 9) + 1}-15`,
        location: ['New York', 'San Francisco', 'London', 'Tokyo', 'Remote'][i % 5],
        manager: `Manager ${(i % 10) + 1}`,
        phone: `555-01${String(i).padStart(2, '0')}`,
        employeeType: ['Full-Time', 'Part-Time', 'Contract', 'Intern'][i % 4]
      }))
    };
  },

  users: async () => {
    await new Promise(resolve => setTimeout(resolve, 800));

    return {
      schema: {
        columns: [
          { name: 'id', label: 'ID', type: 'text', editable: false, visible: true },
          { name: 'username', label: 'Username', type: 'text', editable: true, visible: true },
          { name: 'email', label: 'Email Address', type: 'text', editable: true, visible: true },
          { name: 'role', label: 'Role', type: 'select', editable: true, options: ['Admin', 'Manager', 'User', 'Guest'], visible: true },
          { name: 'active', label: 'Active', type: 'select', editable: true, options: ['Yes', 'No'], visible: true },
          { name: 'lastLogin', label: 'Last Login', type: 'text', editable: true, visible: false },
          { name: 'accountType', label: 'Account Type', type: 'select', editable: true, options: ['Premium', 'Standard', 'Trial', 'Enterprise'], visible: true },
          { name: 'createdDate', label: 'Created Date', type: 'text', editable: true, visible: false },
          { name: 'department', label: 'Department', type: 'select', editable: true, options: ['Engineering', 'Sales', 'Marketing', 'Support', 'Admin'], visible: true },
          { name: 'country', label: 'Country', type: 'select', editable: true, options: ['USA', 'UK', 'Canada', 'Germany', 'Japan', 'Australia'], visible: false }
        ]
      },
      data: Array.from({ length: 35 }, (_, i) => ({
        id: i + 1,
        username: `user${i + 1}`,
        email: `user${i + 1}@example.com`,
        role: ['Admin', 'Manager', 'User', 'Guest'][i % 4],
        active: i % 5 === 0 ? 'No' : 'Yes',
        lastLogin: `2024-01-${String((i % 28) + 1).padStart(2, '0')}`,
        accountType: ['Premium', 'Standard', 'Trial', 'Enterprise'][i % 4],
        createdDate: `202${i % 4}-0${(i % 9) + 1}-15`,
        department: ['Engineering', 'Sales', 'Marketing', 'Support', 'Admin'][i % 5],
        country: ['USA', 'UK', 'Canada', 'Germany', 'Japan', 'Australia'][i % 6]
      }))
    };
  }
};

export default apiClient;

// Toggle between mock and real API
const USE_MOCK_API = true; // Set to false to use real API

const DataTable = ({ tableKey, config, onDataChange, onSave }) => {
  const [data, setData] = useState(config?.data || []);
  const [originalData, setOriginalData] = useState(config?.data || []);
  const [modifiedRowIndices, setModifiedRowIndices] = useState(new Set());
  const [columnVisibility, setColumnVisibility] = useState({});
  const [columnFilters, setColumnFilters] = useState([]);
  const [sorting, setSorting] = useState([]);
  const [showColumnSelector, setShowColumnSelector] = useState(false);
  const [exportOption, setExportOption] = useState('all');
  const [loading, setLoading] = useState(false);
  const [dragStart, setDragStart] = useState(null);
  const [dragEnd, setDragEnd] = useState(null);
  const [isDragging, setIsDragging] = useState(false);

  const isLocalUpdate = React.useRef(false);

  useEffect(() => {
    if (config?.data && config?.schema?.columns) {
      // Don't reset if this update came from our own local edits
      if (!isLocalUpdate.current) {
        setData(config.data);
        setOriginalData(JSON.parse(JSON.stringify(config.data))); // Deep copy
        setModifiedRowIndices(new Set()); // Reset modified rows
      }

      // Reset the flag
      isLocalUpdate.current = false;

      // Set initial visibility from schema
      const initialVisibility = {};
      config.schema.columns.forEach(col => {
        if (col.visible === false) {
          initialVisibility[col.name] = false;
        }
      });
      setColumnVisibility(initialVisibility);
    }
  }, [config]);

  const updateData = (rowIndex, columnId, value) => {
    const newData = data.map((row, index) => {
      if (index === rowIndex) {
        return { ...row, [columnId]: value };
      }
      return row;
    });

    // Mark this as a local update so useEffect doesn't reset our tracking
    isLocalUpdate.current = true;

    setData(newData);
    onDataChange(tableKey, newData);

    // Track modified row
    setModifiedRowIndices(prev => new Set(prev).add(rowIndex));
  };

  const handleDragStart = (e, rowIndex, columnId, value) => {
    e.preventDefault();
    e.stopPropagation();
    setDragStart({ rowIndex, columnId, value });
    setDragEnd({ rowIndex, columnId });
    setIsDragging(true);
    document.body.classList.add('dragging');
  };


  const handleDragEnd = React.useCallback(() => {
    if (dragStart && dragEnd && dragStart.columnId === dragEnd.columnId) {
      const startRow = Math.min(dragStart.rowIndex, dragEnd.rowIndex);
      const endRow = Math.max(dragStart.rowIndex, dragEnd.rowIndex);
      const columnId = dragStart.columnId;
      const fillValue = dragStart.value;

      // Only fill if we dragged to at least one other cell
      if (startRow !== endRow || dragStart.rowIndex !== dragEnd.rowIndex) {
        const newData = data.map((row, index) => {
          if (index >= startRow && index <= endRow) {
            return { ...row, [columnId]: fillValue };
          }
          return row;
        });

        // Mark this as a local update so useEffect doesn't reset our tracking
        isLocalUpdate.current = true;

        setData(newData);
        onDataChange(tableKey, newData);

        // Track all modified rows from drag operation
        setModifiedRowIndices(prev => {
          const newSet = new Set(prev);
          for (let i = startRow; i <= endRow; i++) {
            newSet.add(i);
          }
          return newSet;
        });
      }
    }

    setDragStart(null);
    setDragEnd(null);
    setIsDragging(false);
    document.body.classList.remove('dragging');
  }, [dragStart, dragEnd, data, onDataChange, tableKey]);

  useEffect(() => {
    const handleGlobalMouseUp = () => {
      if (isDragging) {
        handleDragEnd();
      }
    };

    const handleGlobalMouseMove = (e) => {
      if (!isDragging || !dragStart) return;

      // Find the cell element under the mouse
      const element = document.elementFromPoint(e.clientX, e.clientY);
      const cellElement = element?.closest('td');

      if (cellElement) {
        const rowIndex = parseInt(cellElement.getAttribute('data-row-index'));
        const columnId = cellElement.getAttribute('data-column-id');

        if (!isNaN(rowIndex) && columnId === dragStart.columnId) {
          setDragEnd({ rowIndex, columnId });
        }
      }
    };

    if (isDragging) {
      document.addEventListener('mousemove', handleGlobalMouseMove);
    }
    document.addEventListener('mouseup', handleGlobalMouseUp);

    return () => {
      document.removeEventListener('mousemove', handleGlobalMouseMove);
      document.removeEventListener('mouseup', handleGlobalMouseUp);
    };
  }, [isDragging, dragStart, handleDragEnd]);

  const columns = useMemo(() => {
    if (!config?.schema?.columns) return [];

    return config.schema.columns.map(col => {
      const columnDef = {
        accessorKey: col.name,
        header: ({ column }) => (
          <div className="flex items-center gap-2">
            <span className="font-semibold">{col.label}</span>
            {col.editable && (
              <Button
                type="text"
                size="small"
                icon={<ArrowUpDown style={{ width: 12, height: 12 }} />}
                onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
              />
            )}
          </div>
        ),
        cell: ({ row, column }) => {
          const value = row.getValue(column.id);
          const isInDragRange = isDragging && dragStart && dragEnd &&
            dragStart.columnId === column.id &&
            dragEnd.columnId === column.id &&
            row.index >= Math.min(dragStart.rowIndex, dragEnd.rowIndex) &&
            row.index <= Math.max(dragStart.rowIndex, dragEnd.rowIndex);

          if (!col.editable) {
            return <div className="px-2 py-1">{value}</div>;
          }

          if (col.type === 'select') {
            return (
              <div className={`relative group ${isInDragRange ? 'bg-blue-100' : ''}`}>
                <Select
                  value={value}
                  onChange={(newValue) => updateData(row.index, column.id, newValue)}
                  variant="borderless"
                  size="small"
                  style={{ width: '100%' }}
                  options={col.options?.map(option => ({ label: option, value: option }))}
                />
                <div
                  className="drag-handle"
                  onMouseDown={(e) => handleDragStart(e, row.index, column.id, value)}
                />
              </div>
            );
          }

          return (
            <div className={`relative group ${isInDragRange ? 'bg-blue-100' : ''}`}>
              <Input
                value={value}
                onChange={(e) => updateData(row.index, column.id, e.target.value)}
                variant="borderless"
                size="small"
              />
              <div
                className="drag-handle"
                onMouseDown={(e) => handleDragStart(e, row.index, column.id, value)}
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
    },
    onColumnVisibilityChange: setColumnVisibility,
    onColumnFiltersChange: setColumnFilters,
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  const getModifiedRows = () => {
    const modifiedRows = [];
    modifiedRowIndices.forEach(index => {
      if (data[index]) {
        modifiedRows.push(data[index]);
      }
    });
    return modifiedRows;
  };

  const handleSaveData = async () => {
    const modifiedRows = getModifiedRows();

    if (modifiedRows.length === 0) {
      alert('No changes to save!');
      return;
    }

    await onSave(tableKey, modifiedRows);

    // After successful save, update original data and clear modified rows
    setOriginalData(JSON.parse(JSON.stringify(data)));
    setModifiedRowIndices(new Set());
  };

  const handleExport = async () => {
    setLoading(true);
    try {
      if (USE_MOCK_API) {
        // Mock export - just log the data
        await new Promise(resolve => setTimeout(resolve, 500));
        console.log('Mock export - Data:', data);
        console.log('Export option:', exportOption);
        console.log('Filters:', columnFilters);
        alert('Export simulation - check console for data');
      } else {
        // Real API export with axios
        const blob = await dataService.exportTableData(tableKey, columnFilters, exportOption);

        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${tableKey}_export_${Date.now()}.xlsx`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        alert('Export successful!');
      }
    } catch (error: any) {
      console.error('Export error:', error);
      alert(`Export error: ${error.message}`);
    } finally {
      setLoading(false);
    }
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
      {/* Controls */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Filter className="h-4 w-4 text-gray-500" />
          <span className="text-sm text-gray-600">Use filters below columns</span>
        </div>
        <div className="flex gap-2 items-center">
          <div className="relative">
            <Button
              onClick={() => setShowColumnSelector(!showColumnSelector)}
              icon={<Eye style={{ width: 16, height: 16 }} />}
            >
              Columns ({visibleCount}/{totalCount})
            </Button>
            
            {showColumnSelector && (
              <div className="absolute right-0 top-full mt-2 bg-white border-2 border-blue-200 rounded-lg shadow-2xl p-4 z-20 min-w-[280px]">
                <div className="flex items-center justify-between mb-3 pb-3 border-b-2">
                  <span className="font-bold">Toggle Columns</span>
                  <button onClick={() => setShowColumnSelector(false)}>
                    <X className="h-5 w-5" />
                  </button>
                </div>
                <div className="space-y-2 max-h-[400px] overflow-y-auto">
                  {table.getAllLeafColumns().map(column => {
                    const colConfig = config.schema.columns.find(c => c.name === column.id);
                    return (
                      <label key={column.id} className="flex items-center gap-3 p-2 hover:bg-blue-50 rounded cursor-pointer">
                        <input
                          type="checkbox"
                          checked={column.getIsVisible()}
                          onChange={column.getToggleVisibilityHandler()}
                          className="w-5 h-5 rounded"
                        />
                        <span className="text-sm font-medium">{colConfig?.label || column.id}</span>
                        {colConfig?.visible === false && (
                          <span className="text-xs text-orange-600 bg-orange-50 px-2 py-0.5 rounded">
                            Hidden by default
                          </span>
                        )}
                      </label>
                    );
                  })}
                </div>
                <div className="mt-3 pt-3 border-t flex justify-between items-center">
                  <span className="text-sm text-gray-600">{visibleCount}/{totalCount} visible</span>
                  <Button size="small" onClick={() => setShowColumnSelector(false)}>Done</Button>
                </div>
              </div>
            )}
          </div>
          <Button
            onClick={handleSaveData}
            type="primary"
            icon={<Save style={{ width: 16, height: 16 }} />}
          >
            Save {modifiedRowIndices.size > 0 && `(${modifiedRowIndices.size})`}
          </Button>
        </div>
      </div>

      {/* Table */}
      <div className="border rounded-lg bg-white overflow-hidden">
        <div className="overflow-x-auto overflow-y-auto max-h-[600px]">
          <table className="w-full">
            <thead className="bg-gray-50 border-b sticky top-0 z-10">
              {table.getHeaderGroups().map(headerGroup => (
                <React.Fragment key={headerGroup.id}>
                  <tr>
                    {headerGroup.headers.map(header => (
                      <th key={header.id} className="px-4 py-3 text-left bg-gray-50 min-w-[150px] whitespace-nowrap">
                        {flexRender(header.column.columnDef.header, header.getContext())}
                      </th>
                    ))}
                  </tr>
                  <tr>
                    {headerGroup.headers.map(header => {
                      const colConfig = config.schema.columns.find(c => c.name === header.column.id);
                      return (
                        <th key={header.id} className="px-4 py-2 bg-gray-50">
                          {colConfig?.editable && colConfig.type === 'select' ? (
                            <Select
                              value={(header.column.getFilterValue() ?? '') as string}
                              onChange={(value) => header.column.setFilterValue(value || undefined)}
                              size="small"
                              placeholder="All"
                              allowClear
                              style={{ width: '100%' }}
                              options={[
                                ...(colConfig.options?.map(option => ({ label: option, value: option })) || [])
                              ]}
                            />
                          ) : colConfig?.editable ? (
                            <Input
                              placeholder="Filter..."
                              value={(header.column.getFilterValue() ?? '') as string}
                              onChange={(e) => header.column.setFilterValue(e.target.value)}
                              size="small"
                            />
                          ) : null}
                        </th>
                      );
                    })}
                  </tr>
                </React.Fragment>
              ))}
            </thead>
            <tbody className="divide-y divide-gray-200">
              {table.getRowModel().rows.map(row => (
                <tr key={row.id} className="hover:bg-gray-50">
                  {row.getVisibleCells().map(cell => (
                    <td
                      key={cell.id}
                      className="px-4 py-2"
                      data-row-index={row.index}
                      data-column-id={cell.column.id}
                    >
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
            <Radio.Group
              onChange={(e) => setExportOption(e.target.value)}
              value={exportOption}
              style={{ width: '100%' }}
            >
              <Space direction="vertical" style={{ width: '100%' }}>
                {['all', 'filtered', 'selected'].map(option => (
                  <Radio key={option} value={option} style={{ width: '100%' }}>
                    <div>
                      <div className="text-sm font-medium">
                        Export {option.charAt(0).toUpperCase() + option.slice(1)} Data
                      </div>
                      <p className="text-xs text-gray-500">
                        {option === 'all' && `Download all ${data.length} records`}
                        {option === 'filtered' && `Download ${table.getRowModel().rows.length} filtered records`}
                        {option === 'selected' && 'Choose specific columns to export'}
                      </p>
                    </div>
                  </Radio>
                ))}
              </Space>
            </Radio.Group>
            <Button
              onClick={handleExport}
              type="primary"
              block
              size="large"
              icon={loading ? <Loader2 style={{ width: 20, height: 20 }} className="animate-spin" /> : <Download style={{ width: 20, height: 20 }} />}
              loading={loading}
            >
              {loading ? 'Exporting...' : 'Export to Excel'}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
};

const App = () => {
  const [activeScreen, setActiveScreen] = useState('dashboard');
  const [selectedDataSources, setSelectedDataSources] = useState(['dashboard', 'users']);
  const [showDataSourceDropdown, setShowDataSourceDropdown] = useState(false);
  const [loading, setLoading] = useState(false);
  const [tableConfig, setTableConfig] = useState({
    dashboard: { schema: null, data: [] },
    users: { schema: null, data: [] }
  });

  const dataSources = [
    { id: 'dashboard', label: 'Dashboard Data' },
    { id: 'users', label: 'Users Data' },
    { id: 'external', label: 'External API' }
  ];

  const menuItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'users', label: 'Users', icon: Users },
    { id: 'settings', label: 'Settings', icon: Settings }
  ];

  const loadDataFromAPI = async (sources) => {
    setLoading(true);
    const newConfig = { ...tableConfig };

    try {
      for (const source of sources) {
        let response;

        if (USE_MOCK_API) {
          // Use mock data
          if (mockDataService[source]) {
            response = await mockDataService[source]();
          }
        } else {
          // Use real API with axios
          response = await dataService.fetchTableData(source);
        }

        if (response) {
          newConfig[source] = response;
        }
      }
      setTableConfig(newConfig);
      alert(`Successfully loaded data from: ${sources.join(', ')}`);
    } catch (error: any) {
      console.error('Error loading data:', error);
      alert(`Error loading data: ${error.message}`);
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

  const handleSave = async (tableKey, modifiedRows) => {
    setLoading(true);
    try {
      if (USE_MOCK_API) {
        // Mock save - just log the data
        await new Promise(resolve => setTimeout(resolve, 500));
        console.log('Mock save - Modified rows:', modifiedRows);
      } else {
        // Real API save with axios
        await dataService.saveTableData(tableKey, modifiedRows);
      }

      alert(`Successfully saved ${modifiedRows.length} modified row(s)!`);
      console.log('Saved modified rows:', modifiedRows);
    } catch (error: any) {
      console.error('Save error:', error);
      alert(`Error saving data: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const toggleDataSource = (source) => {
    setSelectedDataSources(prev => 
      prev.includes(source) ? prev.filter(s => s !== source) : [...prev, source]
    );
  };

  useEffect(() => {
    loadDataFromAPI(['dashboard', 'users']);
  }, []);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (showDataSourceDropdown && !event.target.closest('.data-source-dropdown')) {
        setShowDataSourceDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showDataSourceDropdown]);

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <div className="w-64 bg-white border-r border-gray-200 flex flex-col">
        <div className="p-6 border-b border-gray-200">
          <h1 className="text-xl font-bold text-gray-900">Data Manager</h1>
        </div>
        
        <nav className="flex-1 p-4">
          <ul className="space-y-2">
            {menuItems.map((item) => {
              const Icon = item.icon;
              return (
                <li key={item.id}>
                  <button
                    onClick={() => setActiveScreen(item.id)}
                    className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                      activeScreen === item.id
                        ? 'bg-blue-50 text-blue-600'
                        : 'text-gray-700 hover:bg-gray-50'
                    }`}
                  >
                    <Icon className="h-5 w-5" />
                    <span className="font-medium">{item.label}</span>
                  </button>
                </li>
              );
            })}
          </ul>
        </nav>

        <div className="p-4 border-t border-gray-200 space-y-3">
          <div className="relative data-source-dropdown">
            <button
              onClick={() => setShowDataSourceDropdown(!showDataSourceDropdown)}
              className="w-full flex items-center justify-between px-4 py-2 border border-gray-300 rounded-lg text-sm hover:bg-gray-50"
            >
              <span className="text-gray-700">{selectedDataSources.length} source(s) selected</span>
              <Filter className="h-4 w-4 text-gray-500" />
            </button>
            
            {showDataSourceDropdown && (
              <div className="absolute bottom-full left-0 right-0 mb-2 bg-white border border-gray-200 rounded-lg shadow-lg p-2 z-10">
                {dataSources.map((source) => (
                  <button
                    key={source.id}
                    onClick={() => toggleDataSource(source.id)}
                    className="w-full flex items-center justify-between px-3 py-2 text-sm hover:bg-gray-50 rounded"
                  >
                    <span className="text-gray-700">{source.label}</span>
                    {selectedDataSources.includes(source.id) && (
                      <Check className="h-4 w-4 text-blue-600" />
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>

          <Button
            onClick={() => loadDataFromAPI(selectedDataSources)}
            disabled={loading}
            type="primary"
            block
            icon={loading ? <Loader2 style={{ width: 16, height: 16 }} className="animate-spin" /> : <Upload style={{ width: 16, height: 16 }} />}
            loading={loading}
          >
            {loading ? 'Loading...' : 'Load Data'}
          </Button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-auto">
        <div className="p-8">
          <div className="mb-6">
            <h2 className="text-2xl font-bold text-gray-900">
              {activeScreen === 'dashboard' && 'Dashboard'}
              {activeScreen === 'users' && 'Users Management'}
              {activeScreen === 'settings' && 'Settings'}
            </h2>
            <p className="text-gray-500 mt-1">
              {activeScreen === 'dashboard' && 'Powered by TanStack Table - Column visibility, filtering, sorting'}
              {activeScreen === 'users' && 'Advanced table features with export capabilities'}
              {activeScreen === 'settings' && 'Configure application settings'}
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
          
          {!loading && activeScreen === 'settings' && (
            <div className="border rounded-lg bg-white p-6">
              <h3 className="text-lg font-semibold mb-4">Application Settings</h3>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-2">API Endpoint</label>
                  <Input
                    placeholder="https://api.example.com"
                    defaultValue="https://api.example.com"
                    style={{ maxWidth: 400 }}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">Theme</label>
                  <Select
                    defaultValue="light"
                    style={{ width: 256 }}
                    options={[
                      { label: 'Light', value: 'light' },
                      { label: 'Dark', value: 'dark' },
                      { label: 'Auto', value: 'auto' }
                    ]}
                  />
                </div>
                <Button type="primary" style={{ marginTop: 16 }}>Save Settings</Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default App;
