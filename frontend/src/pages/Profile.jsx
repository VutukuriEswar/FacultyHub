import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { ArrowLeft, Save, Bot as BotIcon, Link as LinkIcon, CheckCircle, ShieldCheck } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { toast } from 'sonner';
import { useTheme } from '@/App';
import { signInWithGoogle } from '@/firebase';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

axios.defaults.withCredentials = true;

const PREFERENCE_OPTIONS = [
  { value: 'teaching', label: 'Teaching Quality' },
  { value: 'attendance', label: 'Attendance Leniency' },
  { value: 'doubt_clarification', label: 'Doubt Clarification' }
];

const AI_OPTIONS = [
  { value: 'Artificial Intelligence', label: 'Artificial Intelligence (AI)' },
  { value: 'Machine Learning', label: 'Machine Learning (ML)' },
  { value: 'Deep Learning', label: 'Deep Learning' },
  { value: 'Data Science', label: 'Data Science' },
  { value: 'Computer Vision', label: 'Computer Vision' },
  { value: 'Natural Language Processing', label: 'NLP' },
  { value: 'Robotics', label: 'Robotics' },
  { value: 'Neural Networks', label: 'Neural Networks' },
  { value: 'Internet of Things', label: 'IoT' },
  { value: 'Cybersecurity', label: 'Cybersecurity' },
  { value: 'Cloud Computing', label: 'Cloud Computing' },
  { value: 'Blockchain', label: 'Blockchain' }
];

