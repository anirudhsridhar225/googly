# Document Analysis API Specification

## Overview

This specification defines the `/api/classification/analyze/document` endpoint for complete legal document analysis. The endpoint processes PDF uploads through a two-phase AI pipeline:

1. **Text Restructuring**: AI converts raw PDF text into clean, readable markdown
2. **Clause Analysis**: AI identifies predatory clauses using tool calls with precise positioning

The response provides structured data for frontend highlighting and modal interactions.

## Endpoint Details

- **URL**: `POST /api/classification/analyze/document`
- **Authentication**: None (Gemini API key handled server-side)
- **Content-Type**: `multipart/form-data`
- **Timeout**: 300 seconds

## Request Format

### Parameters
- `file` (required): PDF document file

### Example Request
```javascript
const formData = new FormData();
formData.append('file', pdfFile);

fetch('/api/classification/analyze/document', {
  method: 'POST',
  body: formData
});
```

## Processing Pipeline

### Phase 1: Document Processing
1. Extract text using existing OCR/text extraction code in the repo (text_ocr.py, utils.py, document_processing.py)

### Phase 2: AI Processing with Tool Calls
1. **Text Restructuring**: Send raw text to Gemini for markdown formatting (no tools needed)
2. **Clause Analysis**: Send structured markdown to Gemini with tool calling for clause identification
3. **Tool Processing**: Gemini makes multiple tool calls, one per problematic clause found
4. **Data Collection**: Backend collects all tool call responses into structured clause data

### Tool Calling Setup:
```python
CLAUSE_ANALYSIS_TOOLS = [{
    "name": "identify_problematic_clause",
    "description": "Identify and analyze a predatory or unfair clause",
    "parameters": {
        "type": "object",
        "properties": {
            "clause_text": {"type": "string", "description": "Exact clause text from document"},
            "start_position": {"type": "integer", "description": "Character position in structured text"},
            "end_position": {"type": "integer", "description": "Character position in structured text"},
            "severity": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH", "CRITICAL"]},
            "category": {"type": "string", "description": "Type: unfair_fees, hidden_terms, auto_renewal, etc."},
            "explanation": {"type": "string", "description": "Detailed explanation of why problematic"},
            "suggested_action": {"type": "string", "description": "Recommended action for user"}
        },
        "required": ["clause_text", "start_position", "end_position", "severity", "category", "explanation", "suggested_action"]
    }
}]
```

### Analysis Prompt:
```
Analyze this legal document for predatory or unfair clauses. Use the identify_problematic_clause tool for each problematic clause you find.

Focus on: unfair fees, hidden terms, automatic renewals, unilateral changes, excessive penalties, arbitration clauses, liability issues.

Document:
{structured_markdown_text}
```

### Phase 3: Response Assembly
1. Validate clause positions in structured text
2. Build final response with all required fields

### Phase 4: Response Assembly
1. Compile all data into structured response
2. Log audit trail
3. Return JSON response

## Response Format

### Success Response (200 OK)
```json
{
  "structured_text": "# Agreement Title\n\n## Section 1\n\nContent...",
  "clauses": [
    {
      "clause_text": "Exact clause text from document",
      "start_position": 145,
      "end_position": 210,
      "severity": "CRITICAL",
      "category": "unfair_fees",
      "explanation": "Why this clause is problematic",
      "suggested_action": "Recommended action"
    }
  ],

}
```

### Response Fields

#### Core Data
- `structured_text`: AI-restructured markdown for display

#### Clause Data
- `clauses[]`: Array of identified problematic clauses
  - `clause_text`: Exact text from structured document
  - `start_position`: Character index start in structured_text
  - `end_position`: Character index end in structured_text
  - `severity`: CRITICAL, HIGH, MEDIUM, LOW
  - `category`: Type of predatory term
  - `explanation`: Detailed problem description
  - `suggested_action`: Recommended remediation



## Error Responses

### Generic Error (any 4xx/5xx status)
```json
{
  "error": "Error message describing what went wrong"
}
```

## Frontend Integration

