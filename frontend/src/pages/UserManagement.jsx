import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { ArrowLeft, Shield, UserCheck, UserX, Search, Mail } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { useTheme } from '@/App';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

axios.defaults.withCredentials = true;

export default function UserManagement({ user }) {
    const navigate = useNavigate();
    const { theme, toggleTheme } = useTheme();
    const [users, setUsers] = useState([]);
    const [filteredUsers, setFilteredUsers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [updating, setUpdating] = useState({});

    useEffect(() => {
        if (!user?.is_admin) {
            toast.error('Admin access required');
            navigate('/dashboard');
            return;
        }
        loadUsers();
    }, [user, navigate]);

    useEffect(() => {
        const lowerQuery = searchQuery.toLowerCase();
        const filtered = users.filter(u =>
            u.user_id !== user.user_id &&
            (u.name.toLowerCase().includes(lowerQuery) || u.email.toLowerCase().includes(lowerQuery))
        );
        setFilteredUsers(filtered);
    }, [searchQuery, users, user.user_id]);

    const loadUsers = async () => {
        try {
            setLoading(true);
            const response = await axios.get(`${API}/admin/users`);
            setUsers(response.data);
        } catch (error) {
            console.error('Error loading users:', error);
            toast.error('Failed to load users');
        } finally {
            setLoading(false);
        }
    };

    const handleMakeAdmin = async (targetUserId) => {
        const targetUser = users.find(u => u.user_id === targetUserId);
        if (!targetUser) return;

        if (!window.confirm(`Are you sure you want to make ${targetUser.name} an admin?`)) {
            return;
        }

        setUpdating(prev => ({ ...prev, [targetUserId]: true }));

        try {
            await axios.patch(`${API}/admin/users/${targetUserId}`, {
                is_admin: true
            });
            toast.success(`User is now an admin`);
            loadUsers();
        } catch (error) {
            console.error('Error updating user:', error);
            toast.error(error.response?.data?.detail || 'Failed to update user');
        } finally {
            setUpdating(prev => ({ ...prev, [targetUserId]: false }));
        }
    };

    const handleToggleBlock = async (targetUserId) => {
        const targetUser = users.find(u => u.user_id === targetUserId);
        if (!targetUser) return;

        const action = targetUser.blocked ? 'unblock' : 'block';
        if (!window.confirm(`Are you sure you want to ${action} ${targetUser.name}? They will ${action === 'block' ? 'lose access' : 'regain access'} to the platform.`)) {
            return;
        }

        setUpdating(prev => ({ ...prev, [targetUserId]: true }));

        try {
            await axios.patch(`${API}/admin/users/${targetUserId}`, {
                blocked: !targetUser.blocked
            });
            toast.success(`User ${action}ed successfully`);
            loadUsers();
        } catch (error) {
            console.error('Error updating user:', error);
            toast.error(error.response?.data?.detail || 'Failed to update user');
        } finally {
            setUpdating(prev => ({ ...prev, [targetUserId]: false }));
        }
    };

    return (
        <div className={`min-h-screen transition-colors duration-300 ${theme === 'light' ? 'bg-gradient-to-br from-teal-50 via-white to-orange-50' : 'bg-slate-950'}`}>
            <div className="container mx-auto px-6 py-8 max-w-6xl">
                <Button
                    variant="ghost"
                    onClick={() => navigate('/dashboard')}
                    className="mb-6 text-slate-500 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
                    data-testid="back-button"
                >
                    <ArrowLeft className="w-4 h-4 mr-2" />
                    Back to Dashboard
                </Button>

                <div className="flex items-center justify-between mb-8">
                    <div className="flex items-center gap-3">
                        <Shield className="w-8 h-8 text-primary dark:text-teal-400" />
                        <h1 className="text-4xl font-bold gradient-text text-slate-900 dark:text-slate-100">User Management</h1>
                    </div>
                </div>

                <Card className="mb-8 bg-white dark:bg-slate-900 dark:border-slate-800">
                    <CardContent className="p-6">
                        <div className="relative">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                            <Input
                                type="text"
                                placeholder="Search by name or email..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="pl-9 h-12 text-lg border-2 dark:bg-slate-900 dark:border-slate-700 dark:text-white"
                                data-testid="user-search-input"
                            />
                        </div>
                    </CardContent>
                </Card>

                {loading ? (
                    <div className="flex justify-center py-20">
                        <div className="animate-spin rounded-full h-12 w-12 border-4 border-primary border-t-transparent"></div>
                    </div>
                ) : filteredUsers.length === 0 ? (
                    <Card className="p-12 dark:bg-slate-900 dark:border-slate-800">
                        <p className="text-center text-slate-600 dark:text-slate-400">
                            No users found matching your search.
                        </p>
                    </Card>
                ) : (
                    <div className="grid md:grid-cols-2 gap-6">
                        {filteredUsers.map(u => (
                            <Card key={u.user_id} className="hover-lift relative overflow-hidden bg-white dark:bg-slate-900 dark:border-slate-700">
                                {u.blocked && (
                                    <div className="absolute top-0 left-0 w-full h-1 bg-red-500 z-10"></div>
                                )}
                                <CardContent className="p-6">
                                    <div className="flex items-start gap-4 mb-4">
                                        <Avatar className="w-16 h-16">
                                            <AvatarImage src={u.picture} />
                                            <AvatarFallback className={u.blocked ? 'bg-red-100 text-red-600' : 'bg-slate-100 dark:bg-slate-800 text-slate-500'}>
                                                {u.name.charAt(0)}
                                            </AvatarFallback>
                                        </Avatar>
                                        <div className="flex-1">
                                            <h3 className={`font-semibold text-lg mb-1 ${u.blocked ? 'text-red-600' : 'text-slate-900 dark:text-slate-100'}`}>
                                                {u.name}
                                                {u.blocked && <span className="ml-2 text-xs font-normal text-red-500">(Blocked)</span>}
                                            </h3>
                                            <p className="text-sm text-slate-500 dark:text-slate-400 mb-1">{u.email}</p>
                                            <div className="flex gap-2 mt-2">
                                                <Mail className="w-3 h-3 text-slate-500 dark:text-slate-400" />
                                                <span className="text-xs text-slate-400 dark:text-slate-500 font-mono break-all">{u.email}</span>
                                            </div>
                                        </div>
                                    </div>

                                    <div className="flex gap-2">
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            onClick={() => navigate(`/users/${u.user_id}`)}
                                            className="flex-1 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
                                            data-testid={`view-profile-${u.user_id}`}
                                        >
                                            View Full Profile
                                        </Button>
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            onClick={() => handleMakeAdmin(u.user_id)}
                                            disabled={updating[u.user_id]}
                                            className="flex-1 text-green-600 border-green-200 hover:bg-green-50 dark:text-green-400 dark:border-green-600 dark:hover:bg-green-900"
                                            data-testid={`make-admin-${u.user_id}`}
                                        >
                                            <UserCheck className="w-3 h-3 mr-1" />
                                            Make Admin
                                        </Button>
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            onClick={() => handleToggleBlock(u.user_id)}
                                            disabled={updating[u.user_id]}
                                            className={`flex-1 ${u.blocked ? "text-red-600 border-red-200 hover:bg-red-50 dark:text-red-400 dark:border-red-600 dark:hover:bg-red-900" : "text-green-600 border-green-200 hover:bg-green-50 dark:text-green-400 dark:border-green-600 dark:hover:bg-green-900"}`}
                                            data-testid={`toggle-block-${u.user_id}`}
                                        >
                                            {u.blocked ? 'Unblock User' : 'Block User'}
                                        </Button>
                                    </div>
                                </CardContent>
                            </Card>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}