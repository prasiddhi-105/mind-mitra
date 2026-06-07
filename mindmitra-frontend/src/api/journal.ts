import axios from 'axios';

// ── Types ────────────────────────────────────────────────────────────────────

/** Emotion scores distribution from HuggingFace model */
export interface EmotionScores {
  anger?: number;
  disgust?: number;
  fear?: number;
  joy?: number;
  neutral?: number;
  sadness?: number;
  surprise?: number;
  [key: string]: number | undefined;
}

/** Journal entry as returned from the API */
export interface JournalEntryResponse {
  id: string;
  user_id: string;
  mood: number;
  text: string;
  date: string;
  created_at: string;
  updated_at?: string | null;
  emotion_label?: string | null;
  emotion_confidence?: number | null;
  emotion_scores?: EmotionScores | null;
  emotion_analyzed: boolean;
}

/** Payload for creating a new journal entry */
export interface JournalEntryCreate {
  mood: number;
  text: string;
  date?: string | null;
}

/** Payload for updating a journal entry */
export interface JournalEntryUpdate {
  mood?: number;
  text?: string;
}

// ── Emotion display helpers ──────────────────────────────────────────────────

/** Map emotion labels to emoji and color config */
export const EMOTION_CONFIG: Record<string, { emoji: string; bg: string; text: string; bgDark: string; textDark: string }> = {
  joy:      { emoji: '😊', bg: 'bg-yellow-100', text: 'text-yellow-700', bgDark: 'bg-yellow-900/30', textDark: 'text-yellow-300' },
  sadness:  { emoji: '😢', bg: 'bg-blue-100',   text: 'text-blue-700',   bgDark: 'bg-blue-900/30',   textDark: 'text-blue-300' },
  anger:    { emoji: '😠', bg: 'bg-red-100',    text: 'text-red-700',    bgDark: 'bg-red-900/30',    textDark: 'text-red-300' },
  fear:     { emoji: '😨', bg: 'bg-purple-100', text: 'text-purple-700', bgDark: 'bg-purple-900/30', textDark: 'text-purple-300' },
  disgust:  { emoji: '🤢', bg: 'bg-green-100',  text: 'text-green-700',  bgDark: 'bg-green-900/30',  textDark: 'text-green-300' },
  surprise: { emoji: '😮', bg: 'bg-orange-100', text: 'text-orange-700', bgDark: 'bg-orange-900/30', textDark: 'text-orange-300' },
  neutral:  { emoji: '😐', bg: 'bg-gray-100',   text: 'text-gray-700',   bgDark: 'bg-gray-700/50',   textDark: 'text-gray-300' },
};

/** Get display config for an emotion label, with fallback */
export const getEmotionConfig = (label?: string | null) => {
  if (!label) return EMOTION_CONFIG.neutral;
  return EMOTION_CONFIG[label.toLowerCase()] ?? EMOTION_CONFIG.neutral;
};

/** Format confidence as a percentage string */
export const formatConfidence = (confidence?: number | null): string => {
  if (confidence == null) return '';
  return `${Math.round(confidence * 100)}%`;
};

// ── API Functions ────────────────────────────────────────────────────────────

const authHeaders = (token: string) => ({
  headers: { Authorization: `Bearer ${token}` },
});

/** Fetch all journal entries for the authenticated user */
export const fetchJournalEntries = async (token: string, limit = 50) =>
  axios.get<JournalEntryResponse[]>(`/api/v1/journal?limit=${limit}`, authHeaders(token));

/** Create a new journal entry (emotion analysis happens server-side) */
export const saveJournalEntry = async (entry: JournalEntryCreate, token: string) =>
  axios.post<JournalEntryResponse>('/api/v1/journal', entry, authHeaders(token));

/** Fetch a single journal entry by ID */
export const fetchJournalEntry = async (entryId: string, token: string) =>
  axios.get<JournalEntryResponse>(`/api/v1/journal/${entryId}`, authHeaders(token));

/** Update a journal entry */
export const updateJournalEntry = async (entryId: string, update: JournalEntryUpdate, token: string) =>
  axios.put<JournalEntryResponse>(`/api/v1/journal/${entryId}`, update, authHeaders(token));

/** Delete a journal entry */
export const deleteJournalEntry = async (entryId: string, token: string) =>
  axios.delete(`/api/v1/journal/${entryId}`, authHeaders(token));