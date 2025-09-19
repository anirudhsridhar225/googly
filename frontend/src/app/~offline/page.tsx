'use client';

import { useRouter } from 'next/navigation';

export default function Offline() {
  const router = useRouter();

  const handleRetry = () => {
    router.refresh();
    window.location.reload();
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100">
      <h1 className="text-3xl font-bold mb-4">You are offline</h1>
      <p className="text-lg mb-8">Please check your internet connection and try again.</p>
      <button 
        className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
        onClick={handleRetry}
      >
        Retry
      </button>
    </div>
  );
}