### Position-Based Highlighting
Positions are character indices in `structured_text`. Use them to inject HTML spans before markdown rendering:

```javascript
function applyHighlights(markdownText, clauses) {
  let text = markdownText;
  clauses.sort((a, b) => b.start_position - a.start_position);
  
  clauses.forEach((clause, index) => {
    const before = text.substring(0, clause.start_position);
    const clauseContent = text.substring(clause.start_position, clause.end_position);
    const after = text.substring(clause.end_position);
    
    const highlighted = `<span class="clause-highlight severity-${clause.severity.toLowerCase()}" data-clause='${JSON.stringify(clause)}'>${clauseContent}</span>`;
    text = before + highlighted + after;
  });
  
  return text;
}

// Then render with marked.js
const highlightedMarkdown = applyHighlights(analysis.structured_text, analysis.clauses);
const html = marked.parse(highlightedMarkdown);
document.getElementById('viewer').innerHTML = html;
```

### CSS for Highlights
```css
.clause-highlight {
  cursor: pointer;
  border-radius: 3px;
  padding: 2px 4px;
  border-left: 3px solid;
}

.severity-critical { background: #ffebee; border-left-color: #f44336; }
.severity-high { background: #fff3e0; border-left-color: #ff9800; }
.severity-medium { background: #fffde7; border-left-color: #ffeb3b; }
.severity-low { background: #e8f5e8; border-left-color: #4caf50; }
```

### Modal Integration
```javascript
document.querySelectorAll('.clause-highlight').forEach(span => {
  span.addEventListener('click', (e) => {
    const clause = JSON.parse(e.target.dataset.clause);
    showModal(clause);
  });
});

function showModal(clause) {
  // Implement bottom-sheet modal with clause details
}
```

## Implementation Notes

### Position Accuracy
- AI provides exact character positions in structured text
- Backend validates positions are within bounds
- Frontend applies highlights before markdown rendering

### Performance
- Expected processing time: 30-90 seconds
- Memory usage: 200-500MB for large documents
- API calls: 2 Gemini calls per document

### Tool Calling
Gemini function calling ensures reliable clause data extraction without JSON parsing issues.

### Severity Levels
- CRITICAL: Immediate legal danger
- HIGH: Significant risk requiring attention
- MEDIUM: Moderate concerns
- LOW: Minor issues

## Hackathon Optimizations (3-Hour Implementation)

### Major Time-Saving Cuts:
1. **Two AI Calls**: Separate restructuring and clause analysis (but maintain robust tool calls)
2. **No Firestore**: Store everything in memory, no database persistence
3. **No Audit Logging**: Skip all compliance and logging features
4. **Minimal Validation**: Basic file checks only
5. **No Error Recovery**: Simple try/catch, fail fast
6. **No Performance Monitoring**: Skip middleware and tracking
7. **No Batch Processing**: Single document only
8. **Simplified Response**: Basic JSON, no complex formatting

### Maintained Robustness:
- **Tool Calling**: Full Gemini function calling for reliable clause extraction
- **Position Accuracy**: Character positions validated in structured text
- **Data Validation**: Tool responses validated before use
- **Exact Clause Text**: AI must provide precise text matches

### Implementation Priority (2-3 Hours):
1. **Hour 1**: Basic file upload route + text extraction
2. **Hour 2**: Gemini restructuring + tool calling for clauses
3. **Hour 3**: Simple response formatting + basic testing

### Expected Timeline:
- **0-20 min**: Basic route handler with file upload
- **20-80 min**: Text extraction + AI restructuring
- **80-140 min**: Tool calling for clause analysis
- **140-180 min**: Simple response formatting + testing

### Quick Implementation Notes:
- Use existing `extract_text_auto()` from `utils.py`
- Extend existing `gemini_classifier.py` for tool calls
- Return simple dict-based response (no complex Pydantic models)
- Skip all middleware, logging, validation, and error handling complexity
- No file validation, no IDs, no timestamps, no legal_risks array

This specification provides everything needed to implement the document analysis feature in 3 hours while maintaining robust tool calling for clause identification.