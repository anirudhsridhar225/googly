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

// --- Card Icons ---
const ExportIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
        <polyline points="14,2 14,8 20,8"></polyline>
        <line x1="16" y1="13" x2="8" y2="13"></line>
        <line x1="16" y1="17" x2="8" y2="17"></line>
    </svg>
);

const HistoryIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10"></circle>
        <polyline points="12,6 12,12 16,14"></polyline>
    </svg>
);

const PlaceholderIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
        <circle cx="8.5" cy="8.5" r="1.5"></circle>
        <polyline points="21,15 16,10 5,21"></polyline>
    </svg>
);

const ProfileIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
        <circle cx="12" cy="7" r="4"></circle>
    </svg>
);

// --- Vector Graphic (PNG with SVG fallback) ---
const VectorGraphic = () => (
    <>
        {/* PNG Vector - correct filename */}
        <img 
            src="/Vector.png" 
            alt="Decorative vector" 
            className="absolute -top-8 -right-8 w-96 h-64 object-contain opacity-90"
            onError={(e) => {
                // Hide broken image if PNG fails to load
                (e.target as HTMLImageElement).style.display = 'none';
            }}
        />
        
        {/* SVG Fallback - similar to your reference image */}
        <svg 
            width="300" 
            height="200" 
            viewBox="0 0 300 200" 
            fill="none" 
            xmlns="http://www.w3.org/2000/svg" 
            className="absolute -top-8 -right-8 opacity-80"
        >
            
            
            {/* Central glow */}
            
        </svg>
    </>
);

// THE FIX: The component now accepts an 'onOpenCamera' prop.
export default function Dashboard({ onLogout, onOpenCamera, onOpenHistory }: { onLogout: () => void; onOpenCamera: () => void; onOpenHistory: () => void; }) {
    
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
        { title: 'Export to OCR', color: '#FF8A8A', icon: <ExportIcon /> },
        { title: 'History', color: '#A5B68D', icon: <HistoryIcon />, action: onOpenHistory },
        { title: 'Placeholder', color: '#FCDC94', icon: <PlaceholderIcon /> },
        { title: 'Profile', color: '#AD88C6', icon: <ProfileIcon />, action: onLogout },
    ];

  return (
    <div className="w-full h-screen bg-[#91C8E4] flex flex-col">
      <motion.div
        className="flex-1 flex flex-col justify-between p-6"
        variants={containerVariants}
        initial="hidden"
        animate="visible"
      >
        {/* Vector at the top */}
        <div className="relative h-20 overflow-visible">
          <VectorGraphic />
        </div>

        {/* Main content section */}
        <div className="flex-1 flex flex-col justify-center">
          {/* Ask text positioned left, avoiding vector */}
          <motion.p variants={itemVariants} className="text-2xl font-extralight tracking-[0.4px] mb-1" style={{ fontFamily: 'Crimson Pro', lineHeight: '100%' }}>ask</motion.p>
          
          {/* Vero title */}
          <motion.h1 variants={itemVariants} className="text-8xl font-thin -mt-2 mb-6  relative z-20" style={{ fontFamily: 'Crimson Text' }}>Vero</motion.h1>

          {/* White tagline text */}
          <motion.p variants={itemVariants} className="text-white text-5xl font-semibold mb-8 leading-tight tracking-tighter" style={{fontFamily: 'Crimson Text', letterSpacing: '-2px', lineHeight: '85%'}}>
            Cluttered docs, <br />
            clear answers.
          </motion.p>

          {/* Cards grid */}
          <motion.div variants={itemVariants} className="grid grid-cols-2 gap-4">
            {cardData.map((card) => (
                <button key={card.title} onClick={card.action} className="rounded-2xl p-6 h-40 flex flex-col items-center justify-center text-center" style={{backgroundColor: card.color}}>
                    <div className="w-14 h-14 bg-white/90 rounded-full flex items-center justify-center text-gray-700 mb-3">
                        {card.icon}
                    </div>
                    <p className="text-gray-800 font-thin text-base" style={{ fontFamily: 'Crimson Pro' }}>{card.title}</p>
                </button>
            ))}
          </motion.div>
        </div>
      </motion.div>

      <motion.footer 
        variants={itemVariants} 
        initial="hidden"
        animate="visible"
        className="bg-[#FFFDF0] p-6"
      >
            <p className="text-sm text-center text-gray-600 mb-4" style={{ fontFamily: 'Crimson Pro' }}>Start analyzing the document</p>
            <div className="flex items-center justify-center space-x-4">
                {/* THE FIX: The camera button now triggers the onOpenCamera function */}
                <button onClick={onOpenCamera} className="p-4 rounded-full bg-[#4682A9] text-white hover:opacity-90 transition-opacity flex items-center justify-center">
                    <CameraIcon />
                </button>
                <button className="flex-grow flex items-center justify-center bg-[#4682A9] text-white py-4 px-6 rounded-full font-semibold text-lg hover:opacity-90 transition-opacity max-w-xs" style={{ fontFamily: 'Crimson Pro' }}>
                    <UploadIcon />
                    Upload
                </button>
            </div>
      </motion.footer>
    </div>
  );
}

