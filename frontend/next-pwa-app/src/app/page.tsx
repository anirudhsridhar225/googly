"use client";

import { motion } from "framer-motion";

export default function Home() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-[#fef9e7] relative">
      {/* Spiral Animation */}
      <motion.div
        className="absolute top-0 left-0 w-full h-full -z-10"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 2 }}
      >
        {/* Replace with real spiral SVGs later */}
        <div className="bg-gradient-to-r from-yellow-300 via-pink-400 to-purple-400 w-full h-full opacity-60"></div>
      </motion.div>

      <div className="w-full max-w-sm text-center p-6">
        <h1 className="text-4xl font-bold mb-2">Welcome to Googly</h1>
        <p className="italic mb-6">“Proofread. Analyze. Simplified.”</p>

        <button className="bg-blue-400 text-white w-full py-3 rounded-full font-medium shadow-md">
          Continue
        </button>
      </div>
    </main>
  );
}