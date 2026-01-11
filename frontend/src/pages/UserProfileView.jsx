import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { ArrowLeft, Shield, UserCheck } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';

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

export default function UserProfileView({ user }) {
    const { userId } = useParams();
    const navigate = useNavigate();
    const [profileUser, setProfileUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const [updating, setUpdating] = useState(false);

    const loadUserProfile = useCallback(async () => {
        try {
            setLoading(true);
            const response = await axios.get(`${API}/users/${userId}`);
            setProfileUser(response.data);
        } catch (error) {
            console.error('Error loading user:', error);
            if (error.response?.status === 403) {
                toast.error('You do not have permission to view this profile');
                navigate('/dashboard');
            } else {
                toast.error('Failed to load user profile');
            }
        } finally {
            setLoading(false);
        }
    }, [userId, navigate]);

    useEffect(() => {
        loadUserProfile();
    }, [loadUserProfile]);

    const handleMakeAdmin = async () => {
        if (!window.confirm(`Are you sure you want to make ${profileUser.name} an admin?`)) {
            return;
        }

        setUpdating(true);
        try {
            await axios.patch(`${API}/admin/users/${userId}`, {
                is_admin: true
            });
            toast.success(`User is now an admin`);
            loadUserProfile(); // Reload to update UI
        } catch (error) {
            console.error('Error updating user:', error);
            toast.error(error.response?.data?.detail || 'Failed to update user');
        } finally {
            setUpdating(false);
        }
    };

    const handleToggleBlock = async () => {
        const action = profileUser.blocked ? 'unblock' : 'block';
        if (!window.confirm(`Are you sure you want to ${action} ${profileUser.name}?`)) {
            return;
        }

        setUpdating(true);
        try {
            await axios.patch(`${API}/admin/users/${userId}`, {
                blocked: !profileUser.blocked
            });
            toast.success(`User ${action}ed successfully`);
            loadUserProfile();
        } catch (error) {
            console.error('Error updating user:', error);
            toast.error(error.response?.data?.detail || 'Failed to update user');
        } finally {
            setUpdating(false);
        }
    };

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="animate-spin rounded-full h-12 w-12 border-4 border-primary border-t-transparent"></div>
            </div>
        );
    }

    if (!profileUser) {
        return null;
    }

    const isOwnProfile = user.user_id === profileUser.user_id;
    const isAdminViewing = user.is_admin && !isOwnProfile;

    return (
        <div className="min-h-screen bg-gradient-to-br from-teal-50 via-white to-orange-50">
            <div className="container mx-auto px-6 py-8 max-w-4xl">
                <Button variant="ghost" onClick={() => navigate(-1)} className="mb-6" data-testid="back-button">
                    <ArrowLeft className="w-4 h-4 mr-2" />
                    Back
                </Button>

                <h1 className="text-4xl font-bold gradient-text mb-8" data-testid="profile-header">
                    {isOwnProfile ? 'My Profile' : `${profileUser.name}'s Profile`}
                </h1>

                <div className="grid md:grid-cols-3 gap-6">
                    {/* Left Column: Profile Information */}
                    <Card className="md:col-span-2 h-fit relative overflow-hidden">
                        {profileUser.blocked && (
                            <div className="absolute top-0 left-0 w-full h-2 bg-red-500 z-10"></div>
                        )}
                        <CardHeader>
                            <CardTitle className="flex items-center justify-between">
                                <span>Profile Information</span>
                                {profileUser.is_admin && (
                                    <Badge variant="default" className="bg-primary text-primary-foreground">Admin</Badge>
                                )}
                                {!profileUser.is_admin && (
                                    <Badge variant="secondary">Student</Badge>
                                )}
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-6">
                            <div className="flex items-center gap-6">
                                <Avatar className="w-32 h-32 border-2">
                                    {profileUser.picture ? (
                                        <AvatarImage src={profileUser.picture} alt="Profile" className="w-full h-full object-cover" />
                                    ) : (
                                        <AvatarFallback className="w-full h-full text-4xl bg-slate-200 text-slate-500">
                                            {profileUser.name.charAt(0)}
                                        </AvatarFallback>
                                    )}
                                </Avatar>
                                <div>
                                    <h2 className="text-2xl font-bold">{profileUser.name}</h2>
                                    {profileUser.blocked && (
                                        <span className="inline-block mt-1 px-2 py-1 text-xs font-semibold text-red-600 bg-red-100 rounded">
                                            Account Blocked
                                        </span>
                                    )}
                                </div>
                            </div>

                            <div>
                                <label className="text-sm font-medium text-muted-foreground">Email</label>
                                <div className="mt-1 p-3 bg-muted rounded-md text-foreground font-mono text-sm break-all">
                                    {profileUser.email}
                                </div>
                            </div>

                            <div>
                                <label className="text-sm font-medium text-muted-foreground">User ID</label>
                                <div className="mt-1 p-3 bg-muted rounded-md text-foreground font-mono text-sm">
                                    {profileUser.user_id}
                                </div>
                            </div>

                            <div>
                                <label className="text-sm font-medium text-muted-foreground">Anonymous ID</label>
                                <div className="mt-1 p-3 bg-muted rounded-md text-foreground font-mono text-sm">
                                    {profileUser.anonymous_id}
                                </div>
                            </div>

                            {isOwnProfile && (
                                <div className="pt-4 border-t">
                                    <p className="text-sm text-muted-foreground">You are viewing your own profile.</p>
                                </div>
                            )}
                        </CardContent>
                    </Card>

                    <div className="space-y-6">
                        {/* Admin Controls */}
                        {isAdminViewing && (
                            <Card className="border-l-4 border-blue-400 bg-blue-50/10">
                                <CardHeader>
                                    <CardTitle className="flex items-center gap-2 text-blue-900">
                                        <Shield className="w-5 h-5" />
                                        Admin Controls
                                    </CardTitle>
                                </CardHeader>
                                <CardContent className="space-y-3">
                                    <p className="text-sm text-blue-800 mb-4">
                                        Manage {profileUser.name}'s account access and privileges.
                                    </p>

                                    {!profileUser.is_admin && (
                                        <Button
                                            variant="outline"
                                            className="w-full justify-start"
                                            onClick={handleMakeAdmin}
                                            disabled={updating}
                                        >
                                            <UserCheck className="w-4 h-4 mr-2" />
                                            Grant Admin Rights
                                        </Button>
                                    )}

                                    {profileUser.is_admin && (
                                        <div className="text-sm text-blue-900 bg-blue-100 p-2 rounded">
                                            User is already an Administrator.
                                        </div>
                                    )}

                                    <Button
                                        variant="outline"
                                        className={`w-full justify-start ${profileUser.blocked ? 'text-green-600 border-green-200 hover:bg-green-50' : 'text-red-600 border-red-200 hover:bg-red-50'}`}
                                        onClick={handleToggleBlock}
                                        disabled={updating}
                                    >
                                        {profileUser.blocked ? 'Unblock User Account' : 'Block User Account'}
                                    </Button>
                                </CardContent>
                            </Card>
                        )}

                        {/* Read-only Preferences */}
                        <Card>
                            <CardHeader>
                                <CardTitle>Teaching Preferences</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="flex flex-wrap gap-2">
                                    {profileUser.preferences && profileUser.preferences.length > 0 ? (
                                        profileUser.preferences.map(pref => (
                                            <Badge key={pref} variant="secondary">{pref}</Badge>
                                        ))
                                    ) : (
                                        <p className="text-sm text-muted-foreground italic">No preferences set</p>
                                    )}
                                </div>
                            </CardContent>
                        </Card>

                        <Card>
                            <CardHeader>
                                <CardTitle>AI & Research Interests</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="flex flex-wrap gap-2">
                                    {profileUser.ai_interests && profileUser.ai_interests.length > 0 ? (
                                        profileUser.ai_interests.map(interest => (
                                            <Badge key={interest} variant="secondary">{interest}</Badge>
                                        ))
                                    ) : (
                                        <p className="text-sm text-muted-foreground italic">No interests set</p>
                                    )}
                                </div>
                            </CardContent>
                        </Card>
                    </div>
                </div>
            </div>
        </div>
    );
}