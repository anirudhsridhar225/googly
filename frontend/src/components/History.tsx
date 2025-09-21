"use client";

import { useState, useMemo } from "react";
import { motion, Variants } from "framer-motion";
import { ApiResponse, HistoryItem } from "../types";

// --- Icon Components for History View ---
const SearchIcon = () => <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>;
const SortIcon = () => <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 6h18M7 12h10M10 18h4M3 6l3 3M21 6l-3 3" /></svg>;

export default function History({ onClose, onOpenDocument }: { onClose: () => void; onOpenDocument: (documentData: ApiResponse | null) => void }) {
    const [selectedId, setSelectedId] = useState(1);
    const [searchTerm, setSearchTerm] = useState("");
    const [sortOrder, setSortOrder] = useState<"recent" | "alpha">("recent");

    const historyItems: HistoryItem[] = [
        { id: 1, name: "House_agreement.pdf", date: new Date("2024-09-12T10:00:00Z"), tag: "Most Recent" },
        { id: 2, name: "Apartment_lease.pdf", date: new Date("2024-09-10T15:30:00Z") },
        { id: 3, name: "Car_insurance.pdf", date: new Date("2024-08-22T11:00:00Z") },
        { id: 4, name: "Business_proposal.pdf", date: new Date("2024-08-15T09:00:00Z") },
        { id: 5, name: "Final_thesis.pdf", date: new Date("2024-07-30T18:00:00Z") },
    ];

export default function History({ onClose, onOpenDocument }: { onClose: () => void; onOpenDocument: (documentData?: DocumentData) => void }) {
	const [selectedId, setSelectedId] = useState(1);
	const [searchTerm, setSearchTerm] = useState("");
	const [sortOrder, setSortOrder] = useState<"recent" | "alpha">("recent");

<<<<<<< Updated upstream
	// Memoized calculation for filtering and sorting
	const filteredAndSortedItems = useMemo(() => {
		const historyItems = [
			{ id: 1, name: "House_agreement.pdf", date: new Date("2024-09-12T10:00:00Z"), tag: "Most Recent" },
			{ id: 2, name: "Apartment_lease.pdf", date: new Date("2024-09-10T15:30:00Z") },
			{ id: 3, name: "Car_insurance.pdf", date: new Date("2024-08-22T11:00:00Z") },
			{ id: 4, name: "Business_proposal.pdf", date: new Date("2024-08-15T09:00:00Z") },
			{ id: 5, name: "Final_thesis.pdf", date: new Date("2024-07-30T18:00:00Z") },
		];

    // Memoized calculation for filtering and sorting
    const filteredAndSortedItems = useMemo(() => {
        const items = historyItems
            // Filter based on search term
            .filter(item =>
                item.name.toLowerCase().includes(searchTerm.toLowerCase())
            );

        // Sort based on the current sort order
        if (sortOrder === 'alpha') {
            return [...items].sort((a, b) => a.name.localeCompare(b.name));
        } else {
            // Default to sorting by most recent date
            return [...items].sort((a, b) => b.date.getTime() - a.date.getTime());
        }
    }, [searchTerm, sortOrder]);

    const containerVariants: Variants = {
        hidden: { opacity: 0 },
        visible: {
            opacity: 1,
            transition: { staggerChildren: 0.1 }
        }
    };

    const itemVariants: Variants = {
        hidden: { opacity: 0, x: -20 },
        visible: {
            opacity: 1, x: 0,
            transition: { duration: 0.5, ease: 'easeOut' }
        }
    };

    const handleViewDocument = (item: HistoryItem) => {
        // Mock API response for prototype
        const mockApiResponse: ApiResponse = {
            id: item.id.toString(),
            name: item.name,
            structured_text: `# Sample Contract Document

This is a sample document for ${item.name}.

## Section 1
Some legal text here.

## Section 2
More content.`,
            clauses: [
                {
                    clause_text: "Some legal text here.",
                    severity: "HIGH",
                    category: "Contract Terms",
                    explanation: "This clause may have high risk implications.",
                    suggested_action: "Review carefully."
                }
            ]
        };
        onOpenDocument(mockApiResponse);
    };

	const itemVariants: Variants = {
		hidden: { opacity: 0, x: -20 },
		visible: {
			opacity: 1, x: 0,
			transition: { duration: 0.5, ease: 'easeOut' }
		}
	};

	return (
		<div className="w-full h-full flex flex-col bg-[#FFFDF0] p-6">
			<motion.header
				initial={{ opacity: 0, y: -20 }}
				animate={{ opacity: 1, y: 0 }}
				transition={{ duration: 0.5 }}
				className="flex-shrink-0 flex items-center mb-6"
			>
				<button
					onClick={onClose}
					className="w-20 h-20 rounded-full hover:opacity-90 transition-opacity"
				>
					<Image src="/image.png" alt="Back button" width={80} height={80} className="object-contain" />
				</button>
			</motion.header>

			<motion.div
				variants={containerVariants}
				initial="hidden"
				animate="visible"
				className="flex-grow flex flex-col"
			>
				<motion.div variants={itemVariants} className="flex items-end justify-between mb-4">
					<h1 className="font-crimson italic thin text-6xl font-thin text-[#4682A9]">History</h1>
					<button onClick={() => setSearchTerm("")} className="font-secondary text-xl italic text-[#4682A9] hover:text-[#3a6a8a] transition-colors">Clear</button>
				</motion.div>

				<motion.div variants={itemVariants} className="relative flex items-center mb-6">
					<div className="absolute left-4 text-[#4682A9]">
						<SearchIcon />
					</div>
					<input
						type="text"
						placeholder="Search"
						value={searchTerm}
						onChange={(e) => setSearchTerm(e.target.value)}
						className="w-full bg-[#EFEFEF] border-[#4682A9] rounded-full py-3 pl-12 pr-10 font-crimson-pro italic bold text-[#4682A9] focus:ring-2 focus:ring-[#4682A9]"
					/>
					<button
						onClick={() => setSortOrder(prev => prev === 'recent' ? 'alpha' : 'recent')}
						className="absolute right-4 text-[#4682A9] hover:text-gray-800 transition-colors"
						title={`Sort by ${sortOrder === 'recent' ? 'Alphabetical' : 'Most Recent'}`}
					>
						<SortIcon />
					</button>
				</motion.div>

				<div className="flex-grow overflow-y-auto pr-2 space-y-3">
					{filteredAndSortedItems.map(item => {
						const isSelected = item.id === selectedId;
						return (
							<motion.div
								key={item.id}
								layout // Animate layout changes when list reorders
								variants={itemVariants}
								onClick={() => setSelectedId(item.id)}
								className={`p-4 rounded-2xl cursor-pointer transition-colors duration-300 ${isSelected ? 'bg-[#4682A9] text-white' : 'bg-[#91C8E4]/50 text-gray-700'}`}
							>
								<div className="flex items-center justify-between">
									<div>
										<p className="font-secondary text-xs opacity-80 mb-1">File Name</p>
										<p className={`font-primary-crimson font-thin text-xl ${isSelected ? 'text-white' : 'text-[#40404099]'}`}>{item.name}</p>
									</div>
									<button
										onClick={(e) => {
											e.stopPropagation();
											handleViewDocument(item);
										}}
										className={`font-secondary-crimson pro font-thin py-2 px-6 rounded-full transition-colors duration-300 ${isSelected ? 'bg-white text-[#4682A9]' : 'bg-[#4682A9] text-white'}`}
									>
										View
									</button>
								</div>
								<div className="mt-2 flex items-center justify-between text-xs opacity-80">
									<p>Date Scanned</p>
									<p>{item.date.toLocaleDateString()} {item.tag && <span className="font-bold ml-1">{`(${item.tag})`}</span>}</p>
								</div>
							</motion.div>
						);
					})}
				</div>
			</motion.div>
		</div>
	);
}