import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { ArrowLeft, ShieldCheck, UserCheck, UserX } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { useTheme } from '@/App';

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
    const { theme } = useTheme();
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
            loadUserProfile();
        } catch (error) {
            console.error('Error updating user:', error);
            toast.error(error.response?.data?.detail || 'Failed to update user');
        } finally {
            setUpdating(false);
        }
    };

    const handleToggleBlock = async () => {
        const action = profileUser.blocked ? 'unblock' : 'block';
        if (!window.confirm(`Are you sure you want to ${action} ${profileUser.name}? They will ${action === 'block' ? 'lose access' : 'regain access'} to the platform.`)) {
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
            <div className="min-h-screen flex items-center justify-center bg-slate-950">
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
        <div className={`min-h-screen transition-colors duration-300 ${theme === 'light' ? 'bg-gradient-to-br from-teal-50 via-white to-orange-50' : 'bg-slate-950'}`}>
            <div className="container mx-auto px-6 py-8 max-w-4xl">
                <Button
                    variant="ghost"
                    onClick={() => navigate(-1)}
                    className="mb-6 text-slate-500 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
                    data-testid="back-button"
                >
                    <ArrowLeft className="w-4 h-4 mr-2" />
                    Back
                </Button>

                <h1 className="text-4xl font-bold gradient-text mb-8 text-slate-900 dark:text-slate-100" data-testid="profile-header">
                    {isOwnProfile ? 'My Profile' : `Viewing ${profileUser.name}'s Profile`}
                </h1>

                <div className="grid md:grid-cols-3 gap-6">
                    <Card className="md:col-span-2 h-fit bg-white dark:bg-slate-900 dark:border-slate-800" data-testid="profile-card">
                        {profileUser.blocked && (
                            <div className="absolute top-0 left-0 w-full h-2 bg-red-500 z-10"></div>
                        )}
                        <CardHeader className="flex items-center justify-between">
                            <CardTitle className="text-slate-900 dark:text-slate-100">Profile Information</CardTitle>
                            {isAdminViewing && (
                                <Badge variant="secondary" className="bg-blue-600 text-white text-xs">Admin View</Badge>
                            )}
                        </CardHeader>
                        <CardContent className="space-y-6">
                            <div className="flex items-center gap-6">
                                <Avatar className="w-32 h-32 border-2">
                                    <AvatarImage src={profileUser.picture} alt="Profile" className="w-full h-full object-cover" />
                                    <AvatarFallback className="w-full h-full text-4xl bg-slate-200 dark:bg-slate-800 text-slate-500">
                                        {profileUser.name.charAt(0)}
                                    </AvatarFallback>
                                </Avatar>
                                <div className="flex-1">
                                    <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100">{profileUser.name}</h2>
                                    {profileUser.blocked && (
                                        <span className="inline-block mt-1 px-2 py-1 text-xs font-semibold text-red-600 bg-red-100 dark:bg-red-900 dark:text-red-200 rounded">
                                            Account Blocked
                                        </span>
                                    )}
                                </div>
                            </div>

                            <div>
                                <Label htmlFor="email" className="text-slate-700 dark:text-slate-300">Email</Label>
                                <div className="mt-1 p-3 bg-muted dark:bg-slate-800 rounded-md text-slate-600 dark:text-slate-400 font-mono text-sm break-all border border-transparent dark:border-slate-700">
                                    {profileUser.email}
                                </div>
                            </div>

                            <div>
                                <Label htmlFor="user_id" className="text-slate-700 dark:text-slate-300">User ID</Label>
                                <div className="mt-1 p-3 bg-muted dark:bg-slate-800 rounded-md text-slate-600 dark:text-slate-400 font-mono text-sm break-all border border-transparent dark:border-slate-700">
                                    {profileUser.user_id}
                                </div>
                            </div>

                            <div>
                                <Label htmlFor="anonymous_id" className="text-slate-700 dark:text-slate-300">Anonymous ID</Label>
                                <div className="mt-1 p-3 bg-muted dark:bg-slate-800 rounded-md text-slate-600 dark:text-slate-400 font-mono text-sm break-all border border-transparent dark:border-slate-700">
                                    {profileUser.anonymous_id}
                                </div>
                            </div>

                            <div className="pt-4 border-t border-border dark:border-slate-700">
                                <p className="text-sm text-slate-500 dark:text-slate-400">
                                    {isOwnProfile ? 'You are viewing your own profile.' : 'You are viewing another user\'s public profile.'}
                                </p>
                            </div>
                        </CardContent>
                    </Card>

                    <div className="space-y-6">
                        {isOwnProfile && user.is_admin && (
                            <Card className="border-l-4 border-blue-400 bg-blue-50/10 dark:bg-blue-900/20">
                                <CardHeader>
                                    <CardTitle className="flex items-center gap-2 text-blue-900 dark:text-blue-200">
                                        <ShieldCheck className="w-5 h-5" />
                                        Administrator Access
                                    </CardTitle>
                                </CardHeader>
                                <CardContent className="pt-6 pb-6 text-center">
                                    <div className="flex flex-col items-center gap-4">
                                        <ShieldCheck className="w-12 h-12 text-blue-600 dark:text-blue-400 mx-auto" />
                                        <h3 className="text-xl font-bold text-blue-900 dark:text-blue-200">
                                            Your Account Status
                                        </h3>
                                        <p className="text-blue-800 dark:text-blue-300 max-w-md mx-auto">
                                            You have full administrative privileges over the system.
                                        </p>
                                    </div>
                                </CardContent>
                            </Card>
                        )}

                        {isAdminViewing && (
                            <Card className="border-l-4 border-orange-400 bg-orange-50/10 dark:bg-orange-900/20">
                                <CardHeader>
                                    <CardTitle className="flex items-center gap-2 text-orange-900 dark:text-orange-200">
                                        <ShieldCheck className="w-5 h-5" />
                                        Manage User Access
                                    </CardTitle>
                                </CardHeader>
                                <CardContent className="pt-6 pb-6 space-y-3">
                                    {!profileUser.is_admin && (
                                        <Button
                                            variant="outline"
                                            className="w-full justify-start text-blue-600 border-blue-200 hover:bg-blue-50 dark:text-blue-400 dark:border-blue-600 dark:hover:bg-blue-900"
                                            onClick={handleMakeAdmin}
                                            disabled={updating}
                                        >
                                            <UserCheck className="w-4 h-4 mr-2" />
                                            Grant Admin Rights
                                        </Button>
                                    )}

                                    <Button
                                        variant="outline"
                                        className={`w-full justify-start ${profileUser.blocked ? "text-green-600 border-green-200 hover:bg-green-50 dark:text-green-400 dark:border-green-600 dark:hover:bg-green-900" : "text-red-600 border-red-200 hover:bg-red-50 dark:text-red-400 dark:border-red-600 dark:hover:bg-red-900"}`}
                                        onClick={handleToggleBlock}
                                        disabled={updating}
                                    >
                                        {profileUser.blocked ? 'Unblock User Account' : 'Block User Account'}
                                    </Button>
                                </CardContent>
                            </Card>
                        )}

                        {!isAdminViewing && (
                            <>
                                <Card className="hover-lift bg-white dark:bg-slate-900 dark:border-slate-800" data-testid="preferences-section">
                                    <CardHeader>
                                        <CardTitle className="text-slate-900 dark:text-slate-100">Teaching Preferences</CardTitle>
                                    </CardHeader>
                                    <CardContent>
                                        <div className="flex flex-wrap gap-4">
                                            {profileUser.preferences && profileUser.preferences.length > 0 ? (
                                                profileUser.preferences.map(pref => (
                                                    <Badge key={pref} variant="secondary" className="text-sm dark:bg-slate-800 dark:text-slate-300">{pref}</Badge>
                                                ))
                                            ) : (
                                                <p className="text-sm text-slate-500 dark:text-slate-400 italic">No preferences set</p>
                                            )}
                                        </div>
                                    </CardContent>
                                </Card>

                                <Card className="hover-lift bg-white dark:bg-slate-900 dark:border-slate-800" data-testid="ai-interests-section">
                                    <CardHeader>
                                        <CardTitle className="text-slate-900 dark:text-slate-100">AI & Research Interests</CardTitle>
                                    </CardHeader>
                                    <CardContent>
                                        <div className="flex flex-wrap gap-4">
                                            {profileUser.ai_interests && profileUser.ai_interests.length > 0 ? (
                                                profileUser.ai_interests.map(interest => (
                                                    <Badge key={interest} variant="secondary" className="text-sm dark:bg-slate-800 dark:text-slate-300">{interest}</Badge>
                                                ))
                                            ) : (
                                                <p className="text-sm text-slate-500 dark:text-slate-400 italic">No interests set</p>
                                            )}
                                        </div>
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