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

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

axios.defaults.withCredentials = true;

export default function UserManagement({ user }) {
    const navigate = useNavigate();
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
            // Filter out self from the list first
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
        <div className="min-h-screen bg-gradient-to-br from-teal-50 via-white to-orange-50">
            <div className="container mx-auto px-6 py-8 max-w-6xl">
                <Button variant="ghost" onClick={() => navigate('/dashboard')} className="mb-6">
                    <ArrowLeft className="w-4 h-4 mr-2" />
                    Back to Dashboard
                </Button>

                <div className="flex items-center justify-between mb-8">
                    <div className="flex items-center gap-3">
                        <Shield className="w-8 h-8 text-primary" />
                        <h1 className="text-4xl font-bold gradient-text">User Management</h1>
                    </div>
                </div>

                <Card className="mb-8">
                    <CardContent className="p-6">
                        <div className="relative">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                            <Input
                                type="text"
                                placeholder="Search by name or email..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="pl-9 h-12 text-lg border-2"
                            />
                        </div>
                    </CardContent>
                </Card>

                {loading ? (
                    <div className="flex justify-center py-20">
                        <div className="animate-spin rounded-full h-12 w-12 border-4 border-primary border-t-transparent"></div>
                    </div>
                ) : filteredUsers.length === 0 ? (
                    <Card className="p-12">
                        <p className="text-center text-muted-foreground">
                            No users found.
                        </p>
                    </Card>
                ) : (
                    <div className="grid md:grid-cols-2 gap-6">
                        {filteredUsers.map(u => (
                            <Card key={u.user_id} className="hover-lift relative overflow-hidden">
                                {u.blocked && (
                                    <div className="absolute top-0 left-0 w-full h-1 bg-red-500"></div>
                                )}
                                <CardContent className="p-6">
                                    <div className="flex items-start gap-4 mb-4">
                                        <Avatar className="w-16 h-16">
                                            <AvatarImage src={u.picture} />
                                            <AvatarFallback className={u.blocked ? 'bg-red-100 text-red-600' : ''}>
                                                {u.name.charAt(0)}
                                            </AvatarFallback>
                                        </Avatar>
                                        <div className="flex-1">
                                            <h3 className={`font-semibold text-lg mb-1 ${u.blocked ? 'text-red-600' : ''}`}>
                                                {u.name}
                                                {u.blocked && <span className="ml-2 text-xs font-normal">(Blocked)</span>}
                                            </h3>
                                            <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
                                                <Mail className="w-3 h-3" />
                                                <span>{u.email}</span>
                                            </div>
                                            <div className="flex gap-2 mt-2">
                                                {u.is_admin && (
                                                    <Badge variant="default" className="bg-primary text-primary-foreground">Admin</Badge>
                                                )}
                                                {!u.is_admin && (
                                                    <Badge variant="secondary">Student</Badge>
                                                )}
                                            </div>
                                        </div>
                                    </div>

                                    <div className="grid grid-cols-2 gap-2 mt-4 pt-4 border-t">
                                        {/* Make Admin Button - Only if not admin */}
                                        {!u.is_admin && (
                                            <Button
                                                variant="outline"
                                                size="sm"
                                                onClick={() => handleMakeAdmin(u.user_id)}
                                                disabled={updating[u.user_id]}
                                                className="text-green-600 border-green-200 hover:bg-green-50"
                                            >
                                                <UserCheck className="w-3 h-3 mr-1" />
                                                Make Admin
                                            </Button>
                                        )}
                                        {/* If admin, just show a spacer or nothing, no revoke button */}
                                        {u.is_admin && (
                                            <div className="p-1"></div>
                                        )}

                                        <Button
                                            variant="outline"
                                            size="sm"
                                            onClick={() => handleToggleBlock(u.user_id)}
                                            disabled={updating[u.user_id]}
                                            className={u.blocked ? "text-green-600 border-green-200 hover:bg-green-50" : "text-red-600 border-red-200 hover:bg-red-50"}
                                        >
                                            {u.blocked ? 'Unblock User' : 'Block User'}
                                        </Button>
                                    </div>

                                    {/* View Profile Button for Admin */}
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        className="w-full mt-2"
                                        onClick={() => navigate(`/users/${u.user_id}`)}
                                    >
                                        View Full Profile
                                    </Button>
                                </CardContent>
                            </Card>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}