export default function Profile({ user: initialUser }) {
  const navigate = useNavigate();
  const { theme } = useTheme();

  const [currentUser, setCurrentUser] = useState(initialUser);
  const [name, setName] = useState(initialUser?.name || '');
  const [picture, setPicture] = useState(initialUser?.picture || '');
  const [preferences, setPreferences] = useState(initialUser?.preferences || []);
  const [aiInterests, setAiInterests] = useState(initialUser?.ai_interests || []);
  const [customInterest, setCustomInterest] = useState('');
  const [saving, setSaving] = useState(false);
  const [linkingGoogle, setLinkingGoogle] = useState(false);
  const [googleLinked, setGoogleLinked] = useState(initialUser?.google_linked || false);

  useEffect(() => {
    const fetchUserData = async () => {
      try {
        const res = await axios.get(`${API}/auth/me`);
        setCurrentUser(res.data);
        setName(res.data.name || '');
        setPicture(res.data.picture || '');
        setPreferences(res.data.preferences || []);
        setAiInterests(res.data.ai_interests || []);
        setGoogleLinked(res.data.google_linked || false);
      } catch (error) {
        console.error("Failed to fetch user data", error);
        toast.error("Could not refresh profile data.");
      }
    };

    fetchUserData();
  }, []);

  const handleLinkGoogle = async () => {
    setLinkingGoogle(true);
    try {
      const { idToken } = await signInWithGoogle();
      await axios.post(`${API}/auth/link-google`, { id_token: idToken });
      setGoogleLinked(true);
      toast.success('Google account linked successfully!');
    } catch (error) {
      console.error('Google link error:', error);
      const msg =
        error?.message?.includes('@vitapstudent.ac.in')
          ? 'Only your @vitapstudent.ac.in Google account can be linked.'
          : error.response?.data?.detail || 'Failed to link Google account. Make sure you use your @vitapstudent.ac.in account.';
      toast.error(msg);
    } finally {
      setLinkingGoogle(false);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      await axios.patch(`${API}/users/me`, {
        name: name || undefined,
        picture: picture || undefined,
        preferences: preferences,
        ai_interests: aiInterests,
        theme_preference: theme
      });
      toast.success('Profile updated successfully');

      const res = await axios.get(`${API}/auth/me`);
      setCurrentUser(res.data);

    } catch (error) {
      console.error('Error updating profile:', error);
      toast.error('Failed to update profile');
    } finally {
      setSaving(false);
    }
  };

  const handlePreferenceToggle = (value, type) => {
    if (type === 'rating') {
      setPreferences(prev =>
        prev.includes(value)
          ? prev.filter(p => p !== value)
          : [...prev, value]
      );
    } else if (type === 'ai') {
      setAiInterests(prev =>
        prev.includes(value)
          ? prev.filter(p => p !== value)
          : [...prev, value]
      );
    }
  };

  const addCustomInterest = () => {
    if (!customInterest.trim()) return;
    const interest = customInterest.trim();

    if (!aiInterests.includes(interest)) {
      setAiInterests([...aiInterests, interest]);
      toast.success(`Added ${interest}`);
      setCustomInterest('');
    } else {
      toast.error('Interest already added');
    }
  };

  const removeInterest = (interest) => {
    setAiInterests(prev => prev.filter(i => i !== interest));
  };

  const isAdmin = currentUser?.is_admin || false;

  return (
    <div className={`min-h-screen transition-colors duration-300 ${theme === 'light' ? 'bg-gradient-to-br from-teal-50 via-white to-orange-50' : 'bg-slate-950'}`}>
      <div className="container mx-auto px-6 py-8 max-w-4xl">
        <Button
          variant="ghost"
          onClick={() => navigate('/dashboard')}
          className="mb-6 text-slate-500 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
          data-testid="back-button"
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Dashboard
        </Button>

        <h1 className="text-4xl font-bold gradient-text mb-8 text-slate-900 dark:text-slate-100" data-testid="profile-header">My Profile</h1>

        <div className="grid md:grid-cols-3 gap-6">
          <Card className="md:col-span-2 h-fit bg-white dark:bg-slate-900 dark:border-slate-800" data-testid="profile-card">
            <CardHeader>
              <CardTitle className="text-slate-900 dark:text-slate-100">Profile Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex flex-col items-center gap-6">
                <div className="relative group">
                  <Avatar className="w-32 h-32 border-2">
                    {picture ? (
                      <AvatarImage src={picture} alt="Profile" className="w-full h-full object-cover" />
                    ) : (
                      <AvatarFallback className="w-full h-full text-4xl bg-slate-200 dark:bg-slate-800 text-slate-500">
                        {name.charAt(0)}
                      </AvatarFallback>
                    )}
                  </Avatar>
                  <div className="absolute -bottom-2 -right-2 bg-slate-900 dark:bg-slate-900 text-white text-[10px] rounded-full w-6 h-6 flex items-center justify-center z-10 opacity-0 group-hover:opacity-100 transition-opacity">
                    <span className="font-bold">Upload</span>
                  </div>
                  <input
                    type="file"
                    accept="image/*"
                    onChange={(e) => {
                      const file = e.target.files[0];
                      if (file) {
                        const reader = new FileReader();
                        reader.onloadend = (event) => {
                          setPicture(event.target.result);
                        };
                        reader.readAsDataURL(file);
                      }
                    }}
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                    title="Upload profile picture"
                  />
                </div>
              </div>

              <div>
                <Label htmlFor="name" className="text-slate-700 dark:text-slate-300">Full Name</Label>
                <Input
                  id="name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Enter your full name"
                  className="mt-2 dark:bg-slate-900 dark:border-slate-700 dark:text-white"
                  data-testid="name-input"
                />
              </div>

              <div>
                <Label>Email</Label>
                <div className="mt-2 p-3 bg-muted dark:bg-slate-800 rounded-md text-muted-foreground dark:text-slate-300">
                  {currentUser?.email}
                </div>
              </div>

              <div>
                <Label>Role</Label>
                <div className="mt-2">
                  {currentUser?.is_admin && (
                    <Badge variant="secondary" className="bg-primary text-primary-foreground text-sm" data-testid="admin-badge">Administrator</Badge>
                  )}
                  {!currentUser?.is_admin && (
                    <Badge variant="outline" className="text-slate-700 dark:text-slate-300 text-sm">Student</Badge>
                  )}
                </div>
              </div>

              <Button
                onClick={handleSave}
                disabled={saving}
                className="w-full mt-6"
                data-testid="save-profile-button"
              >
                <Save className="w-4 h-4 mr-2" />
                {saving ? 'Saving...' : 'Save Changes'}
              </Button>
            </CardContent>
          </Card>

          <div className="space-y-6">
            <Card className={`bg-white dark:bg-slate-900 dark:border-slate-800 border-l-4 ${googleLinked ? 'border-l-green-500' : 'border-l-slate-300 dark:border-l-slate-600'}`}>
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-slate-900 dark:text-slate-100 text-base">
                  <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true" className="shrink-0">
                    <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z" />
                    <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z" />
                    <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z" />
                    <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z" />
                    <path fill="none" d="M0 0h48v48H0z" />
                  </svg>
                  Google Account
                </CardTitle>
              </CardHeader>
              <CardContent>
                {googleLinked ? (
                  <div className="flex flex-col gap-3">
                    <div className="flex items-center gap-3 p-3 rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800">
                      <ShieldCheck className="w-5 h-5 text-green-600 dark:text-green-400 shrink-0" />
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-semibold text-green-800 dark:text-green-300 truncate">Google account linked</p>
                        <p className="text-xs text-green-700 dark:text-green-400 truncate" title={currentUser?.email}>{currentUser?.email}</p>
                      </div>
                    </div>
                    <p className="text-xs text-slate-500 dark:text-slate-400 flex items-start gap-1.5 mt-1">
                      <CheckCircle className="w-3.5 h-3.5 text-slate-400 shrink-0 mt-[2px]" />
                      <span>Linked accounts cannot be removed for security reasons.</span>
                    </p>
                  </div>
                ) : (
                  <div className="flex flex-col gap-3">
                    <p className="text-sm text-slate-600 dark:text-slate-400">
                      Link your <span className="font-medium text-slate-800 dark:text-slate-200">@vitapstudent.ac.in</span> Google account to enable one-click sign-in.
                    </p>
                    <Button
                      id="link-google-btn"
                      onClick={handleLinkGoogle}
                      disabled={linkingGoogle}
                      variant="outline"
                      className="w-full flex items-center gap-2 border-2 border-slate-200 dark:border-slate-700 hover:border-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-all"
                    >
                      {linkingGoogle ? (
                        <span className="w-4 h-4 border-2 border-slate-400 border-t-transparent rounded-full animate-spin" />
                      ) : (
                        <LinkIcon className="w-4 h-4" />
                      )}
                      {linkingGoogle ? 'Linking...' : 'Link Google Account'}
                    </Button>
                    <p className="text-xs text-slate-400 dark:text-slate-500">
                      Once linked, you can sign in with Google. This cannot be undone.
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>

            {isAdmin && (
              <Card className="border-l-4 border-blue-400 dark:border-blue-600 bg-blue-50/10 dark:bg-blue-900/20">

                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-blue-900 dark:text-blue-200">
                    <BotIcon className="w-5 h-5" />
                    Administrator Access
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-6 pb-6 text-center">
                  <BotIcon className="w-12 h-12 text-blue-600 dark:text-blue-400 mx-auto mb-4" />
                  <h3 className="text-xl font-bold text-blue-900 dark:text-blue-200">Admin Mode</h3>
                  <p className="text-blue-800 dark:text-blue-300 max-w-md mx-auto">
                    As an Administrator, you manage system data.
                    <br />
                    Please use the <span className="font-semibold">Faculty</span> tab to manage faculty & the <span className="font-semibold">Users</span> tab to manage students.
                  </p>
                </CardContent>
              </Card>
            )}

            {!isAdmin && (
              <>
                <Card className="hover-lift bg-white dark:bg-slate-900 dark:border-slate-800" data-testid="preferences-section">
                  <CardHeader>
                    <CardTitle className="text-slate-900 dark:text-slate-100">Teaching Preferences</CardTitle>
                    <p className="text-sm text-slate-600 dark:text-slate-400">Select your teaching preferences to get personalized recommendations</p>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-wrap gap-4">
                      {PREFERENCE_OPTIONS.map(option => (
                        <label
                          key={option.value}
                          className="flex items-center gap-2 cursor-pointer px-4 py-2 rounded-lg border border-border hover:bg-muted/50 transition-colors bg-white dark:bg-slate-800 dark:border-slate-700"
                          data-testid={`preference-checkbox-${option.value}`}
                        >
                          <Checkbox
                            checked={preferences.includes(option.value)}
                            onCheckedChange={() => handlePreferenceToggle(option.value, 'rating')}
                          />
                          <span className="text-sm font-medium text-slate-900 dark:text-slate-100">{option.label}</span>
                        </label>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                <Card className="hover-lift bg-white dark:bg-slate-900 dark:border-slate-800" data-testid="ai-interests-section">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-slate-900 dark:text-slate-100">
                      <BotIcon className="w-5 h-5 text-primary dark:text-teal-400" />
                      AI & Research Interests
                    </CardTitle>
                    <p className="text-sm text-slate-600 dark:text-slate-400">Select your research topics to find professors working on specific projects (e.g., AI, Robotics, ML).</p>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-wrap gap-4">
                      {AI_OPTIONS.map(option => (
                        <label
                          key={option.value}
                          className="flex items-center gap-2 cursor-pointer px-4 py-2 rounded-lg border border-border hover:bg-muted/50 transition-colors bg-white dark:bg-slate-800 dark:border-slate-700"
                          data-testid={`ai-interest-${option.value}`}
                        >
                          <Checkbox
                            checked={aiInterests.includes(option.value)}
                            onCheckedChange={() => handlePreferenceToggle(option.value, 'ai')}
                          />
                          <span className="text-sm font-medium text-slate-900 dark:text-slate-100">{option.label}</span>
                        </label>
                      ))}
                    </div>

                    <div className="mt-6">
                      <Label className="text-slate-700 dark:text-slate-300">Add Custom Interest</Label>
                      <div className="flex gap-2 mt-2">
                        <Input
                          value={customInterest}
                          onChange={(e) => setCustomInterest(e.target.value)}
                          placeholder="e.g. Quantum Computing, Bioinformatics..."
                          className="dark:bg-slate-900 dark:border-slate-700 dark:text-white"
                          onKeyDown={(e) => e.key === 'Enter' && addCustomInterest()}
                        />
                        <Button onClick={addCustomInterest} variant="secondary">Add</Button>
                      </div>
                    </div>

                    <div className="mt-6">
                      <Label className="text-slate-700 dark:text-slate-300 mb-2 block">Your Selected Interests</Label>
                      <div className="flex flex-wrap gap-2">
                        {aiInterests.length === 0 && (
                          <span className="text-sm text-slate-500 italic">No interests selected yet.</span>
                        )}
                        {aiInterests.map((interest, idx) => (
                          <Badge key={idx} variant="secondary" className="px-3 py-1 text-sm bg-teal-100 text-teal-800 dark:bg-teal-900 dark:text-teal-100 flex items-center gap-2">
                            {interest}
                            <button
                              onClick={() => removeInterest(interest)}
                              className="hover:text-red-500 focus:outline-none"
                            >
                              x
                            </button>
                          </Badge>
                        ))}
                      </div>
                    </div>

                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-4">
                      Don't forget to click "Save Changes" to update your preferences.
                    </p>
                  </CardContent>
                </Card>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}