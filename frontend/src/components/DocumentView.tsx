"use client";

import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { ApiResponse, Clause } from '../types';

// Severity Colors
const SEVERITY_COLORS = {
  CRITICAL: '#FF8A8A',
  HIGH: '#AD88C6',
  MEDIUM: '#FCDC94',
  LOW: '#A5B68D'
};

// Highlighted Text Component with Markdown Support
function HighlightedText({ text, clauses, onClauseClick }: {
  text: string;
  clauses: Clause[];
  onClauseClick: (clause: Clause) => void;
}) {
  type Span = {
    text: string;
    highlighted: boolean;
    clause?: Clause;
  };
  // Split text into lines
  const lines = text.split('\n');

// --- Icon Components ---
const SearchIcon = () => <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>;

// --- Mock API Data ---
const mockDocument: TextSpan[] = [
    { id: 't1', text: 'This document outlines the project proposal. ', type: 'none' },
    { id: 't2', text: 'A critical vulnerability was identified in the authentication module.', type: 'red' },
    { id: 't3', text: ' This requires immediate attention. ', type: 'none' },
    { id: 't4', text: 'The proposed solution has been verified and approved.', type: 'green' },
    { id: 't5', text: ' Please note the upcoming deadline.', type: 'yellow' },
    { id: 't6', text: 'There is a potential conflict with the marketing team\'s schedule.', type: 'purple' },
    { id: 't7', text: ' All stakeholders must review the attached document before the meeting.', type: 'none' },
];

  const lines = text.split('\n');
  const spans: Span[] = [];

  lines.forEach((line, lineIndex) => {
    let currentText = line;
    clauses.forEach(clause => {
      const index = currentText.indexOf(clause.clause_text);
      if (index !== -1) {
        const before = currentText.slice(0, index);
        const after = currentText.slice(index + clause.clause_text.length);
        spans.push({ text: before, highlighted: false });
        spans.push({ text: clause.clause_text, highlighted: true, clause });
        currentText = after;
      }
    });
    if (currentText) {
      spans.push({ text: currentText, highlighted: false });
    }
  });

  return (
    <div>
      {lines.map((line, lineIndex) => (
        <p key={lineIndex}>
          {spans.map((span, spanIndex) => (
            <span
              key={spanIndex}
              style={{
                backgroundColor: span.highlighted && span.clause ? SEVERITY_COLORS[span.clause.severity as keyof typeof SEVERITY_COLORS] : 'transparent',
                cursor: span.highlighted ? 'pointer' : 'default'
              }}
              onClick={() => span.highlighted && onClauseClick(span.clause)}
            >
              {span.text}
            </span>
          ))}
        </p>
      ))}
    </div>
  );
}

// Modal Component
function ClauseModal({ clause, isOpen, onClose }: {
  clause: Clause | null;
  isOpen: boolean;
  onClose: () => void;
}) {
  if (!isOpen || !clause) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white p-6 rounded-lg max-w-md w-full max-h-[80vh] overflow-y-auto">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-bold" style={{ color: SEVERITY_COLORS[clause.severity] }}>
            {clause.severity} Risk
          </h3>
          <button onClick={onClose} className="text-gray-500 text-2xl">×</button>
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

// Filter Buttons
function SeverityFilters({ activeFilter, onFilterChange, counts }: {
  activeFilter: string;
  onFilterChange: (filter: string) => void;
  counts: Record<string, number>;
}) {
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
          style={{ backgroundColor: severity === 'ALL' ? '#666' : SEVERITY_COLORS[severity as keyof typeof SEVERITY_COLORS] }}
        >
          {counts[severity]}
        </button>
      ))}
    </div>
  );
}

// Main Component
export default function DocumentViewPage({ onClose, documentData }: {
  onClose?: () => void;
  documentData: ApiResponse | null;
}) {
  const [activeFilter, setActiveFilter] = useState('ALL');
  const [selectedClause, setSelectedClause] = useState<Clause | null>(null);
  const [modalOpen, setModalOpen] = useState(false);

  if (!documentData) {
    return (
      <main className="grid place-items-center min-h-screen w-full bg-[#91C8E4] p-4 font-crimson">
        <div className="relative w-full max-w-sm h-[861px] max-h-[90vh] bg-[#FFFFFF] rounded-[40px] shadow-2xl overflow-hidden border-4 border-blue-200 flex flex-col">
          <header className="px-6 pt-6 pb-2 flex-shrink-0">
            <button
              onClick={onClose}
              className="w-20 h-20 rounded-full hover:opacity-90 transition-opacity"
            >
              <Image src="/image.png" alt="Back button" width={80} height={80} className="object-contain" />
            </button>
            {documentData && (
              <div className="mt-2">
                <p className="text-sm text-gray-600 font-crimson-pro">Viewing:</p>
                <p className="text-lg font-crimson text-[#4682A9]">{documentData.name}</p>
              </div>
            )}
          </header>
          <div className="flex-1 flex flex-col justify-center items-center p-6">
            <p className="text-center text-gray-600">No document selected.</p>
          </div>
        </div>
      </main>
    );
  }

  const filteredClauses = activeFilter === 'ALL' ? documentData.clauses : documentData.clauses.filter(clause => clause.severity === activeFilter);

  const severityCounts = {
    ALL: documentData.clauses.length,
    CRITICAL: documentData.clauses.filter(c => c.severity === 'CRITICAL').length,
    HIGH: documentData.clauses.filter(c => c.severity === 'HIGH').length,
    MEDIUM: documentData.clauses.filter(c => c.severity === 'MEDIUM').length,
    LOW: documentData.clauses.filter(c => c.severity === 'LOW').length,
  };

  return (
    <main className="grid place-items-center min-h-screen w-full bg-[#91C8E4] p-4 font-crimson">
      <div className="relative w-full max-w-sm h-[861px] max-h-[90vh] bg-[#FFFFFF] rounded-[40px] shadow-2xl overflow-hidden border-4 border-blue-200 flex flex-col">
        <header className="px-6 pt-6 pb-2 flex-shrink-0">
          <button
            onClick={onClose}
            className="w-20 h-20 rounded-full hover:opacity-90 transition-opacity"
          >
            <Image src="/image.png" alt="Back button" width={80} height={80} className="object-contain" />
          </button>
          <div className="mt-2">
            <p className="text-sm text-gray-600 font-crimson-pro">Viewing:</p>
            <p className="text-lg font-crimson text-[#4682A9]">{documentData.name}</p>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto p-6">
          <SeverityFilters
            activeFilter={activeFilter}
            onFilterChange={setActiveFilter}
            counts={severityCounts}
          />

          <HighlightedText
            text={documentData.structured_text}
            clauses={filteredClauses}
            onClauseClick={(clause) => {
              setSelectedClause(clause);
              setModalOpen(true);
            }}
          />
        </div>

        <ClauseModal
          clause={selectedClause}
          isOpen={modalOpen}
          onClose={() => setModalOpen(false)}
        />
      </div>
    </main>
  );
}