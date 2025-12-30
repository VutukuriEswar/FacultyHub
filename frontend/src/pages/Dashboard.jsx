import { useState, useEffect, useCallback } from 'react'; // Added useCallback
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Star, TrendingUp, Search, LogOut, User, MessageSquare, Shield } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const PREFERENCE_OPTIONS = [
  { value: 'teaching', label: 'Teaching Quality' },
  { value: 'attendance', label: 'Attendance Leniency' },
  { value: 'doubt_clarification', label: 'Doubt Clarification' }
];

export default function Dashboard({ user }) {
  const navigate = useNavigate();
  const [preferences, setPreferences] = useState(user?.preferences || []);
  const [recommendations, setRecommendations] = useState([]);
  const [allFaculty, setAllFaculty] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [facultyRes, recsRes] = await Promise.all([
        axios.get(`${API}/faculty`),
        preferences.length > 0 ? axios.get(`${API}/recommendations`) : Promise.resolve({ data: [] })
      ]);

      setAllFaculty(facultyRes.data);
      setRecommendations(recsRes.data);
    } catch (error) {
      console.error('Error loading data:', error);
      toast.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  }, [preferences]); // Dependency: preferences

  useEffect(() => {
    loadData();
  }, [loadData]); // Dependency: loadData

  const handlePreferenceToggle = async (value) => {
    const newPreferences = preferences.includes(value)
      ? preferences.filter(p => p !== value)
      : [...preferences, value];

    setPreferences(newPreferences);

    try {
      await axios.patch(`${API}/users/me`, { preferences: newPreferences });
    } catch (error) {
      console.error('Error updating preferences:', error);
    }
  };

  const handleLogout = async () => {
    try {
      await axios.post(`${API}/auth/logout`);
      toast.success('Logged out successfully');
      navigate('/');
    } catch (error) {
      console.error('Logout error:', error);
    }
  };

  const filteredFaculty = allFaculty.filter(f =>
    f.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    f.department.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const displayFaculty = searchQuery ? filteredFaculty : (recommendations.length > 0 ? recommendations : allFaculty);

  return (
    <div className="min-h-screen bg-gradient-to-br from-teal-50 via-white to-orange-50">
      {/* Header */}
      <header className="border-b border-border bg-white/80 backdrop-blur-md sticky top-0 z-50">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-8">
              <h1 className="text-2xl font-bold gradient-text cursor-pointer" onClick={() => navigate('/dashboard')}>
                VIT-AP Faculty Hub
              </h1>
              <nav className="hidden md:flex items-center gap-4">
                <Button variant="ghost" onClick={() => navigate('/dashboard')} data-testid="nav-home-button">
                  Home
                </Button>
                <Button variant="ghost" onClick={() => navigate('/rankings')} data-testid="nav-rankings-button">
                  <TrendingUp className="w-4 h-4 mr-2" />
                  Rankings
                </Button>
                {user?.is_admin && (
                  <Button variant="ghost" onClick={() => navigate('/admin')} data-testid="nav-admin-button">
                    <Shield className="w-4 h-4 mr-2" />
                    Admin
                  </Button>
                )}
              </nav>
            </div>

            <div className="flex items-center gap-3">
              <Button variant="ghost" size="icon" onClick={() => navigate('/chats')} data-testid="nav-chats-button">
                <MessageSquare className="w-5 h-5" />
              </Button>
              <Button variant="ghost" size="icon" onClick={() => navigate('/profile')} data-testid="nav-profile-button">
                <User className="w-5 h-5" />
              </Button>
              <Button variant="ghost" size="icon" onClick={handleLogout} data-testid="logout-button">
                <LogOut className="w-5 h-5" />
              </Button>
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-6 py-8">
        {/* Preferences Section */}
        <Card className="mb-8 hover-lift" data-testid="preferences-section">
          <CardHeader>
            <CardTitle>What matters most to you?</CardTitle>
            <p className="text-sm text-muted-foreground">Select your preferences to get personalized recommendations</p>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-4">
              {PREFERENCE_OPTIONS.map(option => (
                <label
                  key={option.value}
                  className="flex items-center gap-2 cursor-pointer px-4 py-2 rounded-lg border border-border hover:bg-muted/50 transition-colors"
                  data-testid={`preference-${option.value}`}
                >
                  <Checkbox
                    checked={preferences.includes(option.value)}
                    onCheckedChange={() => handlePreferenceToggle(option.value)}
                  />
                  <span className="text-sm font-medium">{option.label}</span>
                </label>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Search Bar */}
        <div className="mb-8">
          <div className="relative max-w-2xl mx-auto">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
            <Input
              type="text"
              placeholder="Search faculty by name or department..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-12 h-14 text-lg border-2"
              data-testid="search-input"
            />
          </div>
        </div>

        {/* Faculty List */}
        <div>
          {!searchQuery && recommendations.length > 0 && (
            <h2 className="text-2xl font-bold mb-4" data-testid="recommended-header">Recommended For You</h2>
          )}
          {!searchQuery && recommendations.length === 0 && preferences.length === 0 && (
            <h2 className="text-2xl font-bold mb-4" data-testid="all-faculty-header">All Faculty</h2>
          )}
          {searchQuery && (
            <h2 className="text-2xl font-bold mb-4" data-testid="search-results-header">
              Search Results ({filteredFaculty.length})
            </h2>
          )}

          {loading ? (
            <div className="flex justify-center py-20">
              <div className="animate-spin rounded-full h-12 w-12 border-4 border-primary border-t-transparent"></div>
            </div>
          ) : displayFaculty.length === 0 ? (
            <Card className="p-12">
              <p className="text-center text-muted-foreground" data-testid="no-results-message">
                {searchQuery ? 'No faculty found matching your search' : 'No faculty available'}
              </p>
            </Card>
          ) : (
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
              {displayFaculty.map(faculty => (
                <Card
                  key={faculty.faculty_id}
                  className="hover-lift cursor-pointer transition-all"
                  onClick={() => navigate(`/faculty/${faculty.faculty_id}`)}
                  data-testid={`faculty-card-${faculty.faculty_id}`}
                >
                  <CardContent className="p-6">
                    <div className="flex items-start gap-4 mb-4">
                      <Avatar className="w-16 h-16">
                        <AvatarImage src={faculty.image_url} />
                        <AvatarFallback>{faculty.name.charAt(0)}</AvatarFallback>
                      </Avatar>
                      <div className="flex-1">
                        <h3 className="font-semibold text-lg mb-1">{faculty.name}</h3>
                        <p className="text-sm text-muted-foreground mb-1">{faculty.designation}</p>
                        <Badge variant="secondary" className="text-xs">{faculty.department}</Badge>
                      </div>
                    </div>

                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-muted-foreground">Overall Rating</span>
                        <div className="flex items-center gap-1">
                          <Star className="w-4 h-4 fill-yellow-400 text-yellow-400" />
                          <span className="font-semibold">
                            {faculty.avg_ratings.overall.toFixed(1)}
                          </span>
                          <span className="text-xs text-muted-foreground">
                            ({faculty.rating_counts.overall})
                          </span>
                        </div>
                      </div>

                      {faculty.compatibility_percentage !== undefined && (
                        <div className="mt-3 pt-3 border-t border-border">
                          <div className="flex items-center justify-between">
                            <span className="text-sm font-medium text-primary">Compatibility</span>
                            <span className="text-lg font-bold text-primary">
                              {faculty.compatibility_percentage}%
                            </span>
                          </div>
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}