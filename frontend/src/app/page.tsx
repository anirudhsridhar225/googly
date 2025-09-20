"use client";

import { useState, useRef, useLayoutEffect } from "react";
import { motion, AnimatePresence, Variants, Transition } from "framer-motion";

// --- 1. Reusable Icon Components (Unchanged) ---
const UserIcon = () => <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>;
const MailIcon = () => <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path><polyline points="22,6 12,13 2,6"></polyline></svg>;
const LockIcon = () => <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>;
const EyeIcon = () => <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>;
const GoogleIcon = () => <svg className="w-6 h-6" viewBox="0 0 24 24"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/><path fill="none" d="M1 1h22v22H1z"/></svg>;


// --- 2. FINAL, DYNAMIC & RESPONSIVE Animated Swirl Background ---

type Dimensions = { width: number; height: number; };
type Stroke = { d: string; color: string; delay: number; };

const Stripe = ({ d, color, delay }: Stroke) => (
  <motion.path
    d={d}
    stroke={color}
    strokeWidth="40"
    fill="none"
    strokeLinecap="round"
    initial={{ pathLength: 0, opacity: 0 }}
    animate={{ pathLength: 1, opacity: 1 }}
    transition={{
      pathLength: { duration: 2.5, ease: "easeInOut", delay },
      opacity: { duration: 1.5, ease: "linear", delay },
    }}
  />
);

const Background = ({ containerSize }: { containerSize: Dimensions }) => {
    const [strokes, setStrokes] = useState<Stroke[]>([]);

    useLayoutEffect(() => {
        if (containerSize.width > 0 && containerSize.height > 0) {
            const { width, height } = containerSize;
            
            const strokeColors = ["#A5B68D", "#AD88C6", "#FCDC94", "#FF8A8A"];
            const generatedStrokes: Stroke[] = [];
            const numStrokes = 4;
            const verticalSpacing = height * 0.09; 
            const horizontalPadding = 150;
            const textSafeZone = height * 0.35; 
            const topBlockHeight = (height - textSafeZone) / 2;

            // Generate Top Strokes
            for (let i = 0; i < numStrokes; i++) {
                const yStart = topBlockHeight - (i * verticalSpacing);
                generatedStrokes.push({
                    d: `M ${width + horizontalPadding} ${yStart - 20} C ${width * 0.7} ${yStart}, ${width * 0.3} ${yStart - 100}, ${-horizontalPadding} ${yStart - 60}`,
                    color: strokeColors[i],
                    delay: 0.2 * i
                });
            }

            // Generate Bottom Strokes
            for (let i = 0; i < numStrokes; i++) {
                 const yStart = height - ((3 - i) * verticalSpacing) - 60; 
                 generatedStrokes.push({
                    d: `M ${-horizontalPadding} ${yStart} C ${width * 0.3} ${yStart + 40}, ${width * 0.7} ${yStart - 100}, ${width + horizontalPadding} ${yStart - 40}`,
                    color: strokeColors[i], 
                    delay: 0.2 * i
                });
            }
            setStrokes(generatedStrokes);
        }
    }, [containerSize]);

    return (
        <svg
            viewBox={`-170 -80 ${containerSize.width + 340} ${containerSize.height + 160}`}
            preserveAspectRatio="xMidYMid slice"
            className="absolute inset-0 w-full h-full"
        >
            {strokes.map((stroke, index) => (
                <Stripe key={index} {...stroke} />
            ))}
        </svg>
    );
};

