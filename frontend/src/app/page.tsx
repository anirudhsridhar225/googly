"use client";

import { motion } from "framer-motion";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col bg-[#FEF9E7]">
      {/* Top Spiral Section */}
      <section className="relative flex flex-grow flex-col items-center justify-center p-6">
        {/* Spiral Placeholder - later replace with SVG */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 2 }}
          className="absolute top-0 left-0 w-full h-full -z-10"
        >
          <div className="bg-gradient-to-r from-[#FFCE73] via-[#E57373] to-[#BA68C8] w-full h-full opacity-60"></div>
        </motion.div>

        <h1 className="text-5xl font-bold text-[#333] mb-3">Welcome to</h1>
        <h2 className="text-6xl font-extrabold text-[#333]">Googly</h2>
        <p className="italic text-[#555] mt-2">“Proofread. Analyze. Simplified.”</p>
      </section>

      {/* Bottom Blue Section */}
      <section className="bg-[#B0D9F6] rounded-t-3xl px-6 py-8 flex flex-col items-center">
        <p className="text-sm text-[#444] text-center mb-6">
          Sign in to upload, analyze, and ask questions – all secure, all private
        </p>

        <button className="w-full bg-[#4A90E2] text-white py-3 rounded-full text-lg font-medium shadow-lg hover:opacity-90 transition">
          Continue
        </button>
      </section>
    </main>
  );
}
