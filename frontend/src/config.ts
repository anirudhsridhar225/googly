// API Configuration
export const API_CONFIG = {
  // Change this to switch between localhost and hosted backend
  BASE_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',

  ENDPOINTS: {
    ANALYZE_DOCUMENT: '/api/classification/analyze/document',
  }
};

// Helper function to get full API URL
export const getApiUrl = (endpoint: string): string => {
  return `${API_CONFIG.BASE_URL}${endpoint}`;
};