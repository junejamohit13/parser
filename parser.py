#crud.py
from sqlalchemy.orm import Session
from sqlalchemy import distinct, func
from typing import List, Optional
import uuid

from . import models, schemas


def get_records(
    db: Session,
    departments: Optional[List[str]] = None,
    statuses: Optional[List[str]] = None
) -> List[models.Record]:
    """Get records with optional filtering"""
    query = db.query(models.Record)

    if departments:
        query = query.filter(models.Record.department.in_(departments))

    if statuses:
        query = query.filter(models.Record.status.in_(statuses))

    return query.all()


def get_departments(db: Session) -> List[str]:
    """Get distinct departments"""
    result = db.query(distinct(models.Record.department)).filter(
        models.Record.department.isnot(None)
    ).all()
    return [dept[0] for dept in result if dept[0]]


def get_statuses(db: Session) -> List[str]:
    """Get distinct statuses"""
    result = db.query(distinct(models.Record.status)).filter(
        models.Record.status.isnot(None)
    ).all()
    return [status[0] for status in result if status[0]]


def update_records_with_transaction(
    db: Session,
    records_data: List[schemas.RecordUpdate]
) -> tuple[uuid.UUID, int]:
    """
    Update records and track transaction
    Returns: (transaction_id, records_updated_count)
    """
    # Generate new transaction ID
    transaction_id = uuid.uuid4()
    records_updated = 0

    # Update each record
    for record_data in records_data:
        record = db.query(models.Record).filter(
            models.Record.id == record_data.id
        ).first()

        if record:
            # Update fields
            update_data = record_data.model_dump(exclude={'id'}, exclude_none=True)
            for key, value in update_data.items():
                setattr(record, key, value)

            # Append transaction ID to transaction_ids array
            if record.transaction_ids is None:
                record.transaction_ids = []
            record.transaction_ids = record.transaction_ids + [transaction_id]

            records_updated += 1

    # Create transaction record
    transaction = models.DimTransaction(
        transaction_id=transaction_id,
        table_name="records",
        operation="update",
        record_count=records_updated
    )
    db.add(transaction)

    # Commit all changes
    db.commit()

    return transaction_id, records_updated


#main.py
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
import os
from dotenv import load_dotenv

from . import models, schemas, crud
from .database import engine, get_db

load_dotenv()

# Create tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Data Manager API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Helper function to build schema response
def build_schema(view_type: str) -> schemas.TableSchema:
    """Build schema based on view type (dashboard or users)"""
    if view_type == "dashboard":
        return schemas.TableSchema(
            columns=[
                schemas.ColumnSchema(name='id', label='ID', type='text', editable=False, visible=False),
                schemas.ColumnSchema(name='name', label='Full Name', type='text', editable=True, visible=True),
                schemas.ColumnSchema(name='status', label='Status', type='select', editable=True, visible=True, options=['Active', 'Inactive', 'Pending']),
                schemas.ColumnSchema(name='department', label='Department', type='select', editable=True, visible=True, options=['Sales', 'Marketing', 'IT', 'HR', 'Finance', 'Operations', 'Legal']),
                schemas.ColumnSchema(name='salary', label='Salary', type='text', editable=True, visible=True),
                schemas.ColumnSchema(name='hire_date', label='Hire Date', type='text', editable=True, visible=False),
                schemas.ColumnSchema(name='location', label='Office Location', type='select', editable=True, visible=True, options=['New York', 'San Francisco', 'London', 'Tokyo', 'Remote']),
                schemas.ColumnSchema(name='manager', label='Manager', type='text', editable=True, visible=False),
                schemas.ColumnSchema(name='phone', label='Phone', type='text', editable=True, visible=False),
                schemas.ColumnSchema(name='employee_type', label='Employment Type', type='select', editable=True, visible=True, options=['Full-Time', 'Part-Time', 'Contract', 'Intern'])
            ]
        )
    else:  # users
        return schemas.TableSchema(
            columns=[
                schemas.ColumnSchema(name='id', label='ID', type='text', editable=False, visible=False),
                schemas.ColumnSchema(name='username', label='Username', type='text', editable=True, visible=True),
                schemas.ColumnSchema(name='email', label='Email Address', type='text', editable=True, visible=True),
                schemas.ColumnSchema(name='role', label='Role', type='select', editable=True, visible=True, options=['Admin', 'Manager', 'User', 'Guest']),
                schemas.ColumnSchema(name='status', label='Status', type='select', editable=True, visible=True, options=['Active', 'Inactive', 'Pending']),
                schemas.ColumnSchema(name='active', label='Active', type='select', editable=True, visible=True, options=['Yes', 'No']),
                schemas.ColumnSchema(name='last_login', label='Last Login', type='text', editable=True, visible=False),
                schemas.ColumnSchema(name='account_type', label='Account Type', type='select', editable=True, visible=True, options=['Premium', 'Standard', 'Trial', 'Enterprise']),
                schemas.ColumnSchema(name='created_date', label='Created Date', type='text', editable=True, visible=False),
                schemas.ColumnSchema(name='department', label='Department', type='select', editable=True, visible=True, options=['Engineering', 'Sales', 'Marketing', 'Support', 'Admin']),
                schemas.ColumnSchema(name='country', label='Country', type='select', editable=True, visible=False, options=['USA', 'UK', 'Canada', 'Germany', 'Japan', 'Australia'])
            ]
        )


