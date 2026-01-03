import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Star, TrendingUp, Search, LogOut, User, MessageSquare, Shield, Bot as BotIcon, LayoutDashboard, Settings } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const RATING_OPTIONS = [
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

// --- COMPONENT: ADMIN VIEW (All Faculty List) ---
function AdminView({ user }) {
  const navigate = useNavigate();
  const [allFaculty, setAllFaculty] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const facultyRes = await axios.get(`${API}/faculty`);
      setAllFaculty(facultyRes.data);
    } catch (error) {
      console.error('Error loading faculty list:', error);
      toast.error('Failed to load faculty data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

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

              {/* ADMIN NAVIGATION: Only Admin Panel */}
              <nav className="hidden md:flex items-center gap-4">
                <Button
                  variant="ghost"
                  onClick={() => navigate('/admin')}
                  className="text-primary font-semibold hover:bg-primary/10"
                  data-testid="nav-admin-button"
                >
                  <Shield className="w-4 h-4 mr-2" />
                  Admin Panel
                </Button>
              </nav>
            </div>

            <div className="flex items-center gap-3">
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

        {/* Header Section */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <LayoutDashboard className="w-8 h-8 text-primary" />
            <div>
              <h1 className="text-3xl font-bold gradient-text">All Faculty Directory</h1>
              <p className="text-muted-foreground">
                View and manage all faculty records.
              </p>
            </div>
          </div>
        </div>

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
              data-testid="admin-search-input"
            />
          </div>
        </div>

        {/* Faculty List */}
        <div>
          <h2 className="text-2xl font-bold mb-4">
            {searchQuery ? `Search Results (${filteredFaculty.length})` : `All Faculty (${allFaculty.length})`}
          </h2>

          {loading ? (
            <div className="flex justify-center py-20">
              <div className="animate-spin rounded-full h-12 w-12 border-4 border-primary border-t-transparent"></div>
            </div>
          ) : filteredFaculty.length === 0 ? (
            <Card className="p-12">
              <p className="text-center text-muted-foreground">
                No faculty found matching your search.
              </p>
            </Card>
          ) : (
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filteredFaculty.map(faculty => (
                <Card
                  key={faculty.faculty_id}
                  className="hover-lift cursor-pointer transition-all"
                  onClick={() => navigate(`/faculty/${faculty.faculty_id}`)}
                  data-testid={`admin-faculty-card-${faculty.faculty_id}`}
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

                    {/* Admin View: Just Ratings */}
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

// --- COMPONENT: STUDENT VIEW (Recommendations, Interests, etc.) ---
function StudentDashboard({ user }) {
  const navigate = useNavigate();
  const [preferences, setPreferences] = useState(user?.preferences || []);
  const [aiInterests, setAiInterests] = useState(user?.ai_interests || []);
  const [recommendations, setRecommendations] = useState([]);
  const [allFaculty, setAllFaculty] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const facultyRes = await axios.get(`${API}/faculty`);
      setAllFaculty(facultyRes.data);

      // Only fetch recommendations if we have filters active
      if (preferences.length > 0 || aiInterests.length > 0) {
        const recsRes = await axios.get(`${API}/recommendations`);
        setRecommendations(recsRes.data);
      } else {
        setRecommendations([]);
      }
    } catch (error) {
      console.error('Error loading data:', error);
      toast.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  }, [preferences, aiInterests]); // Re-run when these change

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleSavePreferences = async () => {
    try {
      await axios.patch(`${API}/users/me`, {
        preferences: preferences,
        ai_interests: aiInterests
      });
      toast.success('Preferences updated successfully');
      // Reload data immediately to show new recommendations
      await loadData();
    } catch (error) {
      console.error('Error updating preferences:', error);
      toast.error('Failed to update preferences');
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

  // State flags for UI switching
  const showSearch = searchQuery.length > 0;
  const showAiRecommendations = aiInterests.length > 0 && preferences.length === 0;
  const showRatingRecommendations = preferences.length > 0 && aiInterests.length === 0;
  const showMixedRecommendations = preferences.length > 0 && aiInterests.length > 0;
  const showAllFaculty = !showSearch && !showAiRecommendations && !showRatingRecommendations && !showMixedRecommendations;

  const displayFaculty = showSearch
    ? filteredFaculty
    : (showAiRecommendations || showRatingRecommendations || showMixedRecommendations)
      ? recommendations
      : allFaculty;

  // Determine if we should show the score (Show only for Rating Prefs)
  const showCompatibilityScore = showRatingRecommendations || showMixedRecommendations;

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

              {/* STUDENT NAVIGATION: Only Home & Rankings */}
              <nav className="hidden md:flex items-center gap-4">
                <Button variant="ghost" onClick={() => navigate('/dashboard')} data-testid="nav-home-button">
                  Home
                </Button>
                <Button variant="ghost" onClick={() => navigate('/rankings')} data-testid="nav-rankings-button">
                  <TrendingUp className="w-4 h-4 mr-2" />
                  Rankings
                </Button>
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

        {/* AI / SEARCH INTERESTS */}
        <Card className="mb-8 border-l-4 border-primary bg-primary/5" data-testid="ai-interests-section">
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
                  className="flex items-center gap-2 cursor-pointer px-4 py-2 rounded-lg border border-border hover:bg-muted/50 transition-colors bg-white shadow-sm"
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
            <Button onClick={handleSavePreferences} className="w-full mt-4" data-testid="save-ai-preferences">
              Update Recommendations
            </Button>
          </CardContent>
        </Card>

        {/* TEACHING PREFERENCES */}
        <Card className="mb-8 hover-lift" data-testid="preferences-section">
          <CardHeader>
            <CardTitle>What matters most to you?</CardTitle>
            <p className="text-sm text-muted-foreground">Select your teaching preferences to get personalized recommendations</p>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-4">
              {RATING_OPTIONS.map(option => (
                <label
                  key={option.value}
                  className="flex items-center gap-2 cursor-pointer px-4 py-2 rounded-lg border border-border hover:bg-muted/50 transition-colors"
                  data-testid={`preference-${option.value}`}
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
          {showSearch && (
            <h2 className="text-2xl font-bold mb-4" data-testid="search-results-header">
              Search Results ({filteredFaculty.length})
            </h2>
          )}

          {showAiRecommendations && (
            <h2 className="text-2xl font-bold mb-4 text-primary" data-testid="recommended-header">
              AI/Project Recommendations
            </h2>
          )}

          {(showRatingRecommendations || showMixedRecommendations) && (
            <h2 className="text-2xl font-bold mb-4" data-testid="recommended-header">
              Recommended For You
            </h2>
          )}

          {!showSearch && !showAiRecommendations && !showRatingRecommendations && !showMixedRecommendations && (
            <h2 className="text-2xl font-bold mb-4" data-testid="all-faculty-header">
              All Faculty
            </h2>
          )}

          {loading ? (
            <div className="flex justify-center py-20">
              <div className="animate-spin rounded-full h-12 w-12 border-4 border-primary border-t-transparent"></div>
            </div>
          ) : displayFaculty.length === 0 ? (
            <Card className="p-12">
              <p className="text-center text-muted-foreground" data-testid="no-results-message">
                {searchQuery ? 'No faculty found matching your search' : 'No recommendations available. Try selecting some interests or preferences.'}
              </p>
            </Card>
          ) : (
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
              {displayFaculty.map(faculty => (
                <Card
                  key={faculty.faculty_id}
                  className="hover-lift cursor-pointer transition-all relative"
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

                    {/* AI REASON BADGE (Shown for AI-only or Mixed) */}
                    {showAiRecommendations && faculty.recommendation_reason && (
                      <div className="mb-3 p-3 bg-blue-50 border border-blue-200 rounded-md text-xs">
                        <p className="font-semibold text-blue-900 mb-1">Why you?</p>
                        <p className="text-blue-800 leading-relaxed">
                          {faculty.recommendation_reason}
                        </p>
                      </div>
                    )}

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

                      {/* COMPATIBILITY SCORE BADGE */}
                      {/* Only show if Rating Prefs are involved */}
                      {showCompatibilityScore && faculty.compatibility_percentage !== undefined && (
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

// --- MAIN EXPORT ---
export default function Dashboard({ user }) {
  if (user?.is_admin) {
    return <AdminView user={user} />;
  }

  return <StudentDashboard user={user} />;
}