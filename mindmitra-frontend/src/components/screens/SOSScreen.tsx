import React from 'react';

const SOSScreen: React.FC = () => {
  return (
    <div className="min-h-screen bg-red-50 flex items-center justify-center p-6">
      <div className="text-center">
        <div className="text-6xl mb-6 animate-pulse">🚨</div>
        <h2 className="text-3xl font-bold text-red-600 mb-8">EMERGENCY SOS</h2>
        <button
          className="w-40 h-40 bg-red-500 hover:bg-red-600 text-white rounded-full shadow-2xl flex items-center justify-center font-bold text-lg mb-8 mx-auto transition-all duration-300 hover:scale-105"
          onTouchStart={() => {}}
        >
          Hold to Alert
        </button>
        <button
          onClick={() => window.history.back()}
          className="bg-gray-500 hover:bg-gray-600 text-white px-8 py-3 rounded-lg font-medium transition-colors duration-300"
        >
          Cancel
        </button>
      </div>
    </div>
  );
};

export default SOSScreen; 