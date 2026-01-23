getStatusesByDepartments: async (departments: string[]): Promise<{ statuses: string[] }> => {            
    const params = new URLSearchParams();                                                                  
    if (departments.length > 0) {                                                                          
      params.append('departments', departments.join(','));                                                 
    }                                                                                                      
    const url = `${API_BASE_URL}/statuses${params.toString() ? '?' + params.toString() : ''}`;             
    const response = await fetch(url);                                                                     
    if (!response.ok) throw new Error('Failed to fetch statuses');                                         
    return await response.json();                                                                          
  },    

  const [loadingStatuses, setLoadingStatuses] = useState(false);        

useEffect(() => {                                                                                        
    const loadStatuses = async () => {                                                                     
      setLoadingStatuses(true);                                                                            
      try {                                                                                                
        const statusResponse = await api.getStatusesByDepartments(selectedDepartments);                    
        setAvailableStatuses(statusResponse.statuses);                                                     
                                                                                                           
        // Clear selected statuses that are no longer available                                            
        if (selectedDepartments.length > 0) {                                                              
          setSelectedStatuses(prev =>                                                                      
            prev.filter(status => statusResponse.statuses.includes(status))                                
          );                                                                                               
        }                                                                                                  
      } catch (error) {                                                                                    
        console.error('Failed to load statuses:', error);                                                  
      } finally {                                                                                          
        setLoadingStatuses(false);                                                                         
      }                                                                                                    
    };                                                                                                     
    loadStatuses();                                                                                        
  }, [selectedDepartments]); // <-- Re-runs when departments change                                        
                       

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
  const [loadingStatuses, setLoadingStatuses] = useState(false);

  const departmentRef = useRef<HTMLDivElement>(null);
  const statusRef = useRef<HTMLDivElement>(null);

  // Load departments on mount
  useEffect(() => {
    const loadDepartments = async () => {
      try {
        const deptResponse = await api.getDepartments();
        setAvailableDepartments(deptResponse.departments);
      } catch (error) {
        console.error('Failed to load departments:', error);
        toast.error('Failed to load departments', { description: 'Please check your connection' });
      }
    };
    loadDepartments();
  }, []);

  // Load statuses based on selected departments (cascading dropdown)
  useEffect(() => {
    const loadStatuses = async () => {
      setLoadingStatuses(true);
      try {
        const statusResponse = await api.getStatusesByDepartments(selectedDepartments);
        setAvailableStatuses(statusResponse.statuses);

        // Clear selected statuses that are no longer available
        if (selectedDepartments.length > 0) {
          setSelectedStatuses(prev =>
            prev.filter(status => statusResponse.statuses.includes(status))
          );
        }
      } catch (error) {
        console.error('Failed to load statuses:', error);
        toast.error('Failed to load statuses', { description: 'Please check your connection' });
      } finally {
        setLoadingStatuses(false);
      }
    };
    loadStatuses();
  }, [selectedDepartments]);

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

        {/* Status Filter (Cascading - filtered by selected departments) */}
        <div ref={statusRef} className="relative">
          <button
            onClick={() => setShowStatusDropdown(!showStatusDropdown)}
            disabled={loadingStatuses}
            className={`
              w-full flex items-center justify-between px-4 py-2.5
              bg-white border rounded-xl text-sm font-medium
              transition-all duration-200 hover:border-teal-200 hover:shadow-sm
              ${showStatusDropdown ? 'border-teal-300 shadow-sm ring-2 ring-teal-100' : 'border-gray-200'}
              ${loadingStatuses ? 'opacity-70' : ''}
            `}
          >
            <span className={selectedStatuses.length > 0 ? 'text-teal-700' : 'text-gray-600'}>
              {loadingStatuses ? (
                <span className="flex items-center gap-2">
                  <Loader2 className="h-3 w-3 animate-spin" />
                  Loading...
                </span>
              ) : selectedStatuses.length > 0
                ? `${selectedStatuses.length} status selected`
                : 'All statuses'}
            </span>
            <ChevronDown className={`h-4 w-4 text-gray-400 transition-transform ${showStatusDropdown ? 'rotate-180' : ''}`} />
          </button>

          {showStatusDropdown && !loadingStatuses && (
            <div className="absolute bottom-full left-0 right-0 mb-2 bg-white border border-gray-200 rounded-xl shadow-xl z-20 overflow-hidden animate-scale-in">
              <div className="p-2 border-b border-gray-100 flex items-center justify-between">
                <div className="flex flex-col">
                  <span className="text-xs font-semibold text-gray-500 px-2">Statuses</span>
                  {selectedDepartments.length > 0 && (
                    <span className="text-[10px] text-teal-600 px-2">
                      Filtered by {selectedDepartments.length} dept(s)
                    </span>
                  )}
                </div>
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
                {availableStatuses.length === 0 ? (
                  <div className="px-3 py-4 text-sm text-gray-500 text-center">
                    No statuses available
                  </div>
                ) : (
                  availableStatuses.map((status) => (
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
                  ))
                )}
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

