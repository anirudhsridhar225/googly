// API Response Types
export interface Clause {
  clause_text: string;
  start_position: number;
  end_position: number;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  category: string;
  explanation: string;
  suggested_action: string;
}

export interface ApiResponse {
  structured_text: string;
  clauses: Clause[];
  bucket_context?: {
    bucket_id: string;
    bucket_name: string;
    similarity_score: number;
    document_count: number;
    relevant_documents: string[];
  };
  analysis_metadata?: {
    processing_time_ms: number;
    text_length: number;
    structured_text_length: number;
    clauses_identified: number;
    bucket_enhanced: boolean;
    context_chunks_used: number;
  };
}

export interface HistoryItem {
  id: number;
  name: string;
  date: Date;
  tag?: string;
}