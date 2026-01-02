import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { ArrowLeft, Upload, Save, Bot as BotIcon } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Ensure cookies are sent
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

export default function Profile({ user }) {
  const navigate = useNavigate();
  const [name, setName] = useState(user?.name || '');
  const [picture, setPicture] = useState(user?.picture || '');
  const [preferences, setPreferences] = useState(user?.preferences || []);
  const [aiInterests, setAiInterests] = useState(user?.ai_interests || []);
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    try {
      setSaving(true);
      await axios.patch(`${API}/users/me`, {
        name: name || undefined,
        picture: picture || undefined,
        preferences: preferences,
        ai_interests: aiInterests
      });
      toast.success('Profile updated successfully');
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

  // Admin Check
  const isAdmin = user?.is_admin || false;

  return (
    <div className="min-h-screen bg-gradient-to-br from-teal-50 via-white to-orange-50">
      <div className="container mx-auto px-6 py-8 max-w-4xl">
        <Button variant="ghost" onClick={() => navigate('/dashboard')} className="mb-6" data-testid="back-button">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Dashboard
        </Button>

        <h1 className="text-4xl font-bold gradient-text mb-8" data-testid="profile-header">My Profile</h1>

        <div className="grid md:grid-cols-3 gap-6">
          {/* Left Column: Profile Information */}
          <Card className="md:col-span-2 h-fit" data-testid="profile-card">
            <CardHeader>
              <CardTitle>Profile Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Avatar Upload */}
              <div className="flex flex-col items-center gap-6">
                <div className="relative group">
                  <Avatar className="w-32 h-32 border-2">
                    {picture ? (
                      <AvatarImage src={picture} alt="Profile" className="w-full h-full object-cover" />
                    ) : (
                      <AvatarFallback className="w-full h-full text-4xl bg-slate-200 text-slate-500">
                        {name.charAt(0)}
                      </AvatarFallback>
                    )}
                  </Avatar>
                  <div className="absolute -bottom-2 -right-2 bg-slate-900 text-white text-[10px] rounded-full w-6 h-6 flex items-center justify-center z-10 opacity-0 group-hover:opacity-100 transition-opacity">
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

              {/* Input Fields */}
              <div>
                <Label htmlFor="name">Full Name</Label>
                <Input
                  id="name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Enter your full name"
                  className="mt-2"
                  data-testid="name-input"
                />
              </div>

              <div>
                <Label>Email</Label>
                <div className="mt-2 p-3 bg-muted rounded-md text-muted-foreground">
                  {user?.email}
                </div>
              </div>

              <div>
                <Label>Role</Label>
                <div className="mt-2">
                  {user?.is_admin && (
                    <Badge variant="secondary" className="text-sm" data-testid="admin-badge">Administrator</Badge>
                  )}
                  {!user?.is_admin && (
                    <Badge variant="outline" className="text-sm">Student</Badge>
                  )}
                </div>
              </div>

              {/* Save Button */}
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

          {/* Right Column Content */}
          <div className="space-y-6">

            {/* ADMIN: Show Admin Info Box */}
            {isAdmin && (
              <Card className="border-l-4 border-blue-400 bg-blue-50/10">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-blue-900">
                    <BotIcon className="w-5 h-5" />
                    Administrator Access
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-6 pb-6 text-center">
                  <BotIcon className="w-12 h-12 text-blue-600 mx-auto mb-4" />
                  <h3 className="text-xl font-bold text-blue-900">Admin Mode</h3>
                  <p className="text-blue-800 max-w-md mx-auto">
                    As an Administrator, you manage system data.
                    <br />
                    Please use the <span className="font-semibold">Admin Panel</span> to manage faculty & sync data.
                  </p>
                </CardContent>
              </Card>
            )}

            {/* STUDENT: Show Preferences */}
            {!isAdmin && (
              <>
                <Card className="hover-lift" data-testid="preferences-section">
                  <CardHeader>
                    <CardTitle>Teaching Preferences</CardTitle>
                    <p className="text-sm text-muted-foreground">Select your teaching preferences to get personalized recommendations</p>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-wrap gap-4">
                      {PREFERENCE_OPTIONS.map(option => (
                        <label
                          key={option.value}
                          className="flex items-center gap-2 cursor-pointer px-4 py-2 rounded-lg border border-border hover:bg-muted/50 transition-colors"
                          data-testid={`preference-checkbox-${option.value}`}
                        >
                          <Checkbox
                            checked={preferences.includes(option.value)}
                            onCheckedChange={() => handlePreferenceToggle(option.value, 'rating')}
                          />
                          <span className="text-sm font-medium">{option.label}</span>
                        </label>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                <Card className="hover-lift" data-testid="ai-interests-section">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <BotIcon className="w-5 h-5 text-primary" />
                      AI & Research Interests
                    </CardTitle>
                    <p className="text-sm text-muted-foreground">
                      Select your research topics to find professors working on specific projects (e.g., AI, Robotics, ML).
                    </p>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-wrap gap-4">
                      {AI_OPTIONS.map(option => (
                        <label
                          key={option.value}
                          className="flex items-center gap-2 cursor-pointer px-4 py-2 rounded-lg border border-border hover:bg-muted/50 transition-colors"
                          data-testid={`ai-interest-${option.value}`}
                        >
                          <Checkbox
                            checked={aiInterests.includes(option.value)}
                            onCheckedChange={() => handlePreferenceToggle(option.value, 'ai')}
                          />
                          <span className="text-sm font-medium">{option.label}</span>
                        </label>
                      ))}
                    </div>
                    <p className="text-xs text-muted-foreground mt-4">
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