import React, { useState, useEffect, useContext, useCallback } from 'react';
import { AppContext } from '../../context/AppContext';
import { Loader2, Trash2, RefreshCw } from 'lucide-react';
import {
  fetchJournalEntries,
  saveJournalEntry,
  deleteJournalEntry,
  getEmotionConfig,
  formatConfidence,
  type JournalEntryResponse,
} from '../../api/journal';

/** Emotion badge component — renders a colored pill with emoji + label + confidence */
const EmotionBadge: React.FC<{
  label?: string | null;
  confidence?: number | null;
  analyzed: boolean;
  darkMode: boolean;
}> = ({ label, confidence, analyzed, darkMode }) => {
  if (!analyzed) {
    return (
      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
        darkMode ? 'bg-gray-700/50 text-gray-400' : 'bg-gray-100 text-gray-500'
      }`}>
        —
      </span>
    );
  }

  const config = getEmotionConfig(label);
  const bg = darkMode ? config.bgDark : config.bg;
  const text = darkMode ? config.textDark : config.text;
  const confStr = formatConfidence(confidence);

  return (
    <span
      className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold transition-all duration-200 ${bg} ${text}`}
      title={`Detected emotion: ${label} (${confStr})`}
    >
      <span className="text-sm">{config.emoji}</span>
      <span className="capitalize">{label}</span>
      {confStr && <span className="opacity-70">· {confStr}</span>}
    </span>
  );
};

/** Loading skeleton for journal entries */
const EntrySkeleton: React.FC<{ darkMode: boolean }> = ({ darkMode }) => (
  <div className={`p-4 rounded-xl animate-pulse ${darkMode ? 'bg-gray-700/50' : 'bg-gray-100'}`}>
    <div className="flex justify-between items-start mb-2">
      <div className={`h-4 w-24 rounded ${darkMode ? 'bg-gray-600' : 'bg-gray-200'}`} />
      <div className={`h-5 w-20 rounded-full ${darkMode ? 'bg-gray-600' : 'bg-gray-200'}`} />
    </div>
    <div className={`h-3 w-full rounded mt-2 ${darkMode ? 'bg-gray-600' : 'bg-gray-200'}`} />
    <div className={`h-3 w-2/3 rounded mt-1.5 ${darkMode ? 'bg-gray-600' : 'bg-gray-200'}`} />
  </div>
);

/** Format date to readable string */
const formatDate = (dateStr: string): string => {
  try {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;

    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  } catch {
    return '';
  }
};

/** Mood emoji mapping */
const moodEmoji = (mood: number): string => {
  const map: Record<number, string> = { 1: '😢', 2: '😕', 3: '😐', 4: '🙂', 5: '😊' };
  return map[mood] ?? '😐';
};

