# Document View Prototype Implementation

## Quick Setup

1. Replace the mock data in `DocumentView.tsx` with real API data.
2. Update the component to handle the API response structure.
3. Implement basic text highlighting and modal popups.

## API Response Structure

```typescript
interface ApiResponse {
  structured_text: string;
  clauses: Clause[];
}

interface Clause {
  clause_text: string;
  start_position: number;
  end_position: number;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  category: string;
  explanation: string;
  suggested_action: string;
}
```

## Core Implementation

### Severity Colors
```typescript
const SEVERITY_COLORS = {
  CRITICAL: '#FF8A8A',
  HIGH: '#AD88C6',
  MEDIUM: '#FCDC94',
  LOW: '#A5B68D'
};
```

### Text Highlighting
```typescript
function HighlightedText({ text, clauses, onClauseClick }) {
  const spans = [];

  let lastEnd = 0;
  clauses.forEach(clause => {
    // Add non-highlighted text
    if (clause.start_position > lastEnd) {
      spans.push({
        text: text.slice(lastEnd, clause.start_position),
        highlighted: false
      });
    }

    // Add highlighted clause
    spans.push({
      text: text.slice(clause.start_position, clause.end_position),
      highlighted: true,
      clause
    });

    lastEnd = clause.end_position;
  });

  // Add remaining text
  if (lastEnd < text.length) {
    spans.push({
      text: text.slice(lastEnd),
      highlighted: false
    });
  }

  return (
    <p>
      {spans.map((span, index) => (
        <span
          key={index}
          style={{
            backgroundColor: span.highlighted ? SEVERITY_COLORS[span.clause.severity] : 'transparent',
            cursor: span.highlighted ? 'pointer' : 'default'
          }}
          onClick={() => span.highlighted && onClauseClick(span.clause)}
        >
          {span.text}
        </span>
      ))}
    </p>
  );
}
```

### Modal Component
```typescript
function ClauseModal({ clause, isOpen, onClose }) {
  if (!isOpen || !clause) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
      <div className="bg-white p-6 rounded-lg max-w-md w-full mx-4">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-bold" style={{ color: SEVERITY_COLORS[clause.severity] }}>
            {clause.severity} Risk
          </h3>
          <button onClick={onClose} className="text-gray-500">×</button>
        </div>

        <div className="mb-4">
          <h4 className="font-semibold">Clause:</h4>
          <p className="text-sm bg-gray-100 p-2 rounded">{clause.clause_text}</p>
        </div>

        <div className="mb-4">
          <h4 className="font-semibold">Category:</h4>
          <p>{clause.category}</p>
        </div>

        <div className="mb-4">
          <h4 className="font-semibold">Explanation:</h4>
          <p className="text-sm">{clause.explanation}</p>
        </div>

        <div className="mb-4">
          <h4 className="font-semibold">Suggested Action:</h4>
          <p className="text-sm bg-blue-50 p-2 rounded">{clause.suggested_action}</p>
        </div>

        <button
          onClick={onClose}
          className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700"
        >
          Close
        </button>
      </div>
    </div>
  );
}
```

### Filter Buttons
```typescript
function SeverityFilters({ activeFilter, onFilterChange, counts }) {
  const severities = ['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'];

  return (
    <div className="flex justify-around mb-4">
      {severities.map(severity => (
        <button
          key={severity}
          onClick={() => onFilterChange(severity)}
          className={`w-12 h-12 rounded-full text-white font-bold ${
            activeFilter === severity ? 'ring-2 ring-blue-500' : ''
          }`}
          style={{ backgroundColor: severity === 'ALL' ? '#666' : SEVERITY_COLORS[severity] }}
        >
          {counts[severity]}
        </button>
      ))}
    </div>
  );
}
```

### Main Component
```typescript
export default function DocumentViewPage({ onClose, documentData }) {
  const [activeFilter, setActiveFilter] = useState('ALL');
  const [selectedClause, setSelectedClause] = useState(null);
  const [modalOpen, setModalOpen] = useState(false);

  if (!documentData) {
    return <div>Loading...</div>;
  }

  const filteredClauses = activeFilter === 'ALL'
    ? documentData.clauses
    : documentData.clauses.filter(c => c.severity === activeFilter);

  const counts = {
    ALL: documentData.clauses.length,
    CRITICAL: documentData.clauses.filter(c => c.severity === 'CRITICAL').length,
    HIGH: documentData.clauses.filter(c => c.severity === 'HIGH').length,
    MEDIUM: documentData.clauses.filter(c => c.severity === 'MEDIUM').length,
    LOW: documentData.clauses.filter(c => c.severity === 'LOW').length
  };

  const handleClauseClick = (clause) => {
    setSelectedClause(clause);
    setModalOpen(true);
  };

  return (
    <div className="min-h-screen bg-blue-200 p-4">
      <div className="max-w-sm mx-auto bg-white rounded-3xl shadow-lg overflow-hidden">
        <header className="p-6">
          <button onClick={onClose} className="mb-4">
            <img src="/image.png" alt="Back" className="w-20 h-20" />
          </button>
          <h1 className="text-xl font-bold text-center">Document Analysis</h1>
          <p className="text-sm text-center text-gray-600">
            {documentData.clauses.length} clauses found
          </p>
        </header>

        <main className="px-6 pb-6">
          <div className="mb-6">
            <HighlightedText
              text={documentData.structured_text}
              clauses={documentData.clauses}
              onClauseClick={handleClauseClick}
            />
          </div>

          <h3 className="font-semibold mb-4">Clauses</h3>
          <SeverityFilters
            activeFilter={activeFilter}
            onFilterChange={setActiveFilter}
            counts={counts}
          />

          <div className="space-y-3">
            {filteredClauses.map((clause, index) => (
              <div
                key={index}
                className="bg-gray-50 p-4 rounded-lg cursor-pointer hover:bg-gray-100"
                onClick={() => handleClauseClick(clause)}
              >
                <div className="flex justify-between items-center mb-2">
                  <span
                    className="px-2 py-1 rounded text-xs text-white"
                    style={{ backgroundColor: SEVERITY_COLORS[clause.severity] }}
                  >
                    {clause.severity}
                  </span>
                  <span className="text-sm text-gray-600">{clause.category}</span>
                </div>
                <p className="text-sm truncate">{clause.clause_text}</p>
              </div>
            ))}
          </div>
        </main>
      </div>

      <ClauseModal
        clause={selectedClause}
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
      />
    </div>
  );
}
```

## Implementation Steps

1. **Update DocumentView.tsx** with the code above
2. **Remove mock data** and use `documentData` prop
3. **Test with sample API response** to ensure highlighting works
4. **Add basic error handling** if needed
5. **Style as needed** for the hackathon demo

This is the minimal viable prototype - just the core functionality to get it working quickly.