import React, { useState, useContext, useRef } from 'react';
import { Send } from 'lucide-react';
import { AppContext } from '../../context/AppContext';
import { sendChatMessage } from '../../api/chat';
import { detectEmotionFromImage } from '../../api/emotion';

interface ChatMessage {
  type: 'user' | 'bot';
  message: string;
  emotion?: string;
}

const ChatScreen: React.FC = () => {
  const { darkMode } = useContext(AppContext);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    { type: 'bot', message: "Hi! I'm here to support you. How are you feeling today?" }
  ]);
  const [newMessage, setNewMessage] = useState('');
  const token = localStorage.getItem('token') || '';
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // Start camera on mount
  React.useEffect(() => {
    const video = videoRef.current;
    navigator.mediaDevices.getUserMedia({ video: true }).then(stream => {
      if (video) {
        video.srcObject = stream;
        video.play();
      }
    });
    // Cleanup: stop camera on unmount
    return () => {
      if (video && video.srcObject) {
        (video.srcObject as MediaStream).getTracks().forEach(track => track.stop());
      }
    };
  }, []);

  const captureFrame = (): string | null => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (video && canvas) {
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const ctx = canvas.getContext('2d');
      if (ctx) {
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        return canvas.toDataURL('image/png').split(',')[1]; // base64 without prefix
      }
    }
    return null;
  };

  const addChatMessage = async (message: string) => {
    setChatMessages(prev => [...prev, { type: 'user', message }]);
    setNewMessage('');
    // Capture camera frame and send to backend for emotion detection
    const imageBase64 = captureFrame();
    let detectedEmotion = '';
    if (imageBase64) {
      try {
        const res = await detectEmotionFromImage(imageBase64, token);
        detectedEmotion = res.data.emotion;
      } catch {
        detectedEmotion = 'unknown';
      }
    }
    // Call backend chatbot
    const res = await sendChatMessage(message, token);
    setChatMessages(prev => [...prev, { type: 'bot', message: res.data.response, emotion: detectedEmotion }]);
  };

  return (
    <div className={`min-h-screen ${darkMode ? 'bg-gray-900' : 'bg-gray-50'}`}>
      <div className="p-6 pb-24">
        <h2 className={`text-2xl font-bold mb-6 text-center ${darkMode ? 'text-white' : 'text-gray-800'}`}>AI Therapist</h2>
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
                {msg.type === 'bot' && msg.emotion && (
                  <div className="text-xs mt-2 text-blue-400">Detected Emotion: {msg.emotion}</div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
      <div className="fixed bottom-20 left-0 right-0 p-4">
        <div className="flex space-x-2 max-w-md mx-auto">
          <input
            value={newMessage}
            onChange={e => setNewMessage(e.target.value)}
            placeholder="Type a message..."
            className={`flex-1 p-3 rounded-full border focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
              darkMode ? 'bg-gray-800 text-white border-gray-600' : 'bg-white border-gray-300'
            }`}
            onKeyPress={e => {
              if (e.key === 'Enter' && newMessage.trim()) {
                addChatMessage(newMessage);
              }
            }}
          />
          <button
            onClick={() => {
              if (newMessage.trim()) {
                addChatMessage(newMessage);
              }
            }}
            className="bg-blue-500 hover:bg-blue-600 text-white p-3 rounded-full transition-colors duration-300"
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
      </div>
      {/* Hidden video/canvas for camera capture */}
      <video ref={videoRef} style={{ display: 'none' }} />
      <canvas ref={canvasRef} style={{ display: 'none' }} />
    </div>
  );
};

export default ChatScreen; 