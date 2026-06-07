import React, { useState } from 'react';
import { Brain, MessageCircle, TrendingUp, AlertTriangle, Moon, Sun } from 'lucide-react';

const MindMitraApp = () => {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [darkMode, setDarkMode] = useState(false);

  return (
    <div className={`min-h-screen ${darkMode ? 'bg-gray-900 text-white' : 'bg-gray-50 text-gray-900'}`}>
      {/* Header */}
      <header className={`${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-lg border-b ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center space-x-3">
              <Brain className="h-8 w-8 text-blue-600" />
              <h1 className="text-2xl font-bold text-blue-600">MindMitra</h1>
            </div>
            <div className="flex items-center space-x-4">
              <button
                onClick={() => setDarkMode(!darkMode)}
                className={`p-2 rounded-lg ${darkMode ? 'bg-gray-700 hover:bg-gray-600' : 'bg-gray-100 hover:bg-gray-200'}`}
              >
                {darkMode ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
              </button>
              <button
                onClick={() => setIsLoggedIn(!isLoggedIn)}
                className={`px-4 py-2 rounded-lg font-medium ${
                  isLoggedIn 
                    ? 'bg-red-500 hover:bg-red-600 text-white' 
                    : 'bg-blue-500 hover:bg-blue-600 text-white'
                }`}
              >
                {isLoggedIn ? 'Logout' : 'Login'}
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {!isLoggedIn ? (
          // Login/Register View
          <div className="max-w-md mx-auto">
            <div className={`${darkMode ? 'bg-gray-800' : 'bg-white'} rounded-lg shadow-lg p-8`}>
              <h2 className="text-2xl font-bold text-center mb-6">Welcome to MindMitra</h2>
              <p className="text-center mb-6 text-gray-600">
                Your AI-powered mental wellness companion
              </p>
              <button
                onClick={() => setIsLoggedIn(true)}
                className="w-full bg-blue-500 hover:bg-blue-600 text-white font-medium py-3 px-4 rounded-lg transition duration-200"
              >
                Get Started
              </button>
            </div>
          </div>
        ) : (
          // Dashboard View
          <div className="space-y-6">
            {/* Welcome Section */}
            <div className={`${darkMode ? 'bg-gray-800' : 'bg-white'} rounded-lg shadow-lg p-6`}>
              <h2 className="text-2xl font-bold mb-2">Welcome back! 👋</h2>
              <p className="text-gray-600">How are you feeling today?</p>
            </div>

            {/* Quick Actions */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <div className={`${darkMode ? 'bg-gray-800' : 'bg-white'} rounded-lg shadow-lg p-6 cursor-pointer hover:shadow-xl transition duration-200`}>
                <MessageCircle className="h-8 w-8 text-blue-500 mb-4" />
                <h3 className="font-semibold mb-2">Chat with AI</h3>
                <p className="text-sm text-gray-600">Get instant support and guidance</p>
              </div>

              <div className={`${darkMode ? 'bg-gray-800' : 'bg-white'} rounded-lg shadow-lg p-6 cursor-pointer hover:shadow-xl transition duration-200`}>
                <MessageCircle className="h-8 w-8 text-green-500 mb-4" />
                <h3 className="font-semibold mb-2">Journal Entry</h3>
                <p className="text-sm text-gray-600">Write about your thoughts and feelings</p>
              </div>

              <div className={`${darkMode ? 'bg-gray-800' : 'bg-white'} rounded-lg shadow-lg p-6 cursor-pointer hover:shadow-xl transition duration-200`}>
                <TrendingUp className="h-8 w-8 text-purple-500 mb-4" />
                <h3 className="font-semibold mb-2">Mood Tracking</h3>
                <p className="text-sm text-gray-600">Track your emotional patterns</p>
              </div>

              <div className={`${darkMode ? 'bg-gray-800' : 'bg-white'} rounded-lg shadow-lg p-6 cursor-pointer hover:shadow-xl transition duration-200`}>
                <AlertTriangle className="h-8 w-8 text-red-500 mb-4" />
                <h3 className="font-semibold mb-2">SOS Support</h3>
                <p className="text-sm text-gray-600">Emergency mental health resources</p>
              </div>
            </div>

            {/* Recent Activity */}
            <div className={`${darkMode ? 'bg-gray-800' : 'bg-white'} rounded-lg shadow-lg p-6`}>
              <h3 className="text-lg font-semibold mb-4">Recent Activity</h3>
              <div className="space-y-3">
                <div className="flex items-center space-x-3">
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                  <span className="text-sm">Last journal entry: 2 hours ago</span>
                </div>
                <div className="flex items-center space-x-3">
                  <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                  <span className="text-sm">AI chat session: 1 day ago</span>
                </div>
                <div className="flex items-center space-x-3">
                  <div className="w-2 h-2 bg-purple-500 rounded-full"></div>
                  <span className="text-sm">Mood check-in: 3 days ago</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className={`${darkMode ? 'bg-gray-800' : 'bg-white'} border-t ${darkMode ? 'border-gray-700' : 'border-gray-200'} mt-12`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="text-center text-gray-600">
            <p>&copy; 2024 MindMitra. Your mental wellness companion.</p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default MindMitraApp; 