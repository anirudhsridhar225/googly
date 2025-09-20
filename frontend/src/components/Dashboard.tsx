"use client";

import { motion, Variants } from "framer-motion";

// --- Icon Components for Dashboard ---
const CameraIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path>
    <circle cx="12" cy="13" r="4"></circle>
  </svg>
);

const UploadIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="mr-2">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
        <polyline points="17 8 12 3 7 8"></polyline>
        <line x1="12" y1="3" x2="12" y2="15"></line>
    </svg>
);

// --- Butterfly Vector Graphic ---
const ButterflyVector = () => (
    <svg width="250" height="150" viewBox="0 0 328 178" fill="none" xmlns="http://www.w3.org/2000/svg" className="absolute top-0 right-0 transform translate-x-8 -translate-y-4 opacity-90">
        <defs>
            <linearGradient id="butterfly-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#A5B68D" />
                <stop offset="50%" stopColor="#FCDC94" />
                <stop offset="100%" stopColor="#FF8A8A" />
            </linearGradient>
        </defs>
        <path d="M208.281 1.74838C209.613 3.32833 210 5.48805 210 7.74954V7.74954C210 10.011 209.613 12.1708 208.281 13.7507L132.551 104.755C131.22 106.335 129.289 107.25 127.273 107.25V107.25C125.257 107.25 123.327 106.335 121.995 104.755L1.71941 1.74838C0.387431 0.168432 -2.1318e-05 -1.99129 -2.1318e-05 -4.25278V-4.25278C-2.1318e-05 -6.51427 0.387431 -8.67399 1.71941 -10.2539L121.995 -113.259C123.327 -114.839 125.257 -115.753 127.273 -115.753V-115.753C129.289 -115.753 131.22 -114.839 132.551 -113.259L208.281 1.74838Z" transform="matrix(0.89, -0.45, -0.45, -0.89, 210, 80)" stroke="url(#butterfly-gradient)" strokeWidth="10" />
    </svg>
);


// The component now correctly accepts an 'onLogout' prop.
export default function Dashboard({ onLogout }: { onLogout: () => void }) {
    
    const containerVariants: Variants = {
        hidden: { opacity: 0 },
        visible: {
            opacity: 1,
            transition: { staggerChildren: 0.15 }
        }
    };

    const itemVariants: Variants = {
        hidden: { opacity: 0, y: 20 },
        visible: {
            opacity: 1, y: 0,
            transition: { duration: 0.5, ease: 'easeOut' }
        }
    };
    
    const cardData = [
        { title: 'Export to OCR', color: '#FF8A8A' },
        { title: 'History', color: '#A5B68D' },
        { title: 'Placeholder', color: '#FCDC94' },
        { title: 'Profile', color: '#AD88C6', action: onLogout }, // Logout action added here
    ];

  return (
    <motion.div
      className="w-full h-full flex flex-col bg-[#91C8E4] p-6 overflow-hidden"
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      <header className="relative flex-shrink-0 z-10">
        <ButterflyVector />
        <motion.p variants={itemVariants} className="font-secondary text-2xl font-extralight tracking-[0.4px]" style={{ lineHeight: '100%' }}>ask</motion.p>
        <motion.h1 variants={itemVariants} className="font-primary text-8xl font-bold -mt-2">Vero</motion.h1>
      </header>

      <motion.p variants={itemVariants} className="font-primary text-white text-6xl font-semibold mt-6 leading-tight tracking-tighter" style={{letterSpacing: '-2px', lineHeight: '90%'}}>
        Cluttered docs, <br />
        clear answers.
      </motion.p>

      <motion.div variants={itemVariants} className="grid grid-cols-2 gap-5 mt-8">
        {cardData.map((card) => (
            <button key={card.title} onClick={card.action} className="rounded-2xl p-4 h-36 flex flex-col justify-between text-left" style={{backgroundColor: card.color}}>
                <div className="w-12 h-12 bg-white/80 rounded-full"></div>
                <p className="font-secondary text-white font-semibold">{card.title}</p>
            </button>
        ))}
      </motion.div>
      
      <div className="flex-grow"></div>

      <motion.footer variants={itemVariants} className="flex-shrink-0 w-full">
            <div className="bg-[#FFFDF0] p-4 rounded-2xl shadow-lg text-center">
                <p className="font-secondary text-sm text-gray-600 mb-3">Start analyzing the document</p>
                <div className="flex items-center justify-center space-x-3">
                    <button className="p-4 rounded-full bg-gray-200 text-[#4682A9] hover:bg-gray-300 transition-colors">
                        <CameraIcon />
                    </button>
                    <button className="flex-grow flex items-center justify-center bg-[#4682A9] text-white py-4 px-6 rounded-full font-secondary font-semibold text-lg hover:opacity-90 transition-opacity">
                        <UploadIcon />
                        Upload
                    </button>
                </div>
            </div>
      </motion.footer>
    </motion.div>
  );
}

