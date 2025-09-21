# Legal Document Analysis API Documentation

A comprehensive AI-powered legal document analysis system with semantic bucket enhancement for identifying predatory and unfair clauses in contracts.

## Base URL
```
http://localhost:8000
```

## Authentication
Currently, no authentication is required for API access.

---

## Endpoints Overview

| Endpoint | Method | Description |
|----------|---------|-------------|
| `/api/classification/analyze/document` | POST | Analyze legal document for predatory clauses |
| `/api/reference/buckets` | GET | List all semantic buckets |
| `/api/reference/buckets/{bucket_id}` | GET | Get specific bucket details |
| `/api/reference/buckets/recompute` | POST | Trigger bucket recomputation |
| `/api/reference/documents` | GET | List reference documents |
| `/api/reference/documents` | POST | Upload reference document |
| `/api/reference/rules` | GET | List classification rules |
| `/api/reference/rules` | POST | Create classification rule |

---

## 1. Document Analysis API

### Analyze Legal Document
**Endpoint:** `POST /api/classification/analyze/document`

**Description:** Uploads and analyzes a legal document (PDF) to identify predatory or unfair clauses using AI with bucket-enhanced context from similar documents.

#### Request Format
```bash
curl -X POST "http://localhost:8000/api/classification/analyze/document" \
  -F "file=@/path/to/document.pdf"
```

#### Request Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file` | File | Yes | PDF document to analyze (max 50MB) |

#### Response Format
```json
{
  "structured_text": "string",
  "clauses": [
    {
      "clause_text": "string",
      "start_position": 0,
      "end_position": 100,
      "severity": "CRITICAL | HIGH | MEDIUM | LOW",
      "category": "string",
      "explanation": "string",
      "suggested_action": "string"
    }
  ],
  "bucket_context": {
    "bucket_id": "string",
    "bucket_name": "string",
    "similarity_score": 0.75,
    "document_count": 5,
    "relevant_documents": ["doc_id_1", "doc_id_2"]
  },
  "analysis_metadata": {
    "processing_time_ms": 60000,
    "text_length": 2500,
    "structured_text_length": 2600,
    "clauses_identified": 8,
    "bucket_enhanced": true,
    "context_chunks_used": 5
  }
}
```

#### Severity Levels
| Level | Description |
|-------|-------------|
| `CRITICAL` | Immediate legal or financial danger - major losses, legal jeopardy, severe restrictions |
| `HIGH` | Significant unfair advantage to other party - substantial risk or cost |
| `MEDIUM` | Moderately concerning terms that limit rights or create potential issues |
| `LOW` | Minor concerns or standard clauses that could be improved |

#### Clause Categories
- `Financial Impact` - Hidden fees, excessive penalties, unclear costs
- `Rights & Obligations` - Unbalanced responsibilities, waived rights
- `Termination & Cancellation` - Difficult exit clauses, automatic renewals
- `Liability & Risk` - Unfair liability shifting, inadequate protections
- `Intellectual Property` - Overly broad IP assignments, invention ownership
- `Confidentiality & Restrictions` - Excessive NDAs, non-compete overreach
- `Dispute Resolution` - Forced arbitration, jurisdiction limitations
- `Modification & Control` - Unilateral change rights, governing terms
- `Privacy & Data` - Data collection overreach, usage rights
- `Performance & Standards` - Unrealistic expectations, undefined terms

#### Example Request
```bash
curl -X POST "http://localhost:8000/api/classification/analyze/document" \
  -F "file=@employment_contract.pdf"
```

