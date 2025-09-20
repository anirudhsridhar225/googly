"use client";

import { useState } from 'react';
import Auth from '../components/Auth';
import Onboarding from '../components/Onboarding';
import Dashboard from '../components/Dashboard';

export default function Home() {
  // This state now controls the entire application flow.
  const [appState, setAppState] = useState<'auth' | 'onboarding' | 'dashboard'>('auth');

  const handleSignupSuccess = () => {
    setAppState('onboarding');
  };

  const handleOnboardingComplete = () => {
    // After onboarding, the user proceeds to the main dashboard.
    setAppState('dashboard'); 
  };
  
  // A function to go back to the auth screen (for demonstration)
  const handleLogout = () => {
    setAppState('auth');
  }

  return (
    <>
      <style jsx global>{`
        @import url('https://fonts.googleapis.com/css2?family=Crimson+Pro:ital,wght@0,200;0,400;0,600;0,700&family=Crimson+Text:ital,wght@0,400;0,600;0,700&display=swap');
        
        .font-primary {
            font-family: 'Crimson Text', serif;
        }

        .font-secondary {
            font-family: 'Crimson Pro', serif;
        }
      `}</style>
      <main className="w-screen h-screen bg-[#FAF6D0] flex items-center justify-center sm:p-4">
        <div className="relative w-full h-full sm:max-w-sm sm:max-h-[850px] flex flex-col bg-[#FFFDF0] sm:rounded-[40px] sm:shadow-2xl overflow-hidden">
          
          {/* Conditional rendering based on the app state */}
          {appState === 'auth' && <Auth onSignupSuccess={handleSignupSuccess} />}
          {appState === 'onboarding' && <Onboarding onComplete={handleOnboardingComplete} />} 
          {/* THE FIX: The correct 'onLogout' prop is now passed to the Dashboard */}
          {appState === 'dashboard' && <Dashboard onLogout={handleLogout} />}

        </div>
      </main>
    </>
  );
}

