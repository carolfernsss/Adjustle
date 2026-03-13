
// Centralized API configuration for production and development environments
const getApiBase = () => {
    // In production, we assume the API is served from the same origin to avoid cors and configuration issues
    if (process.env.NODE_ENV === 'production') {
        return "";
    }
    
    // In development, prioritize environment variable, with local fallback
    return process.env.REACT_APP_API_URL || "http://localhost:8000";
};

export const API_BASE = getApiBase();
