import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { ArrowLeft, Upload, Save } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox'; // Added Checkbox
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const PREFERENCE_OPTIONS = [
  { value: 'teaching', label: 'Teaching Quality' },
  { value: 'attendance', label: 'Attendance Leniency' },
  { value: 'doubt_clarification', label: 'Doubt Clarification' }
];

export default function Profile({ user }) {
  const navigate = useNavigate();
  const [name, setName] = useState(user?.name || '');
  const [picture, setPicture] = useState(user?.picture || '');
  const [preferences, setPreferences] = useState(user?.preferences || []); // New State
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    try {
      setSaving(true);
      await axios.patch(`${API}/users/me`, {
        name: name || undefined,
        picture: picture || undefined,
        preferences: preferences // Include preferences in save
      });
      toast.success('Profile updated successfully');
    } catch (error) {
      console.error('Error updating profile:', error);
      toast.error('Failed to update profile');
    } finally {
      setSaving(false);
    }
  };

  const handlePreferenceToggle = (value) => {
    setPreferences(prev =>
      prev.includes(value)
        ? prev.filter(p => p !== value)
        : [...prev, value]
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-teal-50 via-white to-orange-50">
      <div className="container mx-auto px-6 py-8 max-w-4xl">
        <Button variant="ghost" onClick={() => navigate('/dashboard')} className="mb-6" data-testid="back-button">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Dashboard
        </Button>

        <h1 className="text-4xl font-bold gradient-text mb-8" data-testid="profile-header">My Profile</h1>

        <div className="grid gap-6 md:grid-cols-2">
          {/* Profile Information Card */}
          <Card className="md:col-span-2" data-testid="profile-card">
            <CardHeader>
              <CardTitle>Profile Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Avatar */}
              <div className="flex items-center gap-6">
                <Avatar className="w-24 h-24">
                  <AvatarImage src={picture} />
                  <AvatarFallback className="text-2xl">{name.charAt(0)}</AvatarFallback>
                </Avatar>
                <div className="flex-1">
                  <Label htmlFor="picture">Profile Picture URL</Label>
                  <div className="flex gap-2 mt-2">
                    <Input
                      id="picture"
                      value={picture}
                      onChange={(e) => setPicture(e.target.value)}
                      placeholder="Enter image URL or leave blank for default"
                      data-testid="picture-input"
                    />
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Leave blank to use your Google profile picture
                  </p>
                </div>
              </div>

              {/* Name */}
              <div>
                <Label htmlFor="name">Full Name *</Label>
                <Input
                  id="name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Enter your full name"
                  className="mt-2"
                  data-testid="name-input"
                />
              </div>

              {/* Email (Read-only) */}
              <div>
                <Label>Email</Label>
                <div className="mt-2 p-3 bg-muted rounded-md text-muted-foreground" data-testid="email-display">
                  {user?.email}
                </div>
              </div>

              {/* Admin Badge */}
              {user?.is_admin && (
                <div>
                  <Label>Role</Label>
                  <div className="mt-2">
                    <Badge variant="secondary" className="text-sm" data-testid="admin-badge">Administrator</Badge>
                  </div>
                </div>
              )}

              {/* Save Button */}
              <Button
                onClick={handleSave}
                disabled={saving}
                className="w-full"
                data-testid="save-profile-button"
              >
                <Save className="w-4 h-4 mr-2" />
                {saving ? 'Saving...' : 'Save Changes'}
              </Button>
            </CardContent>
          </Card>

          {/* NEW: Preferences Card */}
          <Card className="md:col-span-2">
            <CardHeader>
              <CardTitle>Recommendation Preferences</CardTitle>
              <p className="text-sm text-muted-foreground">Select the criteria that matter most to you for personalized faculty recommendations.</p>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-4">
                {PREFERENCE_OPTIONS.map(option => (
                  <label
                    key={option.value}
                    className="flex items-center gap-2 cursor-pointer px-4 py-2 rounded-lg border border-border hover:bg-muted/50 transition-colors"
                  >
                    <Checkbox
                      checked={preferences.includes(option.value)}
                      onCheckedChange={() => handlePreferenceToggle(option.value)}
                      data-testid={`preference-checkbox-${option.value}`}
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
        </div>
      </div>
    </div>
  );
}