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
                       
