"use client";

import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';

// API Response Types
interface Clause {
  clause_text: string;
  start_position: number;
  end_position: number;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  category: string;
  explanation: string;
  suggested_action: string;
}
import React, { useState, useRef, createRef } from 'react';
import { motion } from 'framer-motion';
import Image from 'next/image';
import type { DocumentData } from '../app/page';

// --- Icon Components ---
const SearchIcon = () => <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>;

interface ApiResponse {
  structured_text: string;
  clauses: Clause[];
}

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
  // Split text into lines
  const lines = text.split('\n');

<<<<<<< HEAD
  return (
    <div className="text-lg leading-relaxed text-gray-800 space-y-4">
      {lines.map((line, lineIndex) => {
        // Check if line is a heading
        if (line.trim().startsWith('#')) {
          return (
            <ReactMarkdown
              key={lineIndex}
              components={{
                h1: ({ children }) => (
                  <h1 className="text-3xl font-bold text-gray-900 mb-6 mt-8 first:mt-0">
                    {children}
                  </h1>
                ),
                p: ({ children }) => <>{children}</>
              }}
            >
              {line}
            </ReactMarkdown>
          );
=======
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

// --- Main Component ---
export default function DocumentViewPage({ onClose, documentData }: { onClose?: () => void; documentData?: DocumentData | null }) {
    const [activeFilter, setActiveFilter] = useState<ThreatType>('none');
    const contentRefs = useRef(mockDocument.map(() => createRef<HTMLSpanElement>()));

    const handleFilterClick = (filter: ThreatType) => {
        setActiveFilter(prevFilter => prevFilter === filter ? 'none' : filter);
    };
    
    const threatColorMap: Record<ThreatType, string> = {
        green: '#A5B68D',
        purple: '#AD88C6',
        yellow: '#FCDC94',
        red: '#FF8A8A',
        none: 'transparent',
    };

    const handleSearch = () => {
        const targetId = 't5';
        const targetIndex = mockDocument.findIndex(span => span.id === targetId);
        if (targetIndex !== -1 && contentRefs.current[targetIndex].current) {
            contentRefs.current[targetIndex].current?.scrollIntoView({
                behavior: 'smooth',
                block: 'center'
            });
>>>>>>> 60967e2 ([feat]: pre deploy frontend push)
        }

<<<<<<< HEAD
        // For regular text lines, apply highlighting
        const lineStartPos = text.split('\n').slice(0, lineIndex).join('\n').length + (lineIndex > 0 ? 1 : 0);
        const lineEndPos = lineStartPos + line.length;
=======
    if (!documentData) {
        return <div>No document selected.</div>;
    }
    
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
>>>>>>> 60967e2 ([feat]: pre deploy frontend push)

        // Find clauses that intersect with this line
        const intersectingClauses = clauses.filter(clause =>
          clause.start_position < lineEndPos && clause.end_position > lineStartPos
        );

<<<<<<< HEAD
        if (intersectingClauses.length === 0) {
          // No highlighting needed
          return <p key={lineIndex}>{line}</p>;
        }

        // Build highlighted spans for this line
        const spans = [];
        let lastPos = 0;

        intersectingClauses.forEach(clause => {
          const clauseStart = Math.max(0, clause.start_position - lineStartPos);
          const clauseEnd = Math.min(line.length, clause.end_position - lineStartPos);

          // Add text before clause
          if (clauseStart > lastPos) {
            spans.push({
              text: line.slice(lastPos, clauseStart),
              highlighted: false
            });
          }

          // Add highlighted clause
          spans.push({
            text: line.slice(clauseStart, clauseEnd),
            highlighted: true,
            clause
          });

          lastPos = clauseEnd;
        });

        // Add remaining text
        if (lastPos < line.length) {
          spans.push({
            text: line.slice(lastPos),
            highlighted: false
          });
        }

        return (
          <p key={lineIndex}>
            {spans.map((span, spanIndex) => (
              <span
                key={spanIndex}
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
      })}
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
  documentData?: ApiResponse;
}) {
  const [activeFilter, setActiveFilter] = useState('ALL');
  const [selectedClause, setSelectedClause] = useState<Clause | null>(null);
  const [modalOpen, setModalOpen] = useState(false);

  if (!documentData) {
    return (
      <div className="grid place-items-center min-h-screen w-full bg-[#91C8E4] p-4">
        <div className="text-center">
          <div className="animate-spin w-8 h-8 border-4 border-white border-t-transparent rounded-full mx-auto mb-4"></div>
          <p className="text-white">Loading document analysis...</p>
        </div>
      </div>
    );
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

  const handleClauseClick = (clause: Clause) => {
    setSelectedClause(clause);
    setModalOpen(true);
  };

  return (
    <main className="grid place-items-center min-h-screen w-full bg-[#91C8E4] p-4 font-crimson">
      <div className="relative w-full max-w-sm h-[861px] max-h-[90vh] bg-white rounded-[40px] shadow-2xl overflow-hidden border-4 border-blue-200 flex flex-col">

        <header className="px-6 pt-6 pb-2 flex-shrink-0">
          <button onClick={onClose} className="w-20 h-20 rounded-full hover:opacity-90 transition-opacity mb-4">
            <img src="/image.png" alt="Back" className="w-full h-full object-contain" />
          </button>
          <div className="text-center">
            <h1 className="text-xl font-bold text-[#4682A9]">Document Analysis</h1>
            <p className="text-sm text-gray-600">
              {documentData.clauses.length} clauses identified
            </p>
          </div>
        </header>

        <main className="flex-grow px-6 py-4 overflow-y-auto">
          <div className="mb-6">
            <HighlightedText
              text={documentData.structured_text}
              clauses={documentData.clauses}
              onClauseClick={handleClauseClick}
            />
          </div>

          <h3 className="font-semibold text-lg mb-4">Identified Clauses</h3>
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
    </main>
  );
=======
                <footer className="px-6 py-4 bg-white/80 backdrop-blur-sm border-t border-gray-200 flex-shrink-0">
                    <div className="flex justify-around items-center mb-4">
                        <motion.button 
                            animate={{ scale: activeFilter === 'green' ? 1.1 : 1, opacity: activeFilter === 'none' || activeFilter === 'green' ? 1 : 0.6 }}
                            onClick={() => handleFilterClick('green')}
                            className="w-18 h-14 flex ">
                                 <Image src="/green.png" alt="Filter Green" width={72} height={56} className="object-contain" />
                        </motion.button>
                        <motion.button 
                            animate={{ scale: activeFilter === 'purple' ? 1.1 : 1, opacity: activeFilter === 'none' || activeFilter === 'purple' ? 1 : 0.6 }}
                            onClick={() => handleFilterClick('purple')}
                            className="w-18 h-14 flex ">
                                 <Image src="/purple.png" alt="Filter Purple" width={72} height={56} className="object-contain" />
                        </motion.button>
                        <motion.button 
                           animate={{ scale: activeFilter === 'yellow' ? 1.1 : 1, opacity: activeFilter === 'none' || activeFilter === 'yellow' ? 1 : 0.6 }}
                            onClick={() => handleFilterClick('yellow')}
                            className="w-18 h-14 flex ">
                                 <Image src="/yellow.png" alt="Filter Yellow" width={72} height={56} className="object-contain" />
                        </motion.button>
                        <motion.button 
                           animate={{ scale: activeFilter === 'red' ? 1.1 : 1, opacity: activeFilter === 'none' || activeFilter === 'red' ? 1 : 0.6 }}
                            onClick={() => handleFilterClick('red')}
                            className="w-18 h-14 flex ">
                                 <Image src="/alert.png" alt="Filter Red" width={72} height={56} className="object-contain" />
                        </motion.button>
                    </div>
                    <div className={`relative font-crimson-pro`}>
                        <span className="absolute inset-y-0 left-0 flex items-center pl-4 text-gray-400">
                            <SearchIcon />
                        </span>
                        <input 
                            type="text" 
                            placeholder="Ask AI Assistant" 
                            className="w-full py-4 pl-12 pr-16 text-gray-800 bg-[#FFFDF0] rounded-full border border-gray-300 focus:outline-none focus:ring-2 focus:ring-[#4A90E2]"
                            onKeyDown={(e) => { if(e.key === 'Enter') handleSearch()}}
                        />
                        <button
                            onClick={() => handleSearch()}
                            className="absolute inset-y-0 right-0 flex items-center justify-center w-14 h-14 p-2 //bg-[#4A90E2] rounded-full text-white hover:opacity-90 transition"
                        >
                             <Image src="/Frame 21.png" alt="Voice Assistant" width={56} height={56} className="object-contain" />
                        </button>
                    </div>
                </footer>
            </div>
        </main>
    );
>>>>>>> 60967e2 ([feat]: pre deploy frontend push)
}

