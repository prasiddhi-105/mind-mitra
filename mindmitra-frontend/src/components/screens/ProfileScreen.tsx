import React, { useEffect, useRef, useState } from 'react';
import {
  AlertCircle,
  Camera,
  Loader2,
  Mail,
  Phone,
  Save,
  Sun,
  Moon,
  Settings,
  User as UserIcon,
  X,
} from 'lucide-react';
import { useAppContext } from '../../context/AppContext';
import type { EmergencyContact } from '../../api/auth';
import {
  updateProfile,
  uploadProfilePicture,
} from '../../api/auth';

const EMPTY_CONTACT: EmergencyContact = {
  name: '',
  phone: '',
  email: '',
  relationship: '',
};

const MAX_IMAGE_SIZE = 5 * 1024 * 1024;
const ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'];

function axiosErrorMessage(err: unknown): string | null {
  if (typeof err === 'object' && err !== null && 'response' in err) {
    const response = (err as { response?: { data?: { detail?: string } } }).response;
    if (typeof response?.data?.detail === 'string') {
      return response.data.detail;
    }
  }
  return null;
}

interface ProfileScreenProps {
  onLogoutComplete?: () => void;
}

const ProfileScreen: React.FC<ProfileScreenProps> = ({ onLogoutComplete }) => {
  const { darkMode, setDarkMode, user, token, setUser, refreshUser, logout, loadingUser } =
    useAppContext();

  const [isEditing, setIsEditing] = useState(false);
  const [name, setName] = useState('');
  const [contact, setContact] = useState<EmergencyContact>(EMPTY_CONTACT);
  const [picturePreview, setPicturePreview] = useState<string | null>(null);
  const [pendingPicture, setPendingPicture] = useState<File | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (user) {
      setName(user.name);
      const existing = user.emergency_contacts?.[0];
      setContact(existing ? { ...existing, email: existing.email || '' } : { ...EMPTY_CONTACT });
      setPicturePreview(user.profile_picture_url || null);
    }
  }, [user]);

  const resetForm = () => {
    if (!user) return;
    setName(user.name);
    const existing = user.emergency_contacts?.[0];
    setContact(existing ? { ...existing, email: existing.email || '' } : { ...EMPTY_CONTACT });
    setPicturePreview(user.profile_picture_url || null);
    setPendingPicture(null);
    setError('');
    setSuccess('');
  };

  const handlePictureSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!ALLOWED_IMAGE_TYPES.includes(file.type)) {
      setError('Please choose a JPEG, PNG, WebP, or GIF image.');
      return;
    }
    if (file.size > MAX_IMAGE_SIZE) {
      setError('Image must be smaller than 5MB.');
      return;
    }

    setPendingPicture(file);
    setPicturePreview(URL.createObjectURL(file));
    setError('');
  };

  const validateContact = (): string | null => {
    const hasAny = contact.name || contact.phone || contact.relationship || contact.email;
    if (!hasAny) return null;

    if (!contact.name.trim()) return 'Emergency contact name is required.';
    if (!contact.phone.trim() || contact.phone.trim().length < 10) {
      return 'Emergency contact phone must be at least 10 digits.';
    }
    if (!contact.relationship.trim()) return 'Relationship is required.';
    return null;
  };

  const handleSave = async () => {
    if (!token || !user) return;

    const contactError = validateContact();
    if (contactError) {
      setError(contactError);
      return;
    }

    setSaving(true);
    setError('');
    setSuccess('');

    try {
      let updatedUser = user;

      if (pendingPicture) {
        const pictureRes = await uploadProfilePicture(pendingPicture, token);
        updatedUser = pictureRes.data;
        setUser(updatedUser);
        setPendingPicture(null);
      }

      const hasContact =
        contact.name.trim() && contact.phone.trim() && contact.relationship.trim();

      const profileRes = await updateProfile(
        {
          name: name.trim(),
          emergency_contacts: hasContact
            ? [
                {
                  name: contact.name.trim(),
                  phone: contact.phone.trim(),
                  email: contact.email?.trim() || undefined,
                  relationship: contact.relationship.trim(),
                },
              ]
            : [],
        },
        token
      );

      setUser(profileRes.data);
      setPicturePreview(profileRes.data.profile_picture_url || null);
      setIsEditing(false);
      setSuccess('Profile saved successfully.');
      await refreshUser();
    } catch (err: unknown) {
      const message =
        axiosErrorMessage(err) || 'Failed to save profile. Please try again.';
      setError(message);
    } finally {
      setSaving(false);
    }
  };

  const handleLogout = () => {
    logout();
    onLogoutComplete?.();
  };

  const cardClass = `${darkMode ? 'bg-gray-800 text-white' : 'bg-white text-gray-800'} rounded-xl shadow-lg`;
  const inputClass = `w-full p-3 rounded-lg border ${
    darkMode
      ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400'
      : 'bg-white border-gray-300 text-gray-800'
  } focus:ring-2 focus:ring-blue-500 focus:border-transparent`;

  if (loadingUser && !user) {
    return (
      <div className={`min-h-screen ${darkMode ? 'bg-gray-900' : 'bg-gray-50'} flex items-center justify-center`}>
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <div className={`min-h-screen ${darkMode ? 'bg-gray-900' : 'bg-gray-50'} p-6 pb-24`}>
      <div className="max-w-md mx-auto space-y-4">
        <div className={`${cardClass} p-6 text-center`}>
          <div className="relative w-24 h-24 mx-auto mb-4">
            {picturePreview ? (
              <img
                src={picturePreview}
                alt="Profile"
                className="w-24 h-24 rounded-full object-cover border-4 border-blue-500"
              />
            ) : (
              <div className="w-24 h-24 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white text-3xl font-bold">
                {user?.name?.[0]?.toUpperCase() || '?'}
              </div>
            )}
            {isEditing && (
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="absolute bottom-0 right-0 bg-blue-500 hover:bg-blue-600 text-white p-2 rounded-full shadow-lg"
                aria-label="Change profile picture"
              >
                <Camera className="w-4 h-4" />
              </button>
            )}
            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp,image/gif"
              className="hidden"
              onChange={handlePictureSelect}
            />
          </div>

          {isEditing ? (
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className={`${inputClass} text-center font-bold text-lg mb-2`}
              placeholder="Your name"
              maxLength={100}
            />
          ) : (
            <h3 className="text-xl font-bold mb-1">{user?.name || 'Guest'}</h3>
          )}

          <p className={`text-sm ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>
            {user?.email || 'Not signed in'}
          </p>
        </div>

        <div className={`${cardClass} p-5`}>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-5 h-5 text-red-500" />
              <h4 className="font-semibold">Emergency Contact</h4>
            </div>
            {!isEditing && (
              <button
                type="button"
                onClick={() => {
                  resetForm();
                  setIsEditing(true);
                }}
                className="text-sm text-blue-500 hover:text-blue-600 font-medium"
              >
                Edit Profile
              </button>
            )}
          </div>

          {isEditing ? (
            <div className="space-y-3">
              <div>
                <label className="text-xs font-medium uppercase tracking-wide opacity-70">Name</label>
                <div className="relative mt-1">
                  <UserIcon className="absolute left-3 top-3.5 w-4 h-4 text-gray-400" />
                  <input
                    type="text"
                    value={contact.name}
                    onChange={(e) => setContact({ ...contact, name: e.target.value })}
                    className={`${inputClass} pl-10`}
                    placeholder="Contact name"
                  />
                </div>
              </div>
              <div>
                <label className="text-xs font-medium uppercase tracking-wide opacity-70">Phone</label>
                <div className="relative mt-1">
                  <Phone className="absolute left-3 top-3.5 w-4 h-4 text-gray-400" />
                  <input
                    type="tel"
                    value={contact.phone}
                    onChange={(e) => setContact({ ...contact, phone: e.target.value })}
                    className={`${inputClass} pl-10`}
                    placeholder="1234567890"
                  />
                </div>
              </div>
              <div>
                <label className="text-xs font-medium uppercase tracking-wide opacity-70">Email (optional)</label>
                <div className="relative mt-1">
                  <Mail className="absolute left-3 top-3.5 w-4 h-4 text-gray-400" />
                  <input
                    type="email"
                    value={contact.email || ''}
                    onChange={(e) => setContact({ ...contact, email: e.target.value })}
                    className={`${inputClass} pl-10`}
                    placeholder="contact@email.com"
                  />
                </div>
              </div>
              <div>
                <label className="text-xs font-medium uppercase tracking-wide opacity-70">Relationship</label>
                <input
                  type="text"
                  value={contact.relationship}
                  onChange={(e) => setContact({ ...contact, relationship: e.target.value })}
                  className={`${inputClass} mt-1`}
                  placeholder="e.g. Parent, Friend"
                />
              </div>
            </div>
          ) : user?.emergency_contacts?.[0] ? (
            <div className={`space-y-2 text-sm ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>
              <p><span className="font-medium">Name:</span> {user.emergency_contacts[0].name}</p>
              <p><span className="font-medium">Phone:</span> {user.emergency_contacts[0].phone}</p>
              {user.emergency_contacts[0].email && (
                <p><span className="font-medium">Email:</span> {user.emergency_contacts[0].email}</p>
              )}
              <p><span className="font-medium">Relationship:</span> {user.emergency_contacts[0].relationship}</p>
            </div>
          ) : (
            <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
              No emergency contact added yet.
            </p>
          )}
        </div>

        {error && (
          <div className="p-3 rounded-lg bg-red-50 text-red-700 text-sm border border-red-200">
            {error}
          </div>
        )}
        {success && (
          <div className="p-3 rounded-lg bg-green-50 text-green-700 text-sm border border-green-200">
            {success}
          </div>
        )}

        {isEditing ? (
          <div className="flex gap-3">
            <button
              type="button"
              onClick={() => {
                resetForm();
                setIsEditing(false);
              }}
              disabled={saving}
              className={`flex-1 flex items-center justify-center gap-2 p-4 rounded-xl ${
                darkMode ? 'bg-gray-800 text-white' : 'bg-white text-gray-700'
              } shadow-lg`}
            >
              <X className="w-5 h-5" />
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSave}
              disabled={saving || !name.trim()}
              className="flex-1 flex items-center justify-center gap-2 p-4 rounded-xl bg-blue-500 hover:bg-blue-600 text-white shadow-lg disabled:opacity-50"
            >
              {saving ? <Loader2 className="w-5 h-5 animate-spin" /> : <Save className="w-5 h-5" />}
              {saving ? 'Saving...' : 'Save'}
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            <button
              type="button"
              onClick={() => setDarkMode(!darkMode)}
              className={`w-full ${cardClass} p-4 text-left hover:scale-[1.01] transition-transform`}
            >
              <div className="flex items-center">
                {darkMode ? (
                  <Sun className="w-5 h-5 mr-3 text-yellow-500" />
                ) : (
                  <Moon className="w-5 h-5 mr-3 text-blue-500" />
                )}
                <span>Theme: {darkMode ? 'Dark' : 'Light'}</span>
              </div>
            </button>
            <button
              type="button"
              onClick={handleLogout}
              className={`w-full ${cardClass} p-4 text-left hover:scale-[1.01] transition-transform`}
            >
              <div className="flex items-center">
                <Settings className="w-5 h-5 mr-3 text-gray-500" />
                <span>Log out</span>
              </div>
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default ProfileScreen;
