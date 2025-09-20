"use client";

import { useState } from 'react';
import Auth from '../components/Auth';
import Onboarding from '../components/Onboarding';

export default function Home() {
  // This state will control which main component is visible.
  // 'auth' for the login/signup flow, 'onboarding' for the new user tutorial.
  const [appState, setAppState] = useState<'auth' | 'onboarding'>('auth');

  // These functions will be passed to the child components to change the app state.
  const handleSignupSuccess = () => {
    // When a new user signs up in the Auth component, we switch to the onboarding view.
    setAppState('onboarding');
  };

  const handleOnboardingComplete = () => {
    // When the user finishes the tutorial, we can navigate them to the main app.
    // For now, we'll go back to the auth screen to demonstrate the flow.
    setAppState('auth'); 
  };

  return (
    <>
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
          
          {/* Conditional rendering based on the app state */}
          {appState === 'auth' && <Auth onSignupSuccess={handleSignupSuccess} />}
          {appState === 'onboarding' && <Onboarding onComplete={handleOnboardingComplete} />}

        </div>
      </main>
    </>
  );
}

