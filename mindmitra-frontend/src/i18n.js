import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

// Translation Dictionaries
const resources = {
  en: {
    translation: {
      title: "Mood Analytics",
      subtitle: "Track and visualize emotional trends",
      weekly: "Weekly",
      monthly: "Monthly",
      exportPdf: "Export PDF",
      summarySuffix: "Summary",
      lineChartTitle: "Mood Over Time",
      pieChartTitle: "Emotion Distribution",
      moodScore: "Mood Score",
      frequency: "Frequency",
      daysUnit: "days",
      emotions: {
        happy: "Happy",
        calm: "Calm",
        anxious: "Anxious",
        sad: "Sad"
      }
    }
  },
  hi: {
    translation: {
      title: "मूड विश्लेषिकी",
      subtitle: "भावनात्मक प्रवृत्तियों को ट्रैक और विज़ुअलाइज़ करें",
      weekly: "साप्ताहिक",
      monthly: "मासिक",
      exportPdf: "पीडीएफ एक्सपोर्ट",
      summarySuffix: "सारांश",
      lineChartTitle: "समय के साथ मूड ग्राफ",
      pieChartTitle: "भावनाओं का वितरण",
      moodScore: "मूड स्कोर",
      frequency: "आवृत्ति",
      daysUnit: "दिन",
      emotions: {
        happy: "खुश",
        calm: "शांत",
        anxious: "चिंतित",
        sad: "उदास"
      }
    }
  }
};

i18n
  .use(LanguageDetector) // Automatically detects user language
  .use(initReactI18next) // Binds i18next to react-i18next hooks
  .init({
    resources,
    fallbackLng: 'en', // Uses English if a translation is missing
    interpolation: {
      escapeValue: false // React already escapes values safely to prevent XSS attacks
    },
    detection: {
      order: ['localStorage', 'navigator'], // Looks in localStorage first, then browser settings
      caches: ['localStorage'] // Saves user selection back to localStorage
    }
  });

export default i18n;