const JournalScreen: React.FC = () => {
  const { darkMode } = useContext(AppContext);

  // ── State ──────────────────────────────────────────────────────────────────
  const [currentMood, setCurrentMood] = useState(3);
  const [journalText, setJournalText] = useState('');
  const [entries, setEntries] = useState<JournalEntryResponse[]>([]);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Try to get the auth token from localStorage (the app stores it there)
  const getToken = useCallback((): string | null => {
    return localStorage.getItem('authToken') || localStorage.getItem('token') || null;
  }, []);

  // ── Fetch entries on mount ─────────────────────────────────────────────────
  const loadEntries = useCallback(async () => {
    const token = getToken();
    if (!token) return;

    setLoading(true);
    setError(null);
    try {
      const res = await fetchJournalEntries(token);
      setEntries(res.data);
    } catch (err: any) {
      console.error('Failed to fetch journal entries:', err);
      if (err?.response?.status !== 401) {
        setError('Failed to load entries');
      }
    } finally {
      setLoading(false);
    }
  }, [getToken]);

  useEffect(() => {
    loadEntries();
  }, [loadEntries]);

  // ── Save handler ───────────────────────────────────────────────────────────
  const handleSave = async () => {
    if (!journalText.trim()) return;
    const token = getToken();
    if (!token) {
      setError('Please log in to save entries');
      return;
    }

    setSaving(true);
    setError(null);
    setSaveSuccess(false);

    try {
      const res = await saveJournalEntry({ mood: currentMood, text: journalText }, token);
      // Prepend new entry at top of list
      setEntries(prev => [res.data, ...prev]);
      setJournalText('');
      setCurrentMood(3);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err: any) {
      console.error('Journal save error:', err);
      setError(err?.response?.data?.detail || 'Failed to save entry. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  // ── Delete handler ─────────────────────────────────────────────────────────
  const handleDelete = async (entryId: string) => {
    const token = getToken();
    if (!token) return;

    try {
      await deleteJournalEntry(entryId, token);
      setEntries(prev => prev.filter(e => e.id !== entryId));
    } catch (err) {
      console.error('Delete error:', err);
      setError('Failed to delete entry');
    }
  };

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className={`min-h-screen ${darkMode ? 'bg-gray-900' : 'bg-gray-50'} p-6 pb-24`}>
      <div className="max-w-md mx-auto">
        <h2 className={`text-2xl font-bold mb-6 text-center ${darkMode ? 'text-white' : 'text-gray-800'}`}>
          How are you feeling?
        </h2>

        {/* ── Compose Card ────────────────────────────────────────────────── */}
        <div className={`${darkMode ? 'bg-gray-800' : 'bg-white'} rounded-xl p-6 shadow-lg mb-6 transition-colors duration-300`}>
          {/* Mood slider */}
          <div className="flex justify-center items-center space-x-4 mb-6">
            <span className="text-2xl">😢</span>
            <input
              type="range"
              min="1"
              max="5"
              value={currentMood}
              onChange={e => setCurrentMood(Number(e.target.value))}
              className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-500"
              id="mood-slider"
            />
            <span className="text-2xl">😊</span>
          </div>

          <div className="text-center mb-4">
            <span className="text-3xl transition-all duration-200">{moodEmoji(currentMood)}</span>
          </div>

          {/* Journal text */}
          <textarea
            id="journal-text-input"
            value={journalText}
            onChange={e => setJournalText(e.target.value)}
            placeholder="Write about your mood..."
            className={`w-full h-32 p-3 border rounded-lg resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors duration-200 ${
              darkMode ? 'bg-gray-700 text-white border-gray-600 placeholder-gray-400' : 'border-gray-300 placeholder-gray-500'
            }`}
          />

          {/* Error message */}
          {error && (
            <div className="mt-2 p-2 bg-red-100 text-red-700 text-sm rounded-lg dark:bg-red-900/30 dark:text-red-300">
              {error}
            </div>
          )}

          {/* Success message with emotion result */}
          {saveSuccess && entries[0]?.emotion_analyzed && (
            <div className={`mt-2 p-3 rounded-lg flex items-center gap-2 ${
              darkMode ? 'bg-green-900/30 text-green-300' : 'bg-green-50 text-green-700'
            }`}>
              <span className="text-sm">✨ Saved! Detected emotion:</span>
              <EmotionBadge
                label={entries[0].emotion_label}
                confidence={entries[0].emotion_confidence}
                analyzed={entries[0].emotion_analyzed}
                darkMode={darkMode}
              />
            </div>
          )}

          {/* Save button */}
          <button
            id="journal-save-btn"
            onClick={handleSave}
            disabled={saving || !journalText.trim()}
            className={`w-full mt-4 py-3 rounded-lg font-medium transition-all duration-300 flex items-center justify-center gap-2 ${
              saving
                ? 'bg-blue-400 cursor-wait'
                : 'bg-green-500 hover:bg-green-600 active:scale-[0.98]'
            } text-white disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            {saving ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Analyzing emotion...
              </>
            ) : (
              'Save Entry'
            )}
          </button>
        </div>

        {/* ── Recent Entries ───────────────────────────────────────────────── */}
        <div className={`${darkMode ? 'bg-gray-800' : 'bg-white'} rounded-xl p-6 shadow-lg transition-colors duration-300`}>
          <div className="flex items-center justify-between mb-4">
            <h3 className={`font-semibold ${darkMode ? 'text-white' : 'text-gray-800'}`}>
              Recent Entries
            </h3>
            <button
              onClick={loadEntries}
              disabled={loading}
              className={`p-1.5 rounded-lg transition-colors duration-200 ${
                darkMode ? 'hover:bg-gray-700 text-gray-400' : 'hover:bg-gray-100 text-gray-500'
              }`}
              title="Refresh entries"
              id="journal-refresh-btn"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>

          {/* Loading skeletons */}
          {loading && entries.length === 0 && (
            <div className="space-y-3">
              {[0, 1, 2].map(i => <EntrySkeleton key={i} darkMode={darkMode} />)}
            </div>
          )}

          {/* Empty state */}
          {!loading && entries.length === 0 && (
            <div className={`text-center py-8 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
              <span className="text-4xl block mb-2">📝</span>
              <p className="text-sm">No entries yet. Start journaling above!</p>
            </div>
          )}

          {/* Entry list */}
          {entries.length > 0 && (
            <div className="space-y-3">
              {entries.map(entry => (
                <div
                  key={entry.id}
                  className={`p-4 rounded-xl transition-all duration-200 hover:scale-[1.01] ${
                    darkMode
                      ? 'bg-gray-700/50 hover:bg-gray-700/80'
                      : 'bg-gray-50 hover:bg-gray-100'
                  }`}
                >
                  {/* Top row: date + mood + emotion badge */}
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-lg" title={`Mood: ${entry.mood}/5`}>
                        {moodEmoji(entry.mood)}
                      </span>
                      <span className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                        {formatDate(entry.created_at || entry.date)}
                      </span>
                    </div>
                    <EmotionBadge
                      label={entry.emotion_label}
                      confidence={entry.emotion_confidence}
                      analyzed={entry.emotion_analyzed}
                      darkMode={darkMode}
                    />
                  </div>

                  {/* Text preview */}
                  <p className={`text-sm line-clamp-2 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                    {entry.text}
                  </p>

                  {/* Actions row */}
                  <div className="flex justify-end mt-2">
                    <button
                      onClick={() => handleDelete(entry.id)}
                      className={`p-1 rounded transition-colors duration-200 opacity-0 group-hover:opacity-100 ${
                        darkMode ? 'hover:bg-red-900/30 text-red-400' : 'hover:bg-red-50 text-red-400'
                      }`}
                      title="Delete entry"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default JournalScreen;