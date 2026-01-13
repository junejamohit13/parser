interface DateMultiSelectFilter {                                                                   
      25 +   selectedDates: string[];                                                                          
      26   }  

+const dateMultiSelectFilter: FilterFn<Record<string, unknown>> = (row, columnId, filterValue:        
         +DateMultiSelectFilter) => {                                                                          
      40     const value = row.getValue(columnId) as string;                                                   
      41     if (!value) return false;                                                                         
      42                                                                                                       
      43 -   const dateValue = new Date(value).getTime();                                                      
      44 -   const { from, to } = filterValue;                                                                 
      43 +   const { selectedDates } = filterValue;                                                            
      44 +   if (!selectedDates || selectedDates.length === 0) return true;                                    
      45                                                                                                       
      46 -   if (from && dateValue < new Date(from).getTime()) return false;                                   
      47 -   if (to && dateValue > new Date(to).getTime()) return false;                                       
      48 -   return true;                                                                                      
      46 +   // Normalize the date for comparison (just the date part)                                         
      47 +   const rowDate = new Date(value).toISOString().split('T')[0];                                      
      48 +   return selectedDates.includes(rowDate);                                                           
      49   };        


   508 -               col.type === 'date' ? dateRangeFilter :                                              
      508 +               col.type === 'date' ? dateMultiSelectFilter :     


       const dateValue = new Date(value).getTime();                                                      
      44 -   const { from, to } = filterValue;                                                                 
      43 +   const { selectedDates } = filterValue;                                                            
      44 +   if (!selectedDates || selectedDates.length === 0) return true;                                    
      45                                                                                                       
      46 -   if (from && dateValue < new Date(from).getTime()) return false;                                   
      47 -   if (to && dateValue > new Date(to).getTime()) return false;                                       
      48 -   return true;                                                                                      
      46 +   // Normalize the date for comparison (just the date part)                                         
      47 +   const rowDate = new Date(value).toISOString().split('T')[0];                                      
      48 +   return selectedDates.includes(rowDate);          


      -                      // Date range filter                                                          
      848 +                      // Date multi-select filter                                                   
      849                         if (colConfig?.type === 'date') {                                            
      850 -                         const rangeValue = (filterValue as DateRangeFilter) || {};                 
      850 +                         const multiSelectValue = (filterValue as DateMultiSelectFilter) || {       
          +selectedDates: [] };                                                                                
      851 +                         const uniqueDates = [...new Set(                                           
      852 +                           data                                                                     
      853 +                             .map(row => row[header.column.id] as string)                           
      854 +                             .filter(Boolean)                                                       
      855 +                             .map(d => new Date(d).toISOString().split('T')[0])                     
      856 +                         )].sort();                                                                 
      857 +                                                                                                    
      858                           return (                                                                   
      859                             <th key={header.id} className="px-2 py-2 bg-gray-50/50">                 
      860 -                            <div className="flex gap-1">                                            
      861 -                              <Input                                                                
      862 -                                 type="date"                                                        
      863 -                                placeholder="From"                                                  
      864 -                                 value={rangeValue.from ?? ''}                                      
      865 -                                 onChange={(e) => {                                                 
      866 -                                  const from = e.target.value || undefined;                         
      867 -                                   header.column.setFilterValue({ ...rangeValue, from });           
      860 +                            <div className="relative">                                              
      861 +                              <Select                                                               
      862 +                                 value={multiSelectValue.selectedDates.length > 0 ? 'custom' :      
          +'__all__'}                                                                                          
      863 +                                onValueChange={(value) => {                                         
      864 +                                   if (value === '__all__') {                                       
      865 +                                     header.column.setFilterValue(undefined);                       
      866 +                                  }                                                                 
      867                                   }}                                                                 
      868 -                                 className="h-8 text-xs border-gray-200 focus:ring-teal-300 w-1/2"  
      869 -                               />                                                                   
      870 -                               <Input                                                               
      871 -                                 type="date"                                                        
      872 -                                 placeholder="To"                                                   
      873 -                                 value={rangeValue.to ?? ''}                                        
      874 -                                 onChange={(e) => {                                                 
      875 -                                   const to = e.target.value || undefined;                          
      876 -                                   header.column.setFilterValue({ ...rangeValue, to });             
      877 -                                 }}                                                                 
      878 -                                 className="h-8 text-xs border-gray-200 focus:ring-teal-300 w-1/2"  
      879 -                               />                                                                   
      868 +                               >                                                                    
      869 +                                 <SelectTrigger className="h-8 text-xs border-gray-200              
          +focus:ring-teal-300">                                                                               
      870 +                                   <SelectValue>                                                    
      871 +                                     {multiSelectValue.selectedDates.length > 0                     
      872 +                                       ? `${multiSelectValue.selectedDates.length} selected`        
      873 +                                       : 'All dates'}                                               
      874 +                                   </SelectValue>                                                   
      875 +                                 </SelectTrigger>                                                   
      876 +                                 <SelectContent className="max-h-[300px]">                          
      877 +                                   <div className="p-2 border-b border-gray-100">                   
      878 +                                     <button                                                        
      879 +                                       className="w-full text-left text-xs text-teal-600            
          +hover:text-teal-700 font-medium"                                                                    
      880 +                                       onClick={(e) => {                                            
      881 +                                         e.preventDefault();                                        
      882 +                                         header.column.setFilterValue(undefined);                   
      883 +                                       }}                                                           
      884 +                                     >                                                              
      885 +                                       Clear all                                                    
      886 +                                     </button>                                                      
      887 +                                   </div>                                                           
      888 +                                   <div className="py-1 max-h-[200px] overflow-y-auto">             
      889 +                                     {uniqueDates.map(date => {                                     
      890 +                                       const isSelected =                                           
          +multiSelectValue.selectedDates.includes(date);                                                      
      891 +                                       const displayDate = new Date(date +                          
          +'T00:00:00').toLocaleDateString('en-US', {                                                          
      892 +                                         year: 'numeric',                                           
      893 +                                         month: 'short',                                            
      894 +                                         day: 'numeric'                                             
      895 +                                       });                                                          
      896 +                                       return (                                                     
      897 +                                         <div                                                       
      898 +                                           key={date}                                               
      899 +                                           className="flex items-center gap-2 px-3 py-1.5           
          +hover:bg-gray-50 cursor-pointer"                                                                    
      900 +                                           onClick={(e) => {                                        
      901 +                                             e.preventDefault();                                    
      902 +                                             e.stopPropagation();                                   
      903 +                                             const newDates = isSelected                            
      904 +                                               ? multiSelectValue.selectedDates.filter(d => d !==   
          +date)                                                                                               
      905 +                                               : [...multiSelectValue.selectedDates, date];         
      906 +                                             header.column.setFilterValue(                          
      907 +                                               newDates.length > 0 ? { selectedDates: newDates } :  
          +undefined                                                                                           
      908 +                                             );                                                     
      909 +                                           }}                                                       
      910 +                                         >                                                          
      911 +                                           <div className={`w-4 h-4 rounded border flex             
          +items-center justify-center ${isSelected ? 'bg-teal-600 border-teal-600' : 'border-gray-300'}`}>    
      912 +                                             {isSelected && <Check className="h-3 w-3 text-white"   
          +/>}                                                                                                 
      913 +                                           </div>                                                   
      914 +                                           <span className="text-xs                                 
          +text-gray-700">{displayDate}</span>                                                                 
      915 +                                         </div>                                                     
      916 +                                       );                                                           
      917 +                                     })}                                                            
      918 +                                   </div>                                                           
      919 +                                 </SelectContent>                                                   
      920 +                               </Select>      
