// API client configuration

// Base URL configuration - works in both dev and production
const API_BASE_URL = import.meta.env.DEV 
  ? '/api'  // Proxy to backend in development
  : 'http://localhost:8000/api';  // Direct backend in production

// Generic API request function
async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        ...options.headers,
      }
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('API request failed:', error);
    throw error;
  }
}

// API methods
export const api = {
  // Upload file
  async uploadFile(file: File): Promise<FileUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    
    return apiRequest<FileUploadResponse>('/upload', {
      method: 'POST',
      body: formData
    });
  },
  
  // Process query
  async processQuery(request: QueryRequest): Promise<QueryResponse> {
    return apiRequest<QueryResponse>('/query', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(request)
    });
  },
  
  // Get database schema
  async getSchema(): Promise<DatabaseSchemaResponse> {
    return apiRequest<DatabaseSchemaResponse>('/schema');
  },
  
  // Generate insights
  async generateInsights(request: InsightsRequest): Promise<InsightsResponse> {
    return apiRequest<InsightsResponse>('/insights', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(request)
    });
  },
  
  // Health check
  async healthCheck(): Promise<HealthCheckResponse> {
    return apiRequest<HealthCheckResponse>('/health');
  },
  
  // Generate random query
  async generateRandomQuery(): Promise<RandomQueryResponse> {
    return apiRequest<RandomQueryResponse>('/generate-random-query');
  },

  // Export a table as CSV (triggers a browser download)
  async exportTable(tableName: string): Promise<void> {
    return downloadFile(`/export/table/${encodeURIComponent(tableName)}`, {
      method: 'GET'
    }, `${tableName}.csv`);
  },

  // Export query results as CSV (triggers a browser download)
  async exportResults(sql: string): Promise<void> {
    return downloadFile('/export/results', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ sql } as ExportResultsRequest)
    }, 'query_results.csv');
  }
};

// Fetch an endpoint and trigger a browser download of the response body.
// Derives the filename from the Content-Disposition header when present,
// otherwise falls back to the provided default.
async function downloadFile(
  endpoint: string,
  options: RequestInit,
  defaultFilename: string
): Promise<void> {
  const url = `${API_BASE_URL}${endpoint}`;

  const response = await fetch(url, options);

  if (!response.ok) {
    // Try to surface a useful error message from the JSON body
    let message = `HTTP error! status: ${response.status}`;
    try {
      const data = await response.json();
      if (data?.detail) {
        message = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
      }
    } catch {
      // Response body was not JSON; keep the default message
    }
    throw new Error(message);
  }

  // Determine the filename from Content-Disposition when available
  let filename = defaultFilename;
  const disposition = response.headers.get('Content-Disposition');
  if (disposition) {
    const match = /filename="?([^"]+)"?/.exec(disposition);
    if (match && match[1]) {
      filename = match[1];
    }
  }

  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = objectUrl;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(objectUrl);
}