// New component for the stylized logo behind "Vero"
const VeroLogo = () => {
    const rays = [
        { angle: -150, color: '#FF8A8A' }, { angle: -135, color: '#FF8A8A' },
        { angle: -120, color: '#FCDC94' }, { angle: -105, color: '#FCDC94' },
        { angle: -75, color: '#AD88C6' }, { angle: -60, color: '#AD88C6' },
        { angle: -45, color: '#A5B68D' }, { angle: -30, color: '#A5B68D' },
        { angle: 30, color: '#A5B68D' }, { angle: 45, color: '#A5B68D' },
        { angle: 60, color: '#AD88C6' }, { angle: 75, color: '#AD88C6' },
        { angle: 105, color: '#FCDC94' }, { angle: 120, color: '#FCDC94' },
        { angle: 135, color: '#FF8A8A' }, { angle: 150, color: '#FF8A8A' },
    ];
    return (
        <svg width="200" height="100" viewBox="0 0 200 100" className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 opacity-80">
            <g transform="translate(100, 50)">
                {rays.map((ray, i) => (
                    <line 
                        key={i} 
                        x1="25" y1="0" 
                        x2="80" y2="0" 
                        stroke={ray.color} 
                        strokeWidth="5" 
                        strokeLinecap="round"
                        transform={`rotate(${ray.angle})`} 
                    />
                ))}
            </g>
        </svg>
    )
};


