import { Routes, Route } from 'react-router-dom';
import { AppProvider } from './context/AppContext';
import MindMitraApp from './components/MindMitraApp';
import AdminScreen from './components/screens/AdminScreen';
import ForgotPasswordScreen from './components/screens/ForgotPasswordScreen';
import ResetPasswordScreen from './components/screens/ResetPasswordScreen';

export default function App() {
  return (
    <AppProvider>
      <Routes>
        <Route path="/forgot-password" element={<ForgotPasswordScreen />} />
        <Route path="/reset-password" element={<ResetPasswordScreen />} />
        {/* Admin panel — protected inside AdminScreen itself */}
        <Route path="/admin" element={<AdminScreen />} />
        {/* All other paths go to the existing app (its own screen-switcher) */}
        <Route path="*" element={<MindMitraApp />} />
      </Routes>
    </AppProvider>
  );
}
