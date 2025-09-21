"use client";

import { useState, useMemo } from "react";
import { motion, Variants } from "framer-motion";
import Image from "next/image";

// --- Icon Components for History View ---
const SearchIcon = () => <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>;
const SortIcon = () => <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 6h18M7 12h10M10 18h4M3 6l3 3M21 6l-3 3" /></svg>;

interface DocumentData {
	id: number
	name: string
	date: Date
	tag?: string
}

export default function History({ onClose, onOpenDocument }: { onClose: () => void; onOpenDocument: (documentData?: DocumentData) => void }) {
	const [selectedId, setSelectedId] = useState(1);
	const [searchTerm, setSearchTerm] = useState("");
	const [sortOrder, setSortOrder] = useState<"recent" | "alpha">("recent");

	// Memoized calculation for filtering and sorting
	const filteredAndSortedItems = useMemo(() => {
		const historyItems = [
			{ id: 1, name: "House_agreement.pdf", date: new Date("2024-09-12T10:00:00Z"), tag: "Most Recent" },
			{ id: 2, name: "Apartment_lease.pdf", date: new Date("2024-09-10T15:30:00Z") },
			{ id: 3, name: "Car_insurance.pdf", date: new Date("2024-08-22T11:00:00Z") },
			{ id: 4, name: "Business_proposal.pdf", date: new Date("2024-08-15T09:00:00Z") },
			{ id: 5, name: "Final_thesis.pdf", date: new Date("2024-07-30T18:00:00Z") },
		];

		const items = historyItems
			// Filter based on search term
			.filter(item =>
				item.name.toLowerCase().includes(searchTerm.toLowerCase())
			);

		// Sort based on the current sort order
		if (sortOrder === 'alpha') {
			items.sort((a, b) => a.name.localeCompare(b.name));
		} else {
			// Default to sorting by most recent date
			items.sort((a, b) => b.date.getTime() - a.date.getTime());
		}

		return items;
	}, [searchTerm, sortOrder]);

<<<<<<< HEAD
    const handleViewDocument = (item: any) => {
        // Mock API response for prototype
        const mockApiResponse = {
            structured_text: `# Sample Contract Document

This is a sample legal document for demonstration purposes. The following clause contains potential issues that should be reviewed carefully.

Any invention or work developed by Employee during the course of employment and related to Employer's business shall belong to Employer. This includes all intellectual property rights, patents, copyrights, and trade secrets.

The employee agrees to indemnify and hold harmless the Employer from any claims, damages, or liabilities arising from the employee's actions during employment.

This agreement shall remain in effect for a period of 2 years following termination of employment, during which time the employee shall not engage in any competitive business activities.

The employer reserves the right to modify these terms at any time with 30 days written notice to the employee.

All disputes shall be resolved through binding arbitration in the state of California under the rules of the American Arbitration Association.

The employee acknowledges that they have read and understood all terms of this agreement and agree to be bound by them.`,
            clauses: [
                {
                    clause_text: "Any invention or work developed by Employee during the course of employment and related to Employer's business shall belong to Employer.",
                    start_position: 171,
                    end_position: 307,
                    severity: "HIGH",
                    category: "Intellectual Property",
                    explanation: "This clause grants the Employer broad ownership of any invention or work developed by the Employee during their employment, even if it's outside of their core responsibilities or created during personal time. This could stifle the Employee's creativity and future opportunities.",
                    suggested_action: "Request to narrow the scope of the clause to inventions directly related to the Employee's assigned duties and developed using company resources. Propose adding language that inventions created outside of work hours or unrelated to the company's business remain the Employee's property."
                },
                {
                    clause_text: "The employee agrees to indemnify and hold harmless the Employer from any claims, damages, or liabilities arising from the employee's actions during employment.",
                    start_position: 397,
                    end_position: 556,
                    severity: "MEDIUM",
                    category: "Liability & Risk",
                    explanation: "This indemnification clause requires the employee to cover the employer's legal costs and damages for any claims arising from their employment actions, which could be overly broad and unfair.",
                    suggested_action: "Limit the indemnification to actions performed within the scope of employment and in good faith. Consider mutual indemnification or caps on liability amounts."
                },
                {
                    clause_text: "This agreement shall remain in effect for a period of 2 years following termination of employment, during which time the employee shall not engage in any competitive business activities.",
                    start_position: 558,
                    end_position: 744,
                    severity: "HIGH",
                    category: "Confidentiality & Restrictions",
                    explanation: "This non-compete clause extends for 2 years after employment ends and broadly prohibits 'competitive business activities' without geographic or scope limitations, which may be overly restrictive and unenforceable in many jurisdictions.",
                    suggested_action: "Reduce the time period to 6-12 months, define specific geographic limitations, and clearly define what constitutes 'competitive business activities' related to the employee's specific role."
                },
                {
                    clause_text: "The employer reserves the right to modify these terms at any time with 30 days written notice to the employee.",
                    start_position: 746,
                    end_position: 856,
                    severity: "MEDIUM",
                    category: "Modification & Control",
                    explanation: "This unilateral modification clause allows the employer to change terms with only 30 days notice, which could disadvantage the employee significantly.",
                    suggested_action: "Require mutual agreement for material changes, or limit modifications to non-essential terms. Consider requiring employee consent for significant changes."
                },
                {
                    clause_text: "All disputes shall be resolved through binding arbitration in the state of California under the rules of the American Arbitration Association.",
                    start_position: 858,
                    end_position: 1000,
                    severity: "LOW",
                    category: "Dispute Resolution",
                    explanation: "This arbitration clause is relatively standard but forces resolution outside of court, which may limit the employee's access to legal remedies.",
                    suggested_action: "This is generally acceptable, but consider adding language that preserves the right to seek injunctive relief in court for certain claims."
                }
            ]
        };
        onOpenDocument(mockApiResponse);
    };
=======
	const containerVariants: Variants = {
		hidden: { opacity: 0 },
		visible: {
			opacity: 1,
			transition: { staggerChildren: 0.1 }
		}
	};
>>>>>>> 60967e2 ([feat]: pre deploy frontend push)

	const itemVariants: Variants = {
		hidden: { opacity: 0, x: -20 },
		visible: {
			opacity: 1, x: 0,
			transition: { duration: 0.5, ease: 'easeOut' }
		}
	};

	const handleViewDocument = (item: { id: number; name: string; date: Date; tag?: string }) => {
		onOpenDocument(item);
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
