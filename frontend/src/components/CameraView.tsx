"use client";

import { motion } from "framer-motion";
import { useEffect, useRef, useState } from "react";

// --- Icon Components for Camera View ---
const FolderIcon = () => <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>;
const CameraCaptureIcon = () => <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path><circle cx="12" cy="13" r="4"></circle></svg>;
const CheckIcon = () => <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>;

// --- REFINED Background Component ---
const Stripe = ({ d, color, delay, width }: { d: string; color: string; delay: number; width: number; }) => (
  <motion.path
    d={d}
    stroke={color}
    strokeWidth={width}
    fill="none"
    strokeLinecap="round"
    initial={{ pathLength: 0, opacity: 0 }}
    animate={{ pathLength: 1, opacity: 1 }} // Darker, fully opaque strokes
    transition={{
      pathLength: { duration: 2.8, ease: "circOut", delay },
      opacity: { duration: 2, ease: "linear", delay },
    }}
  />
);

const Background = () => {
    // New refined paths that start from a line off-screen and have more inclined curves.
    const strokes = [
        { d: "M 0 900 C 0 650, -20 400, -50 300", color: "#A5B68D", delay: 0.0, width: 55 },
        { d: "M 133 900 C 133 600, 100 200, 100 -50", color: "#AD88C6", delay: 0.2, width: 55 },
        { d: "M 266 900 C 266 600, 300 200, 300 -50", color: "#FCDC94", delay: 0.4, width: 55 },
        { d: "M 400 900 C 400 650, 420 400, 450 300", color: "#FF8A8A", delay: 0.6, width: 55 },
    ];

    return (
        <svg
            viewBox="-50 -50 500 950" // Adjusted viewBox to hide the starting line
            preserveAspectRatio="xMidYMid slice"
            className="absolute inset-0 w-full h-full"
        >
            {strokes.map((stroke, index) => (
                <Stripe key={index} {...stroke} />
            ))}
        </svg>
    );
};


export default function CameraView({ onClose }: { onClose: () => void; }) {
    const videoRef = useRef<HTMLVideoElement>(null);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        let mediaStream: MediaStream;

        const enableCamera = async () => {
            try {
                // Request access to the user's camera
                mediaStream = await navigator.mediaDevices.getUserMedia({
                    video: { facingMode: "environment" } // Prefer the rear camera
                });
                if (videoRef.current) {
                    videoRef.current.srcObject = mediaStream;
                }
            } catch (err) {
                console.error("Error accessing camera:", err);
                setError("Could not access camera. Please check permissions.");
            }
        };

        enableCamera();

        // Cleanup function to stop the camera stream when the component unmounts
        return () => {
            if (mediaStream) {
                mediaStream.getTracks().forEach(track => track.stop());
            }
        };
    }, []);

    return (
        <div className="w-full h-full flex flex-col bg-[#FFFDF0] relative overflow-hidden">
            <div className="absolute inset-0 z-0">
                <Background />
            </div>
            
            <div className="relative flex-grow flex items-center justify-center p-8 z-10">
                <div className="w-full h-full bg-black rounded-3xl flex items-center justify-center overflow-hidden">
                    {/* The video element will display the camera feed */}
                    <video 
                        ref={videoRef} 
                        autoPlay 
                        playsInline 
                        className="w-full h-full object-cover"
                    />
                    {/* Display an error message if the camera fails */}
                    {error && (
                         <div className="absolute inset-0 flex items-center justify-center p-4">
                            <span className="font-secondary text-lg text-red-500 text-center">{error}</span>
                        </div>
                    )}
                </div>
            </div>

            <footer className="relative flex-shrink-0 w-full flex items-center justify-evenly p-6 z-10">
                <button className="p-4 rounded-full bg-[#4682A9]/20 text-[#4682A9] hover:bg-[#4682A9]/30 transition-colors">
                    <FolderIcon />
                </button>
                <button className="p-5 rounded-full bg-[#4682A9] text-white shadow-lg hover:opacity-90 transition-opacity">
                    <CameraCaptureIcon />
                </button>
                <button onClick={onClose} className="p-4 rounded-full bg-[#4682A9]/20 text-[#4682A9] hover:bg-[#4682A9]/30 transition-colors">
                    <CheckIcon />
                </button>
            </footer>
        </div>
    );
}

