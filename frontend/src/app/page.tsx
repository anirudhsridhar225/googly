"use client";

import { useState } from 'react';
import Auth from '../components/Auth';
import Onboarding from '../components/Onboarding';
import Dashboard from '../components/Dashboard';
import CameraView from '../components/CameraView';
import History from '../components/History'; 

export default function Home() {
  const [appState, setAppState] = useState<'auth' | 'onboarding' | 'dashboard' | 'camera' | 'history'>('auth');

  const handleSignupSuccess = () => {
    setAppState('onboarding');
  };

  const handleOnboardingComplete = () => {
    setAppState('dashboard'); 
  };
  
  const handleLogout = () => {
    setAppState('auth');
  }

  const handleOpenCamera = () => {
    setAppState('camera');
  }
  
  const handleCloseCamera = () => {
    setAppState('dashboard');
  }

  const handleOpenHistory = () => {
    setAppState('history');
  }
  
  // THE FIX: Added a dedicated function to close the history page.
  const handleCloseHistory = () => {
    setAppState('dashboard');
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
          
          {appState === 'auth' && <Auth onSignupSuccess={handleSignupSuccess} />}
          {appState === 'onboarding' && <Onboarding onComplete={handleOnboardingComplete} />}
          {/* THE FIX: Dashboard now receives the onOpenHistory prop. */}
          {appState === 'dashboard' && <Dashboard onLogout={handleLogout} onOpenCamera={handleOpenCamera} onOpenHistory={handleOpenHistory} />}
          {appState === 'camera' && <CameraView onClose={handleCloseCamera} />}
           {/* THE FIX: History now receives the correct handleCloseHistory prop. */}
          {appState === 'history' && <History onClose={handleCloseHistory} />}

        </div>
      </main>
    </>
  );
}

