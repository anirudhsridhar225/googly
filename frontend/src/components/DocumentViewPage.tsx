"use client";

import React, { useState, useRef, createRef } from 'react';
import { motion } from 'framer-motion';

// --- Icon Components ---
const CheckIcon = () => <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>;
const ExclamationIcon = () => <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10zM12 8v5"/><path d="M12 17h.01"/></svg>;
const InfoIcon = () => <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>;
const PersonIcon = () => <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>;
const SearchIcon = () => <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>;
const BackIcon = () => <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m12 19-7-7 7-7"/><path d="M19 12H5"/></svg>;

// --- Data Structures ---
type ThreatType = 'green' | 'purple' | 'yellow' | 'red' | 'none';

interface TextSpan {
  id: string;
  text: string;
  type: ThreatType;
}

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
export default function DocumentViewPage({ onClose, documentData }: { onClose: () => void; documentData?: any }) {
    
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

    const handleSearch = (query: string) => {
        const targetId = 't5'; 
        const targetIndex = mockDocument.findIndex(span => span.id === targetId);
        if (targetIndex !== -1 && contentRefs.current[targetIndex].current) {
            contentRefs.current[targetIndex].current?.scrollIntoView({
                behavior: 'smooth',
                block: 'center'
            });
        }
    };

    return (
        <main className={`flex items-center justify-center min-h-screen w-full bg-[#91C8E4] p-4 font-crimson`}>
            <div className="relative w-full max-w-sm h-[861px] max-h-[90vh] bg-[#FFFFFF] rounded-[40px] shadow-2xl overflow-hidden border-4 border-white/50 flex flex-col">
                
                <header className="px-4 pt-4 pb-2 flex-shrink-0">
                    <button 
                        onClick={onClose}
                        className="inline-flex items-center justify-center w-12 h-12 p-2 rounded-full bg-[#4682A9]/10 hover:bg-[#4682A9]/20 transition-colors text-[#4682A9]"
                    >
                        <BackIcon />
                    </button>
                    {documentData && (
                        <div className="mt-2">
                            <p className="text-sm text-gray-600 font-crimson-pro">Viewing:</p>
                            <p className="text-lg font-crimson text-[#4682A9]">{documentData.name}</p>
                        </div>
                    )}
                </header>

                <main className="flex-grow p-6 overflow-y-auto text-lg leading-relaxed text-gray-800">
                    <p>
                        {mockDocument.map((span, index) => (
                            <motion.span
                                key={span.id}
                                ref={contentRefs.current[index]}
                                className="px-1 rounded-md transition-opacity duration-300"
                                animate={{ 
                                    opacity: activeFilter === 'none' || activeFilter === span.type ? 1 : 0.2,
                                    backgroundColor: threatColorMap[span.type]
                                }}
                            >
                                {span.text}
                            </motion.span>
                        ))}
                    </p>
                </main>

                <footer className="p-4 bg-white/80 backdrop-blur-sm border-t border-gray-200 flex-shrink-0">
                    <div className="flex justify-around items-center mb-4">
                        <motion.button 
                            animate={{ scale: activeFilter === 'green' ? 1.1 : 1, opacity: activeFilter === 'none' || activeFilter === 'green' ? 1 : 0.6 }}
                            onClick={() => handleFilterClick('green')}
                            className="w-14 h-14 flex items-center justify-center bg-[#A5B68D] rounded-2xl shadow-md"><CheckIcon /></motion.button>
                        <motion.button 
                            animate={{ scale: activeFilter === 'purple' ? 1.1 : 1, opacity: activeFilter === 'none' || activeFilter === 'purple' ? 1 : 0.6 }}
                            onClick={() => handleFilterClick('purple')}
                            className="w-14 h-14 flex items-center justify-center bg-[#AD88C6] rounded-2xl shadow-md"><ExclamationIcon /></motion.button>
                        <motion.button 
                           animate={{ scale: activeFilter === 'yellow' ? 1.1 : 1, opacity: activeFilter === 'none' || activeFilter === 'yellow' ? 1 : 0.6 }}
                            onClick={() => handleFilterClick('yellow')}
                            className="w-14 h-14 flex items-center justify-center bg-[#FCDC94] rounded-2xl shadow-md"><InfoIcon /></motion.button>
                        <motion.button 
                           animate={{ scale: activeFilter === 'red' ? 1.1 : 1, opacity: activeFilter === 'none' || activeFilter === 'red' ? 1 : 0.6 }}
                            onClick={() => handleFilterClick('red')}
                            className="w-14 h-14 flex items-center justify-center bg-[#FF8A8A] rounded-2xl shadow-md"><PersonIcon /></motion.button>
                    </div>
                    <div className={`relative font-crimson-pro`}>
                        <span className="absolute inset-y-0 left-0 flex items-center pl-4 text-gray-400">
                            <SearchIcon />
                        </span>
                        <input 
                            type="text" 
                            placeholder="Ask AI Assistant" 
                            className="w-full py-4 pl-12 pr-16 text-gray-800 bg-[#FFFDF0] rounded-full border border-gray-300 focus:outline-none focus:ring-2 focus:ring-[#4A90E2]"
                            onKeyDown={(e) => { if(e.key === 'Enter') handleSearch(e.currentTarget.value)}}
                        />
                        <button 
                            onClick={() => handleSearch('find deadline')}
                            className="absolute inset-y-0 right-0 flex items-center justify-center w-14 h-14 p-2 bg-[#4A90E2] rounded-full text-white hover:opacity-90 transition"
                        >
                            <img src="/voice-button.png" alt="Voice Assistant" className="w-full h-full object-contain" />
                        </button>
                    </div>
                </footer>
            </div>
        </main>
    );
}