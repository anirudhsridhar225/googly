# Requirements Document

## Introduction

The Legal Document Analysis System is a comprehensive solution that demystifies legal documents by analyzing and tagging clauses based on severity and predatory nature. The system processes legal documents through OCR technology, uses LLM analysis to evaluate clauses, and provides visual highlighting with metadata to help users understand potential risks and exposure levels in legal agreements.

## Requirements

### Requirement 1

**User Story:** As a user, I want to upload legal documents in various formats (PDF, DOCX, scanned images) with encrypted storage, so that I can analyze the content securely regardless of the document format.

#### Acceptance Criteria

1. WHEN a user uploads a PDF document THEN the system SHALL encrypt and store it in Supabase before extracting text content using OCR technology
2. WHEN a user uploads a DOCX document THEN the system SHALL encrypt and store it in Supabase before extracting text content directly from the document structure
3. WHEN a user uploads a scanned document image THEN the system SHALL encrypt and store it in Supabase before using OCR to convert the image to readable text
4. IF the document format is unsupported THEN the system SHALL return an error message indicating supported formats without storing the file
5. WHEN text extraction is complete THEN the system SHALL preserve the original document structure and line positioning while maintaining encrypted storage

### Requirement 2

**User Story:** As a user, I want the system to analyze legal clauses and tag them with severity levels, so that I can understand the potential impact of each clause.

#### Acceptance Criteria

1. WHEN the system processes extracted text THEN it SHALL identify individual legal clauses within the document
2. WHEN a clause is identified THEN the system SHALL analyze it using LLM technology to determine severity level
3. WHEN severity analysis is complete THEN the system SHALL assign one of three severity levels: Low, Medium, High
4. WHEN severity is determined THEN the system SHALL provide reasoning for the severity classification
5. IF a clause cannot be properly analyzed THEN the system SHALL mark it as "Unclassified" with appropriate metadata

### Requirement 3

**User Story:** As a user, I want clauses to be evaluated for predatory nature, so that I can identify potentially harmful or unfair terms.

#### Acceptance Criteria

1. WHEN analyzing each clause THEN the system SHALL evaluate predatory characteristics using LLM analysis
2. WHEN predatory analysis is complete THEN the system SHALL assign one of three predatory levels: Non-Predatory, Moderately Predatory, Highly Predatory
3. WHEN predatory classification is assigned THEN the system SHALL provide specific reasoning for the classification
4. WHEN both severity and predatory analysis are complete THEN the system SHALL combine these metrics for overall risk assessment

### Requirement 4

**User Story:** As a user, I want to see visual highlighting of clauses based on their risk levels, so that I can quickly identify areas of concern in the document.

#### Acceptance Criteria

1. WHEN document analysis is complete THEN the system SHALL apply color-coded highlighting to each analyzed clause
2. WHEN displaying highlighted clauses THEN the system SHALL use distinct colors for different severity levels
3. WHEN displaying highlighted clauses THEN the system SHALL use distinct visual indicators for different predatory levels
4. WHEN a user hovers over or selects a highlighted clause THEN the system SHALL display detailed metadata including severity, predatory level, and reasoning
5. WHEN multiple risk factors apply to a clause THEN the system SHALL use visual indicators that represent the combined risk level

### Requirement 5

**User Story:** As a user, I want to receive structured JSON metadata for each analyzed clause, so that I can understand the detailed analysis results and export them if needed.

#### Acceptance Criteria

1. WHEN clause analysis is complete THEN the system SHALL generate JSON metadata containing exactly three components: the highlighted line text, severity level, and explanation for the severity
2. WHEN generating JSON metadata THEN it SHALL follow the structure: {"line": "clause text", "severity": "severity level", "explanation": "detailed reasoning for severity assignment"}
3. WHEN metadata is generated THEN the system SHALL ensure each JSON object represents one analyzed clause with its complete assessment
4. WHEN a user requests analysis results THEN the system SHALL provide an array of JSON objects, one for each analyzed clause in the document
5. IF analysis fails for any clause THEN the system SHALL include error information in the explanation field of the JSON metadata

### Requirement 6

**User Story:** As a user, I want to view exposure levels for breaking specific clauses, so that I can understand the potential consequences of non-compliance.

#### Acceptance Criteria

1. WHEN analyzing clauses THEN the system SHALL evaluate potential exposure levels for clause violations
2. WHEN exposure analysis is complete THEN the system SHALL assign one of three exposure levels: Low Exposure, Medium Exposure, High Exposure
3. WHEN exposure level is determined THEN the system SHALL provide specific details about potential consequences
4. WHEN displaying clause information THEN the system SHALL include exposure level alongside severity and predatory classifications
5. WHEN multiple clauses have related exposure risks THEN the system SHALL identify and highlight these relationships

### Requirement 7

**User Story:** As a user, I want to manage multiple documents and their analysis results, so that I can compare and track different legal agreements.

#### Acceptance Criteria

1. WHEN a user uploads multiple documents THEN the system SHALL process each document independently with encrypted storage in Supabase
2. WHEN processing multiple documents THEN the system SHALL maintain separate analysis results for each document in Supabase database
3. WHEN analysis is complete THEN the system SHALL provide a summary view comparing risk levels across documents
4. WHEN a user requests document history THEN the system SHALL display previously analyzed documents with their results from Supabase
5. IF a user re-uploads a previously analyzed document THEN the system SHALL detect duplicates and offer to use cached results or re-analyze

### Requirement 8

**User Story:** As a user, I want complete control over my document privacy and deletion, so that I can ensure my sensitive legal documents are permanently removed when I no longer need them.

#### Acceptance Criteria

1. WHEN a user requests document deletion THEN the system SHALL permanently delete the encrypted document from Supabase storage
2. WHEN a document is deleted THEN the system SHALL also remove all associated analysis results, metadata, and cached data from Supabase database
3. WHEN deletion is complete THEN the system SHALL provide confirmation that no traces of the document remain in the system
4. WHEN a user views their document list THEN the system SHALL provide clear deletion options for each document
5. IF a user deletes their account THEN the system SHALL automatically delete all their documents and analysis data from Supabase