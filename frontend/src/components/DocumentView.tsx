"use client";

import React, { useState, useRef, createRef } from 'react';
import { motion } from 'framer-motion';
import Image from 'next/image';
import type { DocumentData } from '../app/page';

// --- Types ---
type ThreatType = 'green' | 'purple' | 'yellow' | 'red' | 'none';

interface TextSpan {
  id: string;
  text: string;
  type: ThreatType;
}

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
        }
    };

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
}