#### Example Response
```json
{
  "structured_text": "# Employment Agreement\n\nThis Employment Agreement is made on 1st October 2025...",
  "clauses": [
    {
      "clause_text": "Any invention or work developed by Employee during the course of employment and related to Employer's business shall belong to Employer.",
      "start_position": 1040,
      "end_position": 1172,
      "severity": "HIGH",
      "category": "Intellectual Property",
      "explanation": "This clause grants the Employer broad ownership of any invention or work developed by the Employee during their employment, even if it's outside of their core responsibilities or created during personal time. This could stifle the Employee's creativity and future opportunities.",
      "suggested_action": "Request to narrow the scope of the clause to inventions directly related to the Employee's assigned duties and developed using company resources. Propose adding language that inventions created outside of work hours or unrelated to the company's business remain the Employee's property."
    }
  ],
  "bucket_context": {
    "bucket_id": "e390af04-439c-4ccd-b219-758aad6aa933",
    "bucket_name": "chunk_cluster_3",
    "similarity_score": 0.6660746714353368,
    "document_count": 1,
    "relevant_documents": [
      "0380a97a-9865-4e7f-8656-cafa64dbb7bb"
    ]
  },
  "analysis_metadata": {
    "processing_time_ms": 68886,
    "text_length": 2439,
    "structured_text_length": 2461,
    "clauses_identified": 2,
    "bucket_enhanced": true,
    "context_chunks_used": 5
  }
}
```

---

## 2. Bucket Management API

### List Semantic Buckets
**Endpoint:** `GET /api/reference/buckets`

**Description:** Retrieve all semantic buckets used for document similarity matching.

#### Request Format
```bash
curl -X GET "http://localhost:8000/api/reference/buckets?limit=50&offset=0"
```

#### Query Parameters
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | 50 | Maximum buckets to return (1-1000) |
| `offset` | integer | 0 | Number of buckets to skip |

#### Response Format
```json
[
  {
    "bucket_id": "string",
    "bucket_name": "string",
    "document_count": 5,
    "description": "string",
    "created_at": "2025-09-21T15:23:24.926785",
    "updated_at": "2025-09-21T15:23:24.926792"
  }
]
```

### Get Specific Bucket
**Endpoint:** `GET /api/reference/buckets/{bucket_id}`

#### Response Format
```json
{
  "bucket_id": "e390af04-439c-4ccd-b219-758aad6aa933",
  "bucket_name": "chunk_cluster_3",
  "document_count": 1,
  "description": "Cluster 3: 111 chunks from 1 documents. Top docs: employment_contract.pdf(111)",
  "created_at": "2025-09-21T15:23:24.926785",
  "updated_at": "2025-09-21T15:23:24.926792"
}
```

### Recompute Buckets
**Endpoint:** `POST /api/reference/buckets/recompute`

**Description:** Trigger recomputation of all semantic buckets based on current document corpus.

#### Response Format
```json
{
  "message": "Bucket recomputation started",
  "status": "accepted"
}
```

---

## 3. Reference Document Management

### List Reference Documents
**Endpoint:** `GET /api/reference/documents`

#### Query Parameters
| Parameter | Type | Description |
|-----------|------|-------------|
| `limit` | integer | Maximum documents to return (1-1000) |
| `offset` | integer | Number of documents to skip |
| `severity_filter` | enum | Filter by severity: `CRITICAL`, `HIGH`, `MEDIUM`, `LOW` |
| `tag_filter` | string | Filter by tag |

#### Response Format
```json
[
  {
    "document_id": "string",
    "filename": "contract.pdf",
    "severity_label": "HIGH",
    "file_size": 125000,
    "content_hash": "sha256_hash",
    "tags": ["employment", "IP_clause"],
    "created_at": "2025-09-21T15:23:24.926785",
    "uploader_id": "user123",
    "description": "Employment contract with problematic IP clause"
  }
]
```

### Upload Reference Document
**Endpoint:** `POST /api/reference/documents`

#### Request Format
```bash
curl -X POST "http://localhost:8000/api/reference/documents" \
  -F "file=@reference_contract.pdf" \
  -F "severity_label=HIGH" \
  -F "tags=employment,confidentiality" \
  -F "description=Reference contract with standard confidentiality issues"
```

---

## 4. Classification Rules Management

### List Classification Rules
**Endpoint:** `GET /api/reference/rules`

#### Query Parameters
| Parameter | Type | Description |
|-----------|------|-------------|
| `limit` | integer | Maximum rules to return |
| `offset` | integer | Number of rules to skip |
| `active_only` | boolean | Return only active rules |