def record_to_dict(record: models.Record, view_type: str) -> dict:
    """Convert record to dict based on view type"""
    base_dict = {
        'id': str(record.id),
        'name': record.name,
        'status': record.status,
        'department': record.department,
    }

    if view_type == "dashboard":
        base_dict.update({
            'salary': record.salary,
            'hireDate': record.hire_date,
            'location': record.location,
            'manager': record.manager,
            'phone': record.phone,
            'employeeType': record.employee_type,
        })
    else:  # users
        base_dict.update({
            'username': record.username,
            'email': record.email,
            'role': record.role,
            'active': record.active,
            'lastLogin': record.last_login,
            'accountType': record.account_type,
            'createdDate': record.created_date,
            'country': record.country,
        })

    return base_dict


# API Endpoints

@app.get("/")
def read_root():
    return {"message": "Data Manager API", "version": "1.0.0"}


@app.get("/api/dashboard")
def get_dashboard(
    departments: Optional[str] = None,
    statuses: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get dashboard data with optional filtering"""
    dept_list = departments.split(',') if departments else None
    status_list = statuses.split(',') if statuses else None

    records = crud.get_records(db, departments=dept_list, statuses=status_list)
    schema = build_schema("dashboard")
    data = [record_to_dict(r, "dashboard") for r in records]

    return {
        "schema": schema.model_dump(),
        "data": data
    }


@app.get("/api/users")
def get_users(
    departments: Optional[str] = None,
    statuses: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get users data with optional filtering"""
    dept_list = departments.split(',') if departments else None
    status_list = statuses.split(',') if statuses else None

    records = crud.get_records(db, departments=dept_list, statuses=status_list)
    schema = build_schema("users")
    data = [record_to_dict(r, "users") for r in records]

    return {
        "schema": schema.model_dump(),
        "data": data
    }


@app.get("/api/departments", response_model=schemas.DepartmentsResponse)
def get_departments(db: Session = Depends(get_db)):
    """Get available departments"""
    departments = crud.get_departments(db)
    return {"departments": departments}


@app.get("/api/statuses", response_model=schemas.StatusesResponse)
def get_statuses(db: Session = Depends(get_db)):
    """Get available statuses"""
    statuses = crud.get_statuses(db)
    return {"statuses": statuses}


@app.post("/api/dashboard/save", response_model=schemas.SaveResponse)
def save_dashboard(
    request: schemas.SaveRequest,
    db: Session = Depends(get_db)
):
    """Save dashboard data with transaction tracking"""
    try:
        transaction_id, records_updated = crud.update_records_with_transaction(
            db, request.data
        )
        return {
            "success": True,
            "transaction_id": transaction_id,
            "records_updated": records_updated
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/users/save", response_model=schemas.SaveResponse)
def save_users(
    request: schemas.SaveRequest,
    db: Session = Depends(get_db)
):
    """Save users data with transaction tracking"""
    try:
        transaction_id, records_updated = crud.update_records_with_transaction(
            db, request.data
        )
        return {
            "success": True,
            "transaction_id": transaction_id,
            "records_updated": records_updated
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("API_PORT", 8000))
    host = os.getenv("API_HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)

#database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:password@localhost:5432/datamanager")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


#models.py
from sqlalchemy import Column, String, DateTime, Integer, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from .database import Base


class Record(Base):
    __tablename__ = "records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Common fields
    name = Column(String(255))
    status = Column(String(50))
    department = Column(String(100))

    # Dashboard-specific fields
    salary = Column(String(50))
    hire_date = Column(String(50))
    location = Column(String(100))
    manager = Column(String(255))
    phone = Column(String(50))
    employee_type = Column(String(50))

    # Users-specific fields
    username = Column(String(255))
    email = Column(String(255))
    role = Column(String(50))
    active = Column(String(10))
    last_login = Column(String(50))
    account_type = Column(String(50))
    created_date = Column(String(50))
    country = Column(String(100))

    # Transaction tracking
    transaction_ids = Column(ARRAY(UUID(as_uuid=True)), default=[])

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class DimTransaction(Base):
    __tablename__ = "dim_transaction"

    transaction_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    table_name = Column(String(50))
    operation = Column(String(20))
    record_count = Column(Integer)


#schemas.py
from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID
from datetime import datetime


class RecordBase(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    department: Optional[str] = None
    salary: Optional[str] = None
    hire_date: Optional[str] = None
    location: Optional[str] = None
    manager: Optional[str] = None
    phone: Optional[str] = None
    employee_type: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    active: Optional[str] = None
    last_login: Optional[str] = None
    account_type: Optional[str] = None
    created_date: Optional[str] = None
    country: Optional[str] = None


class RecordUpdate(RecordBase):
    id: UUID


class RecordResponse(RecordBase):
    id: UUID
    transaction_ids: List[UUID] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SaveRequest(BaseModel):
    data: List[RecordUpdate]


class SaveResponse(BaseModel):
    success: bool
    transaction_id: UUID
    records_updated: int


class DepartmentsResponse(BaseModel):
    departments: List[str]


class StatusesResponse(BaseModel):
    statuses: List[str]


class ColumnSchema(BaseModel):
    name: str
    label: str
    type: str
    editable: bool
    visible: bool
    options: Optional[List[str]] = None


class TableSchema(BaseModel):
    columns: List[ColumnSchema]


class DataResponse(BaseModel):
    schema: TableSchema
    data: List[dict]


#lib/utils.ts
import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

#App.css
#root {
  max-width: 1280px;
  margin: 0 auto;
  padding: 2rem;
  text-align: center;
}

.logo {
  height: 6em;
  padding: 1.5em;
  will-change: filter;
  transition: filter 300ms;
}
.logo:hover {
  filter: drop-shadow(0 0 2em #646cffaa);
}
.logo.react:hover {
  filter: drop-shadow(0 0 2em #61dafbaa);
}

@keyframes logo-spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

@media (prefers-reduced-motion: no-preference) {
  a:nth-of-type(2) .logo {
    animation: logo-spin infinite 20s linear;
  }
}

.card {
  padding: 2em;
}

.read-the-docs {
  color: #888;
}

#App.tsx
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
import { LayoutDashboard, Users, Settings, Filter, Download, X, Upload, Check, Loader2, Save, ArrowUpDown, Eye, EyeOff, Home } from 'lucide-react';

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
  }
};

const DataTable = ({ tableKey, config, onDataChange, onSave }) => {
  const [data, setData] = useState(config?.data || []);
  const modifiedRecordIdsRef = useRef(new Set());
  const [, forceUpdate] = useState({});
  const [columnVisibility, setColumnVisibility] = useState({});
  const [columnFilters, setColumnFilters] = useState([]);
  const [sorting, setSorting] = useState([]);
  const [showColumnSelector, setShowColumnSelector] = useState(false);
  const [exportOption, setExportOption] = useState('all');
  const [loading, setLoading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState(null);
  const [dragEnd, setDragEnd] = useState(null);
  const [dragColumn, setDragColumn] = useState(null);

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
    }
  }, [config]);

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
            <span className="font-semibold">{col.label}</span>
            {col.editable && (
              <Button
                variant="ghost"
                size="sm"
                className="h-6 w-6 p-0"
                onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
              >
                <ArrowUpDown className="h-3 w-3" />
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
    },
    onColumnVisibilityChange: setColumnVisibility,
    onColumnFiltersChange: setColumnFilters,
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  const handleExport = async () => {
    setLoading(true);
    try {
      const response = await fetch(`https://api.example.com/export/${tableKey}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          option: exportOption,
          filters: columnFilters
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
      alert('Export simulation - check console for data');
      console.log('Export data:', data);
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
              variant="secondary"
              className="gap-2 bg-blue-50 hover:bg-blue-100 text-blue-700"
            >
              <Eye className="h-4 w-4" />
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
                  <Button size="sm" onClick={() => setShowColumnSelector(false)}>Done</Button>
                </div>
              </div>
            )}
          </div>
          <Button
            onClick={() => {
              const modifiedRecords = data.filter(record => modifiedRecordIdsRef.current.has(record.id));
              console.log('=== SAVE CLICKED ===');
              console.log('Total records in table:', data.length);
              console.log('Modified record IDs:', Array.from(modifiedRecordIdsRef.current));
              console.log('Modified records to send:', modifiedRecords);
              console.log('Number of records to update:', modifiedRecords.length);

              // If no modified records tracked, send all data
              const recordsToSave = modifiedRecords.length > 0 ? modifiedRecords : data;
              console.log('Actually sending:', recordsToSave.length, 'records');

              onSave(tableKey, recordsToSave);
              modifiedRecordIdsRef.current = new Set(); // Clear after save
              forceUpdate({}); // Force re-render to update Save button
            }}
            className="gap-2"
          >
            <Save className="h-4 w-4" />
            Save {modifiedRecordIdsRef.current.size > 0 && `(${modifiedRecordIdsRef.current.size})`}
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
            <tbody className="divide-y divide-gray-200">
              {table.getRowModel().rows.map(row => (
                <tr key={row.id} className="hover:bg-gray-50">
                  {row.getVisibleCells().map(cell => (
                    <td key={cell.id} className="px-4 py-2" data-row-id={row.id}>
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
    font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    line-height: 1.5;
    font-weight: 400;

    /* Theme colors */
    --background: 0 0% 100%;
    --foreground: 222.2 84% 4.9%;
    --card: 0 0% 100%;
    --card-foreground: 222.2 84% 4.9%;
    --popover: 0 0% 100%;
    --popover-foreground: 222.2 84% 4.9%;
    --primary: 221.2 83.2% 53.3%;
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
    --ring: 221.2 83.2% 53.3%;
  }

  body {
    margin: 0;
    min-height: 100vh;
    background-color: hsl(var(--background));
    color: hsl(var(--foreground));
  }
}

#main.tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

#eslint.config.json
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
    "class-variance-authority": "^0.7.1",
    "clsx": "^2.1.1",
    "lucide-react": "^0.553.0",
    "react": "^19.2.0",
    "react-dom": "^19.2.0",
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
