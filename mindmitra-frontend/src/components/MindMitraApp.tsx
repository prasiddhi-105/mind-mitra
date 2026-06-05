import React, { useState, useEffect } from 'react';
import { Camera, Send, Home, User, MessageCircle, BookOpen, AlertCircle, Settings, BarChart3, Heart, Moon, Sun } from 'lucide-react';
import { sendChatMessage } from '../api/chat';
import AuthScreen from './screens/AuthScreen';
import { useAppContext } from '../context/AppContext';

const MindMitraApp = () => {
  const [currentScreen, setCurrentScreen] = useState('splash');
  const { darkMode, setDarkMode } = useAppContext();
  const [currentMood, setCurrentMood] = useState(3);
  const [journalText, setJournalText] = useState('');
  const [chatMessages, setChatMessages] = useState([
    { type: 'bot', message: "Hi! I'm here to support you. How are you feeling today?" }
  ]);
  const [newMessage, setNewMessage] = useState('');
  const [userName] = useState('Alex');
  const [isRecording, setIsRecording] = useState(false);
  const [, setIsAuthenticated] = useState(false);
  const [authToken, setAuthToken] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (currentScreen === 'splash') {
      const timer = setTimeout(() => setCurrentScreen('login'), 3000);
      return () => clearTimeout(timer);
    }
  }, [currentScreen]);

  const addChatMessage = async (message: string, type = 'user') => {
    setChatMessages(prev => [...prev, { type, message }]);
    if (type === 'user' && authToken) {
      try {
        setLoading(true);
        const response = await sendChatMessage(message, authToken);
        setChatMessages(prev => [...prev, { 
          type: 'bot', 
          message: response.data.response || "I'm here to help you. Can you tell me more about how you're feeling?"
        }]);
      } catch (error) {
        console.error('Chat error:', error);
        // Fallback to mock responses
        const responses = [
          "I understand how you're feeling. Can you tell me more about what's troubling you?",
          "That sounds challenging. Let's work through this together. What thoughts are going through your mind?",
          "Thank you for sharing. Have you noticed any patterns in when these feelings occur?",
          "I'm here to support you. What coping strategies have helped you in the past?"
        ];
        setChatMessages(prev => [...prev, { 
          type: 'bot', 
          message: responses[Math.floor(Math.random() * responses.length)] 
        }]);
      } finally {
        setLoading(false);
      }
    }
  };

  const handleLogin = async (_email: string, _password: string) => {
    try {
      setLoading(true);
      // Mock login for now - integrate with your auth API
      setAuthToken('mock-token');
      setIsAuthenticated(true);
      setCurrentScreen('home');
    } catch (error) {
      console.error('Login error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleJournalSave = async () => {
    if (!journalText.trim() || !authToken) return;
    
    try {
      setLoading(true);
      // Mock API call for now - integrate with your backend
      // await saveJournalEntry({ mood: currentMood, text: journalText }, authToken);
      setJournalText('');
      setCurrentScreen('home');
    } catch (error) {
      console.error('Journal save error:', error);
      // Still clear and navigate on error for demo
      setJournalText('');
      setCurrentScreen('home');
    } finally {
      setLoading(false);
    }
  };

  const handleEmotionAnalysis = async () => {
    if (!authToken) return;
    
    try {
      setLoading(true);
      setIsRecording(true);
      // Mock emotion analysis - integrate with your emotion API
      setTimeout(() => {
        setIsRecording(false);
        setLoading(false);
      }, 3000);
    } catch (error) {
      console.error('Emotion analysis error:', error);
      setIsRecording(false);
      setLoading(false);
    }
  };

  const SplashScreen = () => (
    <div className="min-h-screen bg-gradient-to-br from-blue-100 via-purple-50 to-pink-100 flex items-center justify-center">
      <div className="text-center">
        <div className="mb-8 relative">
          <div className="text-6xl mb-4 animate-pulse">🌊</div>
          <h1 className="text-4xl font-bold text-gray-800 mb-2">MindMitra</h1>
          <p className="text-gray-600 text-lg">"Your companion for emotional wellness"</p>
        </div>
        <div className="flex space-x-2 justify-center mb-6">
          <div className="w-3 h-3 bg-blue-500 rounded-full animate-bounce"></div>
          <div className="w-3 h-3 bg-purple-500 rounded-full animate-bounce delay-100"></div>
          <div className="w-3 h-3 bg-pink-500 rounded-full animate-bounce delay-200"></div>
        </div>
      </div>
    </div>
  );

  const LoginScreen = () => (
    <AuthScreen
      onSignIn={handleLogin}
      onRegister={(email, password) => handleLogin(email, password)}
      loading={loading}
    />
  );

  const HomeScreen = () => (
    <div className={`min-h-screen ${darkMode ? 'bg-gray-900' : 'bg-gray-50'} transition-colors duration-300`}>
      <div className="p-6">
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className={`text-2xl font-bold ${darkMode ? 'text-white' : 'text-gray-800'}`}>
              Hi, {userName} 👋
            </h1>
            <p className={`${darkMode ? 'text-gray-300' : 'text-gray-600'} mt-1`}>
              😊 You seem calm today
            </p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4 mb-6">
          <button
            onClick={() => setCurrentScreen('journal')}
            className="bg-gradient-to-r from-green-400 to-blue-500 text-white p-6 rounded-xl shadow-lg hover:scale-105 transition-transform duration-300"
          >
            <BookOpen className="w-8 h-8 mb-2 mx-auto" />
            <p className="font-medium">New Journal Entry</p>
          </button>
          <button
            onClick={() => setCurrentScreen('chat')}
            className="bg-gradient-to-r from-purple-400 to-pink-500 text-white p-6 rounded-xl shadow-lg hover:scale-105 transition-transform duration-300"
          >
            <MessageCircle className="w-8 h-8 mb-2 mx-auto" />
            <p className="font-medium">AI Chatbot</p>
          </button>
        </div>

        <div className={`${darkMode ? 'bg-gray-800' : 'bg-white'} rounded-xl p-4 shadow-lg mb-6`}>
          <h3 className={`font-medium mb-3 ${darkMode ? 'text-white' : 'text-gray-800'}`}>Mood Trend</h3>
          <div className="h-32 flex items-end space-x-2">
            {[4, 3, 5, 2, 4, 5, 3].map((height, i) => (
              <div
                key={i}
                className="bg-gradient-to-t from-blue-500 to-purple-500 rounded-t flex-1"
                style={{ height: `${height * 20}%` }}
              />
            ))}
          </div>
        </div>
      </div>

      <div className="fixed bottom-6 right-6">
        <button
          onClick={() => setCurrentScreen('sos')}
          className="bg-red-500 hover:bg-red-600 text-white w-16 h-16 rounded-full shadow-2xl flex items-center justify-center animate-pulse"
        >
          <AlertCircle className="w-8 h-8" />
        </button>
      </div>

      <BottomNav />
    </div>
  );

  const EmotionDetectionScreen = () => (
    <div className={`min-h-screen ${darkMode ? 'bg-gray-900' : 'bg-gray-50'} p-6`}>
      <div className="max-w-md mx-auto">
        <h2 className={`text-2xl font-bold mb-6 text-center ${darkMode ? 'text-white' : 'text-gray-800'}`}>
          Emotion Detection
        </h2>
        
        <div className={`${darkMode ? 'bg-gray-800' : 'bg-white'} rounded-xl p-6 shadow-lg mb-6`}>
          <div className="aspect-square bg-gray-200 rounded-lg flex items-center justify-center mb-4 relative overflow-hidden">
            {isRecording ? (
              <div className="absolute inset-0 bg-blue-500 opacity-20 animate-pulse" />
            ) : null}
            <Camera className="w-16 h-16 text-gray-400" />
          </div>
          
          <button
            onClick={handleEmotionAnalysis}
            disabled={loading}
            className={`w-full py-3 rounded-lg font-medium transition-all duration-300 ${
              isRecording 
                ? 'bg-red-500 hover:bg-red-600 text-white' 
                : 'bg-blue-500 hover:bg-blue-600 text-white'
            } disabled:opacity-50`}
          >
            {loading ? 'Analyzing...' : isRecording ? 'Stop Analysis' : 'Start Analysis'}
          </button>
        </div>

        {isRecording && (
          <div className={`${darkMode ? 'bg-gray-800' : 'bg-white'} rounded-xl p-6 shadow-lg text-center`}>
            <div className="animate-bounce mb-4">
              <div className="w-16 h-16 bg-gradient-to-r from-blue-400 to-purple-600 rounded-full mx-auto flex items-center justify-center">
                <Heart className="w-8 h-8 text-white animate-pulse" />
              </div>
            </div>
            <p className={`text-lg font-medium ${darkMode ? 'text-white' : 'text-gray-800'}`}>
              Detected Emotion: Anxious 😟
            </p>
            <div className="flex space-x-3 mt-4">
              <button
                onClick={() => setIsRecording(false)}
                className="flex-1 py-2 bg-gray-500 hover:bg-gray-600 text-white rounded-lg"
              >
                Try Again
              </button>
              <button className="flex-1 py-2 bg-green-500 hover:bg-green-600 text-white rounded-lg">
                Save Result
              </button>
            </div>
          </div>
        )}
      </div>
      <BottomNav />
    </div>
  );

  const JournalScreen = () => (
    <div className={`min-h-screen ${darkMode ? 'bg-gray-900' : 'bg-gray-50'} p-6`}>
      <div className="max-w-md mx-auto">
        <h2 className={`text-2xl font-bold mb-6 text-center ${darkMode ? 'text-white' : 'text-gray-800'}`}>
          How are you feeling?
        </h2>
        
        <div className={`${darkMode ? 'bg-gray-800' : 'bg-white'} rounded-xl p-6 shadow-lg mb-6`}>
          <div className="flex justify-center items-center space-x-4 mb-6">
            <span className="text-2xl">😢</span>
            <input
              type="range"
              min="1"
              max="5"
              value={currentMood}
              onChange={(e) => setCurrentMood(parseInt(e.target.value))}
              className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
            />
            <span className="text-2xl">😊</span>
          </div>
          
          <div className="text-center mb-4">
            <span className="text-3xl">
              {currentMood == 1 ? '😢' : currentMood == 2 ? '😕' : currentMood == 3 ? '😐' : currentMood == 4 ? '🙂' : '😊'}
            </span>
          </div>
          
          <textarea
            value={journalText}
            onChange={(e) => setJournalText(e.target.value)}
            placeholder="Write about your mood..."
            className={`w-full h-32 p-3 border border-gray-300 rounded-lg resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
              darkMode ? 'bg-gray-700 text-white border-gray-600' : ''
            }`}
          />
          
          <button
            onClick={handleJournalSave}
            disabled={loading || !journalText.trim()}
            className="w-full mt-4 bg-green-500 hover:bg-green-600 text-white py-3 rounded-lg font-medium transition-all duration-300 disabled:opacity-50"
          >
            {loading ? 'Saving...' : 'Save Entry'}
          </button>
        </div>

        <div className={`${darkMode ? 'bg-gray-800' : 'bg-white'} rounded-xl p-6 shadow-lg`}>
          <h3 className={`font-medium mb-3 ${darkMode ? 'text-white' : 'text-gray-800'}`}>Recent Entries</h3>
          <div className="grid grid-cols-7 gap-2">
            {Array.from({ length: 14 }, (_, i) => (
              <div
                key={i}
                className={`aspect-square rounded-lg flex items-center justify-center text-sm ${
                  i % 3 === 0 ? 'bg-green-100 text-green-600' : 
                  i % 3 === 1 ? 'bg-yellow-100 text-yellow-600' : 
                  'bg-red-100 text-red-600'
                }`}
              >
                {20 - i}
              </div>
            ))}
          </div>
        </div>
      </div>
      <BottomNav />
    </div>
  );

  const ChatScreen = () => (
    <div className={`min-h-screen ${darkMode ? 'bg-gray-900' : 'bg-gray-50'}`}>
      <div className="p-6 pb-24">
        <h2 className={`text-2xl font-bold mb-6 text-center ${darkMode ? 'text-white' : 'text-gray-800'}`}>
          AI Therapist
        </h2>
        
        <div className="space-y-4 mb-6">
          {chatMessages.map((msg, i) => (
            <div
              key={i}
              className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-xs px-4 py-2 rounded-2xl ${
                  msg.type === 'user'
                    ? 'bg-blue-500 text-white'
                    : `${darkMode ? 'bg-gray-800 text-white' : 'bg-white'} shadow-lg`
                }`}
              >
                <p className="text-sm">{msg.message}</p>
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex justify-start">
              <div className={`max-w-xs px-4 py-2 rounded-2xl ${darkMode ? 'bg-gray-800 text-white' : 'bg-white'} shadow-lg`}>
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-100"></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-200"></div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
      
      <div className="fixed bottom-20 left-0 right-0 p-4">
        <div className="flex space-x-2 max-w-md mx-auto">
          <input
            value={newMessage}
            onChange={(e) => setNewMessage(e.target.value)}
            placeholder="Type a message..."
            className={`flex-1 p-3 rounded-full border focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
              darkMode ? 'bg-gray-800 text-white border-gray-600' : 'bg-white border-gray-300'
            }`}
            onKeyPress={(e) => {
              if (e.key === 'Enter' && newMessage.trim() && !loading) {
                addChatMessage(newMessage);
                setNewMessage('');
              }
            }}
          />
          <button
            onClick={() => {
              if (newMessage.trim() && !loading) {
                addChatMessage(newMessage);
                setNewMessage('');
              }
            }}
            disabled={loading || !newMessage.trim()}
            className="bg-blue-500 hover:bg-blue-600 text-white p-3 rounded-full transition-colors duration-300 disabled:opacity-50"
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
      </div>
      
      <BottomNav />
    </div>
  );

  const SOSScreen = () => (
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
          onClick={() => setCurrentScreen('home')}
          className="bg-gray-500 hover:bg-gray-600 text-white px-8 py-3 rounded-lg font-medium transition-colors duration-300"
        >
          Cancel
        </button>
      </div>
    </div>
  );

  const ProfileScreen = () => (
    <div className={`min-h-screen ${darkMode ? 'bg-gray-900' : 'bg-gray-50'} p-6`}>
      <div className="max-w-md mx-auto">
        <div className={`${darkMode ? 'bg-gray-800' : 'bg-white'} rounded-xl p-6 shadow-lg mb-6 text-center`}>
          <div className="w-20 h-20 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white text-2xl font-bold mx-auto mb-4">
            {userName[0]}
          </div>
          <h3 className={`text-xl font-bold ${darkMode ? 'text-white' : 'text-gray-800'}`}>
            {userName} Doe
          </h3>
          <p className={`${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>alex@email.com</p>
        </div>
        
        <div className="space-y-3">
          <button className={`w-full ${darkMode ? 'bg-gray-800 text-white' : 'bg-white'} p-4 rounded-xl shadow-lg text-left hover:scale-105 transition-transform duration-300`}>
            <div className="flex items-center">
              <AlertCircle className="w-5 h-5 mr-3 text-red-500" />
              <span>Edit Emergency Contacts</span>
            </div>
          </button>
          
          <button 
            onClick={() => setDarkMode(!darkMode)}
            className={`w-full ${darkMode ? 'bg-gray-800 text-white' : 'bg-white'} p-4 rounded-xl shadow-lg text-left hover:scale-105 transition-transform duration-300`}
          >
            <div className="flex items-center">
              {darkMode ? <Sun className="w-5 h-5 mr-3 text-yellow-500" /> : <Moon className="w-5 h-5 mr-3 text-blue-500" />}
              <span>Theme: {darkMode ? 'Dark' : 'Light'}</span>
            </div>
          </button>
          
          <button
            onClick={() => {
              setIsAuthenticated(false);
              setAuthToken('');
              setCurrentScreen('login');
            }}
            className={`w-full ${darkMode ? 'bg-gray-800 text-white' : 'bg-white'} p-4 rounded-xl shadow-lg text-left hover:scale-105 transition-transform duration-300`}
          >
            <div className="flex items-center">
              <Settings className="w-5 h-5 mr-3 text-gray-500" />
              <span>Log out</span>
            </div>
          </button>
        </div>
      </div>
      <BottomNav />
    </div>
  );

  const TrendsScreen = () => (
    <div className={`min-h-screen ${darkMode ? 'bg-gray-900' : 'bg-gray-50'} p-6`}>
      <div className="max-w-md mx-auto">
        <h2 className={`text-2xl font-bold mb-6 text-center ${darkMode ? 'text-white' : 'text-gray-800'}`}>
          Mood Trends
        </h2>
        
        <div className={`${darkMode ? 'bg-gray-800' : 'bg-white'} rounded-xl p-6 shadow-lg mb-6`}>
          <div className="h-48 flex items-end space-x-2 mb-4">
            {[4, 3, 5, 2, 4, 5, 3, 4, 2, 5, 4, 3, 5].map((height, i) => (
              <div
                key={i}
                className="bg-gradient-to-t from-blue-500 to-purple-500 rounded-t flex-1"
                style={{ height: `${height * 20}%` }}
              />
            ))}
          </div>
          
          <div className="flex justify-center space-x-3 mb-4">
            <button className="px-4 py-2 bg-blue-500 text-white rounded-lg text-sm">Week</button>
            <button className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg text-sm">Month</button>
            <button className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg text-sm">Custom</button>
          </div>
          
          <button className="w-full bg-green-500 hover:bg-green-600 text-white py-3 rounded-lg font-medium transition-colors duration-300">
            Export/Share
          </button>
        </div>

        <div className={`${darkMode ? 'bg-gray-800' : 'bg-white'} rounded-xl p-6 shadow-lg`}>
          <h3 className={`font-medium mb-3 ${darkMode ? 'text-white' : 'text-gray-800'}`}>Insights</h3>
          <div className="space-y-3">
            <div className="p-3 bg-green-50 rounded-lg">
              <p className="text-sm text-green-700">📈 Your mood has improved 15% this week!</p>
            </div>
            <div className="p-3 bg-blue-50 rounded-lg">
              <p className="text-sm text-blue-700">🌅 You feel best in the mornings</p>
            </div>
            <div className="p-3 bg-yellow-50 rounded-lg">
              <p className="text-sm text-yellow-700">💭 Journaling helps boost your mood</p>
            </div>
          </div>
        </div>
      </div>
      <BottomNav />
    </div>
  );

  const BottomNav = () => (
    <div className={`fixed bottom-0 left-0 right-0 ${darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'} border-t px-6 py-3`}>
      <div className="flex justify-around max-w-md mx-auto">
        {[
          { icon: Home, screen: 'home', label: 'Home' },
          { icon: Camera, screen: 'emotion', label: 'Detect' },
          { icon: BookOpen, screen: 'journal', label: 'Journal' },
          { icon: BarChart3, screen: 'trends', label: 'Trends' },
          { icon: User, screen: 'profile', label: 'Profile' }
        ].map(({ icon: Icon, screen, label }) => (
          <button
            key={screen}
            onClick={() => setCurrentScreen(screen)}
            className={`flex flex-col items-center space-y-1 p-2 rounded-lg transition-colors duration-300 ${
              currentScreen === screen 
                ? 'text-blue-500' 
                : darkMode ? 'text-gray-400 hover:text-gray-300' : 'text-gray-600 hover:text-gray-800'
            }`}
          >
            <Icon className="w-5 h-5" />
            <span className="text-xs">{label}</span>
          </button>
        ))}
      </div>
    </div>
  );

  const showNavbar = currentScreen !== 'splash' && currentScreen !== 'login' && currentScreen !== 'sos';

  const Navbar = () => (
    <header className={`${darkMode ? 'bg-gray-800 border-gray-700 text-white' : 'bg-white border-gray-200 text-gray-800'} border-b px-6 py-4 flex justify-between items-center transition-colors duration-300`}>
      <div className="flex items-center space-x-2">
        <span className="text-2xl animate-pulse">🌊</span>
        <span className={`text-xl font-bold ${darkMode ? 'text-white' : 'text-gray-850'}`}>MindMitra</span>
      </div>
      <button
        onClick={() => setDarkMode(!darkMode)}
        className={`p-2 rounded-full transition-colors duration-300 ${darkMode ? 'bg-gray-700 text-yellow-400 hover:bg-gray-600' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
      >
        {darkMode ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
      </button>
    </header>
  );

  const screens: Record<string, React.ReactElement> = {
    splash: <SplashScreen />,
    login: <LoginScreen />,
    home: <HomeScreen />,
    emotion: <EmotionDetectionScreen />,
    journal: <JournalScreen />,
    chat: <ChatScreen />,
    sos: <SOSScreen />,
    profile: <ProfileScreen />,
    trends: <TrendsScreen />
  };

  if (currentScreen === 'login') {
    return <LoginScreen />;
  }

  return (
    <div className={`max-w-md mx-auto ${darkMode ? 'bg-gray-900 text-white' : 'bg-white text-gray-800'} min-h-screen relative overflow-hidden flex flex-col transition-colors duration-300`}>
      {showNavbar && <Navbar />}
      <div className="flex-1 overflow-y-auto">
        {screens[currentScreen]}
      </div>
    </div>
  );
};

export default MindMitraApp;
