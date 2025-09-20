"use client";

import { motion, Variants } from "framer-motion";

// THE FIX: This component now accepts an 'onComplete' prop.
export default function Onboarding({ onComplete }: { onComplete: () => void; }) {
  const containerVariants: Variants = {
    hidden: { opacity: 0 },
    visible: { 
      opacity: 1,
      transition: { staggerChildren: 0.3, delayChildren: 0.2 }
    },
  };

  const itemVariants: Variants = {
    hidden: { opacity: 0, y: 20 },
    visible: { 
      opacity: 1, y: 0,
      transition: { duration: 0.5, ease: "easeOut" }
    },
  };

  return (
    <motion.div 
      className="w-full h-full flex flex-col items-center justify-center p-8 bg-[#91C8E4]"
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      <motion.div 
        className="w-full max-w-sm"
        variants={itemVariants}
      >
        <div className="p-1.5 rounded-[30px]" style={{ backgroundImage: 'conic-gradient(from 180deg at 50% 50%, #A5B68D 0deg, #AD88C6 90deg, #FCDC94 180deg, #FF8A8A 270deg, #A5B68D 360deg)' }}>
          <div className="bg-[#FFFDF0] w-full h-[550px] rounded-[24px] flex items-center justify-center">
            <span className="font-secondary text-2xl text-gray-400">
              [Tutorial video]
            </span>
          </div>
        </div>
      </motion.div>

      <motion.button 
        onClick={onComplete}
        className="font-secondary mt-8 w-full max-w-sm bg-white text-[#4682A9] py-4 rounded-full text-lg font-semibold shadow-lg hover:bg-gray-100 transition-colors flex items-center justify-center"
        variants={itemVariants}
      >
        Continue
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="ml-2"><polyline points="9 18 15 12 9 6"></polyline></svg>
      </motion.button>
    </motion.div>
  );
}