#### Response Format
```json
[
  {
    "rule_id": "string",
    "name": "High Interest Rate Detection",
    "description": "Identifies interest rates above 25%",
    "conditions": [
      {
        "operator": "CONTAINS",
        "field": "text",
        "value": "interest rate",
        "case_sensitive": false
      }
    ],
    "condition_logic": "AND",
    "severity_override": "HIGH",
    "priority": 1,
    "active": true,
    "created_at": "2025-09-21T15:23:24.926785",
    "updated_at": "2025-09-21T15:23:24.926792"
  }
]
```

---

## Error Responses

### Standard Error Format
```json
{
  "status": "error",
  "message": "Error description",
  "data": null,
  "errors": [
    {
      "code": "ERROR_CODE",
      "message": "Detailed error message",
      "field": "field_name",
      "value": "invalid_value",
      "context": {
        "type": "validation_error"
      }
    }
  ],
  "warnings": null,
  "metadata": null,
  "timestamp": "2025-09-21T15:55:12.471027"
}
```

### Common Error Codes
| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 422 | Request validation failed |
| `FILE_TOO_LARGE` | 413 | File exceeds size limit |
| `UNSUPPORTED_FORMAT` | 415 | Unsupported file format |
| `INTERNAL_ERROR` | 500 | Server error |
| `NOT_FOUND` | 404 | Resource not found |

---

## Rate Limits

- **Document Analysis:** No explicit limit, but processing time is ~60-90 seconds per document
- **Bucket Operations:** No limit
- **Document Upload:** 50MB file size limit

---

## Response Times

| Operation | Typical Time |
|-----------|--------------|
| Document Analysis | 60-90 seconds |
| Bucket Listing | < 1 second |
| Document Upload | 5-10 seconds |
| Rule Operations | < 1 second |

---

## Usage Examples

### Complete Analysis Workflow
```bash
# 1. Check available buckets
curl -X GET "http://localhost:8000/api/reference/buckets" | jq 'length'

# 2. Analyze a contract
curl -X POST "http://localhost:8000/api/classification/analyze/document" \
  -F "file=@contract.pdf" | jq '{
    clauses: (.clauses | length),
    critical: [.clauses[] | select(.severity == "CRITICAL")] | length,
    high: [.clauses[] | select(.severity == "HIGH")] | length,
    bucket_enhanced: .analysis_metadata.bucket_enhanced
  }'

# 3. Get detailed clause analysis
curl -X POST "http://localhost:8000/api/classification/analyze/document" \
  -F "file=@contract.pdf" | jq '.clauses[] | {
    severity,
    category,
    clause_text: (.clause_text | .[0:100] + "..."),
    explanation: (.explanation | .[0:200] + "...")
  }'
```

### Bucket Analysis
```bash
# Check bucket statistics
curl -X GET "http://localhost:8000/api/reference/buckets" | jq '{
  total_buckets: length,
  bucket_names: [.[].bucket_name] | unique
}'
```

---

## Integration Notes

1. **File Upload**: Use `multipart/form-data` for document uploads
2. **Async Processing**: Document analysis is synchronous but may take 1-2 minutes
3. **Bucket Context**: Analysis automatically uses semantic buckets for enhanced context
4. **Error Handling**: Check `status` field in response for success/error state
5. **Pagination**: Use `limit` and `offset` for large result sets

---

## SDK Examples

### Python
```python
import requests

# Analyze document
with open('contract.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/classification/analyze/document',
        files={'file': f}
    )
    
result = response.json()
print(f"Found {len(result['clauses'])} problematic clauses")
for clause in result['clauses']:
    print(f"- {clause['severity']}: {clause['category']}")
```

### JavaScript
```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);

fetch('http://localhost:8000/api/classification/analyze/document', {
    method: 'POST',
    body: formData
})
.then(response => response.json())
.then(data => {
    console.log(`Analysis complete: ${data.clauses.length} clauses found`);
    console.log(`Bucket enhanced: ${data.analysis_metadata.bucket_enhanced}`);
});
```

---

## Support

For API support or questions about integration, refer to the system logs or contact the development team.

**Last Updated:** September 21, 2025