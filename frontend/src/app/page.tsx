"use client";

import { useState } from 'react';
import Auth from '../components/Auth';
import CameraView from '../components/CameraView';
import Dashboard from '../components/Dashboard';
import DocumentViewPage from '../components/DocumentView';
import { ApiResponse } from '../types';

export default function Home() {
  const [appState, setAppState] = useState<'auth' | 'onboarding' | 'dashboard' | 'camera' | 'history' | 'document'>('auth');
  const [selectedDocument, setSelectedDocument] = useState<ApiResponse | null>(null);

	const handleSignupSuccess = () => {
		setAppState('onboarding');
	};

	const handleOnboardingComplete = () => {
		setAppState('dashboard');
	};

	const handleLogout = () => {
		setAppState('auth');
	};

	const handleOpenCamera = () => {
		setAppState('camera');
	};

	const handleCloseCamera = () => {
		setAppState('dashboard');
	};

	const handleOpenHistory = () => {
		setAppState('history');
	};

<<<<<<< Updated upstream
	const handleCloseHistory = () => {
		setAppState('dashboard');
	};
=======
  const handleOpenDocument = (documentData: ApiResponse | null = null) => {
    setSelectedDocument(documentData);
    setAppState('document');
  };
>>>>>>> Stashed changes

	const handleOpenDocument = (documentData?: DocumentData | null) => {
		// Ensure documentData is not undefined before setting state
		setSelectedDocument(documentData ?? null);
		setAppState('document');
	};

  const handleDocumentAnalyzed = (documentData: ApiResponse) => {
    setSelectedDocument(documentData);
    setAppState('document');
  };

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
        
        .font-crimson {
            font-family: 'Crimson Text', serif;
        }
        
        .font-crimson-pro {
            font-family: 'Crimson Pro', serif;
        }
      `}</style>
<<<<<<< Updated upstream
			<main className="w-screen h-screen bg-[#FAF6D0] flex items-center justify-center sm:p-4">
				<div className="relative w-full h-full sm:max-w-sm sm:max-h-[850px] flex flex-col bg-[#FFFDF0] sm:rounded-[40px] sm:shadow-2xl overflow-y-auto">

					{appState === 'auth' && <Auth onSignupSuccess={handleSignupSuccess} />}
					{appState === 'onboarding' && <Onboarding onComplete={handleOnboardingComplete} />}
					{appState === 'dashboard' && <Dashboard onLogout={handleLogout} onOpenCamera={handleOpenCamera} onOpenHistory={handleOpenHistory} />}
					{appState === 'camera' && <CameraView onClose={handleCloseCamera} />}
					{appState === 'history' && <History onClose={handleCloseHistory} onOpenDocument={handleOpenDocument} />}
					{appState === 'document' && <DocumentViewPage onClose={handleCloseDocument} documentData={selectedDocument} />}

        </div>
      </main>
    </>
  );
}
