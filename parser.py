import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { LayoutDashboard, Users, Settings, Filter, Plus, Download } from 'lucide-react';

const ShadcnTableApp = () => {
  const [activeScreen, setActiveScreen] = useState('dashboard');
  const [dashboardData, setDashboardData] = useState([
    { id: 1, name: 'John Doe', status: 'Active', department: 'Sales', salary: '75000' },
    { id: 2, name: 'Jane Smith', status: 'Active', department: 'Marketing', salary: '68000' },
    { id: 3, name: 'Bob Johnson', status: 'Inactive', department: 'IT', salary: '82000' },
    { id: 4, name: 'Alice Williams', status: 'Active', department: 'HR', salary: '71000' },
    { id: 5, name: 'Charlie Brown', status: 'Active', department: 'Sales', salary: '79000' },
  ]);
  
  const [usersData, setUsersData] = useState([
    { id: 1, username: 'jdoe', email: 'john@example.com', role: 'Admin', active: 'Yes' },
    { id: 2, username: 'jsmith', email: 'jane@example.com', role: 'User', active: 'Yes' },
    { id: 3, username: 'bjohnson', email: 'bob@example.com', role: 'Manager', active: 'No' },
    { id: 4, username: 'awilliams', email: 'alice@example.com', role: 'User', active: 'Yes' },
    { id: 5, username: 'cbrown', email: 'charlie@example.com', role: 'Manager', active: 'Yes' },
  ]);

  const [filterText, setFilterText] = useState('');
  const [dragStart, setDragStart] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [draggedCells, setDraggedCells] = useState([]);

  const departments = ['Sales', 'Marketing', 'IT', 'HR', 'Finance'];
  const statuses = ['Active', 'Inactive', 'Pending'];
  const roles = ['Admin', 'Manager', 'User'];

  const handleCellChange = (dataType, rowId, field, value) => {
    if (dataType === 'dashboard') {
      setDashboardData(prev => 
        prev.map(row => row.id === rowId ? { ...row, [field]: value } : row)
      );
    } else {
      setUsersData(prev => 
        prev.map(row => row.id === rowId ? { ...row, [field]: value } : row)
      );
    }
  };

  const handleMouseDown = (rowId, field) => {
    setDragStart({ rowId, field });
    setIsDragging(true);
    setDraggedCells([rowId]);
  };

  const handleMouseUp = () => {
    setIsDragging(false);
    setDragStart(null);
    setDraggedCells([]);
  };

  const handleMouseEnter = (dataType, rowId, field) => {
    if (isDragging && dragStart && dragStart.field === field) {
      const data = dataType === 'dashboard' ? dashboardData : usersData;
      const setData = dataType === 'dashboard' ? setDashboardData : setUsersData;
      
      const startIndex = data.findIndex(row => row.id === dragStart.rowId);
      const endIndex = data.findIndex(row => row.id === rowId);
      
      if (startIndex !== -1 && endIndex !== -1) {
        const sourceValue = data[startIndex][field];
        const [minIndex, maxIndex] = startIndex < endIndex 
          ? [startIndex, endIndex] 
          : [endIndex, startIndex];
        
        // Track dragged cells for visual effect
        const cellsInRange = data.slice(minIndex, maxIndex + 1).map(row => row.id);
        setDraggedCells(cellsInRange);
        
        setData(prev => 
          prev.map((row, idx) => 
            idx >= minIndex && idx <= maxIndex 
              ? { ...row, [field]: sourceValue }
              : row
          )
        );
      }
    }
  };

  const filterData = (data) => {
    if (!filterText) return data;
    return data.filter(row => 
      Object.values(row).some(val => 
        String(val).toLowerCase().includes(filterText.toLowerCase())
      )
    );
  };

  const addNewRow = (dataType) => {
    if (dataType === 'dashboard') {
      const newId = Math.max(...dashboardData.map(r => r.id)) + 1;
      setDashboardData([...dashboardData, {
        id: newId,
        name: 'New Employee',
        status: 'Active',
        department: 'Sales',
        salary: '50000'
      }]);
    } else {
      const newId = Math.max(...usersData.map(r => r.id)) + 1;
      setUsersData([...usersData, {
        id: newId,
        username: 'newuser',
        email: 'new@example.com',
        role: 'User',
        active: 'Yes'
      }]);
    }
  };

  const exportData = (dataType) => {
    const data = dataType === 'dashboard' ? dashboardData : usersData;
    console.log('Exporting data:', data);
    alert('Data exported to console');
  };

  useEffect(() => {
    if (isDragging) {
      document.addEventListener('mouseup', handleMouseUp);
      return () => document.removeEventListener('mouseup', handleMouseUp);
    }
  }, [isDragging]);

  const renderDashboardTable = () => {
    const filteredData = filterData(dashboardData);
    
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4" />
            <Input
              placeholder="Filter data..."
              value={filterText}
              onChange={(e) => setFilterText(e.target.value)}
              className="w-64"
            />
          </div>
          <div className="flex gap-2">
            <Button onClick={() => addNewRow('dashboard')} className="gap-2">
              <Plus className="h-4 w-4" />
              Add Row
            </Button>
            <Button onClick={() => exportData('dashboard')} variant="outline" className="gap-2">
              <Download className="h-4 w-4" />
              Export
            </Button>
          </div>
        </div>

        <div className="border rounded-lg bg-white overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">ID</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Name</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Status</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Department</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Salary</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {filteredData.map((row) => (
                  <tr key={row.id} className="hover:bg-gray-50">
                    <td className="px-4 py-2 text-sm text-gray-900">{row.id}</td>
                    <td className="px-4 py-2 relative">
                      <div className="relative">
                        <Input
                          value={row.name}
                          onChange={(e) => handleCellChange('dashboard', row.id, 'name', e.target.value)}
                          onMouseEnter={() => handleMouseEnter('dashboard', row.id, 'name')}
                          className={`border-0 focus-visible:ring-1 h-8 ${
                            draggedCells.includes(row.id) && dragStart?.field === 'name'
                              ? 'bg-blue-100 border-2 border-blue-400'
                              : ''
                          }`}
                        />
                        <div
                          onMouseDown={() => handleMouseDown(row.id, 'name')}
                          className="absolute bottom-0 right-0 w-2 h-2 bg-blue-600 cursor-crosshair hover:w-3 hover:h-3 transition-all"
                          style={{ transform: 'translate(50%, 50%)' }}
                        />
                      </div>
                    </td>
                    <td className="px-4 py-2 relative">
                      <div className="relative">
                        <Select
                          value={row.status}
                          onValueChange={(value) => handleCellChange('dashboard', row.id, 'status', value)}
                        >
                          <SelectTrigger 
                            className={`border-0 focus:ring-1 h-8 ${
                              draggedCells.includes(row.id) && dragStart?.field === 'status'
                                ? 'bg-blue-100 border-2 border-blue-400'
                                : ''
                            }`}
                            onMouseEnter={() => handleMouseEnter('dashboard', row.id, 'status')}
                          >
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {statuses.map(status => (
                              <SelectItem key={status} value={status}>{status}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        <div
                          onMouseDown={() => handleMouseDown(row.id, 'status')}
                          className="absolute bottom-0 right-0 w-2 h-2 bg-blue-600 cursor-crosshair hover:w-3 hover:h-3 transition-all z-10"
                          style={{ transform: 'translate(50%, 50%)' }}
                        />
                      </div>
                    </td>
                    <td className="px-4 py-2 relative">
                      <div className="relative">
                        <Select
                          value={row.department}
                          onValueChange={(value) => handleCellChange('dashboard', row.id, 'department', value)}
                        >
                          <SelectTrigger 
                            className={`border-0 focus:ring-1 h-8 ${
                              draggedCells.includes(row.id) && dragStart?.field === 'department'
                                ? 'bg-blue-100 border-2 border-blue-400'
                                : ''
                            }`}
                            onMouseEnter={() => handleMouseEnter('dashboard', row.id, 'department')}
                          >
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {departments.map(dept => (
                              <SelectItem key={dept} value={dept}>{dept}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        <div
                          onMouseDown={() => handleMouseDown(row.id, 'department')}
                          className="absolute bottom-0 right-0 w-2 h-2 bg-blue-600 cursor-crosshair hover:w-3 hover:h-3 transition-all z-10"
                          style={{ transform: 'translate(50%, 50%)' }}
                        />
                      </div>
                    </td>
                    <td className="px-4 py-2 relative">
                      <div className="relative">
                        <Input
                          value={row.salary}
                          onChange={(e) => handleCellChange('dashboard', row.id, 'salary', e.target.value)}
                          onMouseEnter={() => handleMouseEnter('dashboard', row.id, 'salary')}
                          className={`border-0 focus-visible:ring-1 h-8 ${
                            draggedCells.includes(row.id) && dragStart?.field === 'salary'
                              ? 'bg-blue-100 border-2 border-blue-400'
                              : ''
                          }`}
                        />
                        <div
                          onMouseDown={() => handleMouseDown(row.id, 'salary')}
                          className="absolute bottom-0 right-0 w-2 h-2 bg-blue-600 cursor-crosshair hover:w-3 hover:h-3 transition-all"
                          style={{ transform: 'translate(50%, 50%)' }}
                        />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    );
  };

  const renderUsersTable = () => {
    const filteredData = filterData(usersData);
    
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4" />
            <Input
              placeholder="Filter users..."
              value={filterText}
              onChange={(e) => setFilterText(e.target.value)}
              className="w-64"
            />
          </div>
          <div className="flex gap-2">
            <Button onClick={() => addNewRow('users')} className="gap-2">
              <Plus className="h-4 w-4" />
              Add User
            </Button>
            <Button onClick={() => exportData('users')} variant="outline" className="gap-2">
              <Download className="h-4 w-4" />
              Export
            </Button>
          </div>
        </div>

        <div className="border rounded-lg bg-white overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">ID</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Username</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Email</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Role</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Active</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {filteredData.map((row) => (
                  <tr key={row.id} className="hover:bg-gray-50">
                    <td className="px-4 py-2 text-sm text-gray-900">{row.id}</td>
                    <td className="px-4 py-2 relative">
                      <div className="relative">
                        <Input
                          value={row.username}
                          onChange={(e) => handleCellChange('users', row.id, 'username', e.target.value)}
                          onMouseEnter={() => handleMouseEnter('users', row.id, 'username')}
                          className={`border-0 focus-visible:ring-1 h-8 ${
                            draggedCells.includes(row.id) && dragStart?.field === 'username'
                              ? 'bg-blue-100 border-2 border-blue-400'
                              : ''
                          }`}
                        />
                        <div
                          onMouseDown={() => handleMouseDown(row.id, 'username')}
                          className="absolute bottom-0 right-0 w-2 h-2 bg-blue-600 cursor-crosshair hover:w-3 hover:h-3 transition-all"
                          style={{ transform: 'translate(50%, 50%)' }}
                        />
                      </div>
                    </td>
                    <td className="px-4 py-2 relative">
                      <div className="relative">
                        <Input
                          value={row.email}
                          onChange={(e) => handleCellChange('users', row.id, 'email', e.target.value)}
                          onMouseEnter={() => handleMouseEnter('users', row.id, 'email')}
                          className={`border-0 focus-visible:ring-1 h-8 ${
                            draggedCells.includes(row.id) && dragStart?.field === 'email'
                              ? 'bg-blue-100 border-2 border-blue-400'
                              : ''
                          }`}
                        />
                        <div
                          onMouseDown={() => handleMouseDown(row.id, 'email')}
                          className="absolute bottom-0 right-0 w-2 h-2 bg-blue-600 cursor-crosshair hover:w-3 hover:h-3 transition-all"
                          style={{ transform: 'translate(50%, 50%)' }}
                        />
                      </div>
                    </td>
                    <td className="px-4 py-2 relative">
                      <div className="relative">
                        <Select
                          value={row.role}
                          onValueChange={(value) => handleCellChange('users', row.id, 'role', value)}
                        >
                          <SelectTrigger 
                            className={`border-0 focus:ring-1 h-8 ${
                              draggedCells.includes(row.id) && dragStart?.field === 'role'
                                ? 'bg-blue-100 border-2 border-blue-400'
                                : ''
                            }`}
                            onMouseEnter={() => handleMouseEnter('users', row.id, 'role')}
                          >
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {roles.map(role => (
                              <SelectItem key={role} value={role}>{role}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        <div
                          onMouseDown={() => handleMouseDown(row.id, 'role')}
                          className="absolute bottom-0 right-0 w-2 h-2 bg-blue-600 cursor-crosshair hover:w-3 hover:h-3 transition-all z-10"
                          style={{ transform: 'translate(50%, 50%)' }}
                        />
                      </div>
                    </td>
                    <td className="px-4 py-2 relative">
                      <div className="relative">
                        <Select
                          value={row.active}
                          onValueChange={(value) => handleCellChange('users', row.id, 'active', value)}
                        >
                          <SelectTrigger 
                            className={`border-0 focus:ring-1 h-8 ${
                              draggedCells.includes(row.id) && dragStart?.field === 'active'
                                ? 'bg-blue-100 border-2 border-blue-400'
                                : ''
                            }`}
                            onMouseEnter={() => handleMouseEnter('users', row.id, 'active')}
                          >
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="Yes">Yes</SelectItem>
                            <SelectItem value="No">No</SelectItem>
                          </SelectContent>
                        </Select>
                        <div
                          onMouseDown={() => handleMouseDown(row.id, 'active')}
                          className="absolute bottom-0 right-0 w-2 h-2 bg-blue-600 cursor-crosshair hover:w-3 hover:h-3 transition-all z-10"
                          style={{ transform: 'translate(50%, 50%)' }}
                        />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    );
  };

  const menuItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'users', label: 'Users', icon: Users },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  return (
    <div className={`flex h-screen bg-gray-50 ${isDragging ? 'cursor-crosshair select-none' : ''}`}>
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
              {activeScreen === 'dashboard' && 'Manage employee data with drag-down, filters, and dropdowns'}
              {activeScreen === 'users' && 'Manage user accounts and permissions'}
              {activeScreen === 'settings' && 'Configure application settings'}
            </p>
          </div>

          {activeScreen === 'dashboard' && renderDashboardTable()}
          {activeScreen === 'users' && renderUsersTable()}
          {activeScreen === 'settings' && (
            <div className="border rounded-lg bg-white p-6">
              <h3 className="text-lg font-semibold mb-4">Application Settings</h3>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-2">Theme</label>
                  <Select defaultValue="light">
                    <SelectTrigger className="w-64">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="light">Light</SelectItem>
                      <SelectItem value="dark">Dark</SelectItem>
                      <SelectItem value="auto">Auto</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">Language</label>
                  <Select defaultValue="en">
                    <SelectTrigger className="w-64">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="en">English</SelectItem>
                      <SelectItem value="es">Spanish</SelectItem>
                      <SelectItem value="fr">French</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <Button className="mt-4">Save Settings</Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ShadcnTableApp;/
