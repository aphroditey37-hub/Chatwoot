/**
 * Utility function to safely extract error message from API responses
 * Handles both string and object error formats
 */
export const getErrorMessage = (error, fallback = 'An error occurred') => {
  if (!error) return fallback;
  
  // If error.response exists (axios error)
  if (error.response?.data) {
    const detail = error.response.data.detail;
    
    // If detail is a string, return it
    if (typeof detail === 'string') {
      return detail;
    }
    
    // If detail is an object (Pydantic validation error)
    if (typeof detail === 'object') {
      // Handle array of validation errors
      if (Array.isArray(detail)) {
        return detail.map(err => err.msg || err.message || JSON.stringify(err)).join(', ');
      }
      
      // Handle single validation error object
      if (detail.msg) return detail.msg;
      if (detail.message) return detail.message;
      
      // Fallback to JSON string
      return JSON.stringify(detail);
    }
    
    // Check for error message field
    if (error.response.data.message) {
      return error.response.data.message;
    }
    
    // Check for error field
    if (error.response.data.error) {
      return typeof error.response.data.error === 'string' 
        ? error.response.data.error 
        : JSON.stringify(error.response.data.error);
    }
  }
  
  // If error.message exists (standard Error)
  if (error.message) {
    return error.message;
  }
  
  // If error is a string
  if (typeof error === 'string') {
    return error;
  }
  
  // Fallback
  return fallback;
};

/**
 * Safely extract detail from error.response.data.detail
 * Use this for inline error handling where you have the detail already
 */
export const safeDetail = (detail, fallback = 'An error occurred') => {
  if (!detail) return fallback;
  if (typeof detail === 'string') return detail;
  if (typeof detail === 'object') {
    if (Array.isArray(detail)) {
      return detail.map(err => err.msg || err.message || JSON.stringify(err)).join(', ');
    }
    if (detail.msg) return detail.msg;
    if (detail.message) return detail.message;
    return JSON.stringify(detail);
  }
  return fallback;
};

/**
 * Utility function to safely display errors in toast notifications
 */
export const showErrorToast = (error, fallback = 'An error occurred', toast) => {
  const message = getErrorMessage(error, fallback);
  toast.error(message);
};