// --- 3. Main Page Component ---
export default function Home() {
    const [view, setView] = useState<'landing' | 'choice' | 'signup' | 'login'>('landing');
    
    const sectionRef = useRef<HTMLElement>(null);
    const [containerSize, setContainerSize] = useState<Dimensions>({ width: 0, height: 0 });

    useLayoutEffect(() => {
        const observer = new ResizeObserver(() => {
            if (sectionRef.current) {
                const { width, height } = sectionRef.current.getBoundingClientRect();
                setContainerSize({ width, height });
            }
        });
        if (sectionRef.current) observer.observe(sectionRef.current);
        return () => observer.disconnect();
    }, [view]);

    const viewVariants: Variants = {
        initial: { opacity: 0, y: 30 },
        animate: { opacity: 1, y: 0 },
        exit: { opacity: 0, y: -30 },
    };
    
    const transition: Transition = { 
        duration: 0.5, 
        ease: "easeInOut" 
    };

    const getTopSectionHeight = () => {
        switch (view) {
            case 'landing': return '75%';
            case 'choice': return '60%';
            case 'signup': case 'login': return '50%';
            default: return '60%';
        }
    };

    const AuthInput = ({ type, placeholder, icon, hasEye }: { type: string; placeholder: string; icon: React.ReactNode; hasEye?: boolean; }) => (
        <div className="relative w-full mb-4">
            <span className="absolute inset-y-0 left-0 flex items-center pl-5 text-gray-500">{icon}</span>
            <input type={type} placeholder={placeholder} className="w-full py-3 pl-14 pr-12 text-[#333333] bg-white rounded-full border-0 focus:outline-none focus:ring-2 focus:ring-[#4682A9] placeholder-gray-400" />
            {hasEye && <button className="absolute inset-y-0 right-0 flex items-center pr-5 text-gray-500"><EyeIcon /></button>}
        </div>
    );

    const renderContent = () => {
        switch (view) {
            case 'landing':
                return (
                    <motion.div key="landing" variants={viewVariants} transition={transition} initial="initial" animate="animate" exit="exit" className="w-full text-center">
                        <p className="font-secondary mb-6 text-white text-sm max-w-xs mx-auto">Sign in to upload, analyze, and ask questions–all secure, all private</p>
                        <button onClick={() => setView('choice')} className="font-secondary w-full max-w-sm bg-[#4682A9] text-white py-3 rounded-full text-lg font-semibold shadow-lg hover:opacity-90 transition-opacity">Continue</button>
                    </motion.div>
                );
            case 'choice':
                return (
                    <motion.div key="choice" variants={viewVariants} transition={transition} initial="initial" animate="animate" exit="exit" className="w-full text-center flex flex-col items-center">
                        <button className="font-secondary w-full max-w-sm bg-white text-gray-700 py-3 rounded-full text-base font-medium shadow-lg hover:bg-gray-50 transition flex items-center justify-center mb-4"><GoogleIcon /><span className="ml-3">Continue with Google</span></button>
                        <div className="flex items-center w-full max-w-sm my-3"><hr className="flex-grow border-t border-white/50" /><span className="font-secondary px-3 text-sm text-white/90">OR</span><hr className="flex-grow border-t border-white/50" /></div>
                        <button onClick={() => setView('signup')} className="font-secondary w-full max-w-sm bg-[#4682A9] text-white py-3 rounded-full text-lg font-semibold shadow-lg hover:opacity-90 transition-opacity mt-3">Create Account</button>
                        <p className="font-secondary text-sm text-white mt-10">Already have an account? <button onClick={() => setView('login')} className="font-bold text-white hover:underline">Log In</button></p>
                    </motion.div>
                );
            case 'signup':
                return (
                    <motion.div key="signup" variants={viewVariants} transition={transition} initial="initial" animate="animate" exit="exit" className="w-full max-w-sm">
                        <h3 className="font-secondary text-3xl font-bold text-white mb-6 text-center">Create Account</h3>
                        <AuthInput type="text" placeholder="Full Name" icon={<UserIcon />} />
                        <AuthInput type="email" placeholder="Email Address" icon={<MailIcon />} />
                        <AuthInput type="password" placeholder="Password" icon={<LockIcon />} hasEye />
                        <button className="font-secondary w-full bg-[#4682A9] text-white py-3 rounded-full text-lg font-semibold shadow-lg hover:opacity-90 transition-opacity mt-2">Create Account</button>
                        <p className="font-secondary text-xs text-white/80 text-center mt-4 max-w-xs mx-auto">By signing up, you agree to our Terms, Privacy Policy, and Cookie Use.</p>
                    </motion.div>
                );
            case 'login':
                return (
                    <motion.div key="login" variants={viewVariants} transition={transition} initial="initial" animate="animate" exit="exit" className="w-full max-w-sm">
                        <h3 className="font-secondary text-3xl font-bold text-white mb-6 text-center">Login</h3>
                        <AuthInput type="email" placeholder="Email Address" icon={<MailIcon />} />
                        <AuthInput type="password" placeholder="Password" icon={<LockIcon />} hasEye />
                         <div className="text-right w-full pr-2 mb-2"><a href="#" className="font-secondary text-sm text-white hover:underline">Forgot Password?</a></div>
                        <button className="font-secondary w-full bg-[#4682A9] text-white py-3 rounded-full text-lg font-semibold shadow-lg hover:opacity-90 transition-opacity mt-3">Login</button>
                    </motion.div>
                );
        }
    };

    return (
        <>
            {/* Component to inject Google Fonts */}
            <style jsx global>{`
                @import url('https://fonts.googleapis.com/css2?family=Crimson+Pro:ital,wght@0,400;0,700;1,400&family=Crimson+Text:ital,wght@0,400;0,700;1,400&display=swap');
                
                .font-primary {
                    font-family: 'Crimson Text', serif;
                }

                .font-secondary {
                    font-family: 'Crimson Pro', serif;
                }
            `}</style>
            <main className="w-screen h-screen bg-[#FAF6D0] flex items-center justify-center sm:p-4">
                <div className="relative w-full h-full sm:max-w-sm sm:max-h-[850px] flex flex-col bg-[#FFFDF0] sm:rounded-[40px] sm:shadow-2xl overflow-hidden">
                    
                    <motion.section
                        ref={sectionRef}
                        className="relative px-6 flex-shrink-0"
                        animate={{ height: getTopSectionHeight() }}
                        transition={{ duration: 0.8, ease: [0.4, 0, 0.2, 1] }}
                    >
                        <div className="absolute inset-0 z-0">
                            <Background containerSize={containerSize} />
                        </div>
                        <div className="relative z-10 h-full flex flex-col items-center justify-center">
                            <div className="text-center">
                                {/* New Title Design */}
                                <h1 className="font-secondary text-4xl text-[#333333] tracking-wider">ask</h1>
                                <div className="relative -mt-6">
                                    <VeroLogo />
                                    <h2 className="relative font-primary text-8xl font-bold text-[#333333]">Vero</h2>
                                </div>
                                <p className="font-secondary italic text-[#555555] mt-2 text-sm">“Proofread. Analyze. Simplified.”</p>
                            </div>
                        </div>
                    </motion.section>

                    <section className="relative flex-grow flex flex-col items-center justify-center p-6 bg-[#91C8E4]">
                        <div className="w-full flex items-center justify-center">
                            <AnimatePresence mode="wait">
                                {renderContent()}
                            </AnimatePresence>
                        </div>
                    </section>
                </div>
            </main>
        </>
    );
}

