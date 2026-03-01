import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Star, TrendingUp, Search, LogOut, User, MessageSquare, Shield, Bot as BotIcon, LayoutDashboard, Settings, Users, Moon, Sun, X, Save } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { toast } from 'sonner';
import { useTheme } from '@/App';

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

function AdminView({ user }) {
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();
  const [allFaculty, setAllFaculty] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const facultyRes = await axios.get(`${API}/faculty`, { withCredentials: true });
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
      await axios.post(`${API}/auth/logout`, {}, { withCredentials: true });
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
    <div className={`min-h-screen transition-colors duration-300 ${theme === 'light' ? 'bg-gradient-to-br from-teal-50 via-white to-orange-50' : 'bg-slate-950'}`}>
      <header className="border-b border-border bg-white/80 dark:bg-slate-900/80 backdrop-blur-md sticky top-0 z-50">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-8">
              <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-teal-600 to-orange-500 cursor-pointer" onClick={() => navigate('/dashboard')}>
                VIT-AP Faculty Hub
              </h1>

              <nav className="hidden md:flex items-center gap-4">
                <Button variant="ghost" onClick={() => navigate('/admin')} className="text-teal-600 dark:text-teal-400 font-semibold hover:bg-teal-50 dark:hover:bg-teal-950" data-testid="nav-admin-button">
                  <Settings className="w-4 h-4 mr-2" /> Faculty
                </Button>
                <Button variant="ghost" onClick={() => navigate('/admin/users')} className="text-blue-600 dark:text-blue-400 font-semibold hover:bg-blue-50 dark:hover:bg-blue-950">
                  <Users className="w-4 h-4 mr-2" /> Users
                </Button>
              </nav>
            </div>

            <div className="flex items-center gap-3">
              <Button variant="ghost" size="icon" onClick={() => toggleTheme(theme === 'light' ? 'dark' : 'light')} className="text-slate-500 dark:text-slate-300" data-testid="theme-toggle">
                {theme === 'light' ? <Moon className="w-5 h-5" /> : <Sun className="w-5 h-5 text-orange-400" />}
              </Button>
              <Button variant="ghost" size="icon" onClick={() => navigate('/chats')} className="text-slate-500 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 relative" data-testid="nav-chats-button">
                <MessageSquare className="w-5 h-5" />
              </Button>
              <Button variant="ghost" size="icon" onClick={() => navigate('/profile')} className="text-slate-500 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800" data-testid="nav-profile-button">
                <User className="w-5 h-5" />
              </Button>
              <Button variant="ghost" size="icon" onClick={handleLogout} className="text-slate-500 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800" data-testid="logout-button">
                <LogOut className="w-5 h-5" />
              </Button>
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-6 py-8">
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <LayoutDashboard className="w-8 h-8 text-teal-600 dark:text-teal-400" />
            <div>
              <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-100">All Faculty Directory</h1>
              <p className="text-slate-600 dark:text-slate-400">View and manage all faculty records.</p>
            </div>
          </div>
        </div>

        <div className="mb-8">
          <div className="relative max-w-2xl mx-auto">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
            <Input type="text" placeholder="Search faculty by name or department..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="pl-12 h-14 text-lg border-2 dark:bg-slate-900 dark:border-slate-700 dark:text-white" data-testid="admin-search-input" />
          </div>
        </div>

        <div>
          <h2 className="text-2xl font-bold mb-4 text-slate-900 dark:text-slate-100">
            {searchQuery ? `Search Results (${filteredFaculty.length})` : `All Faculty (${allFaculty.length})`}
          </h2>
          {loading ? (
            <div className="flex justify-center py-20"><div className="animate-spin rounded-full h-12 w-12 border-4 border-teal-600 border-t-transparent"></div></div>
          ) : filteredFaculty.length === 0 ? (
            <Card className="p-12 dark:bg-slate-900 dark:border-slate-800"><p className="text-center text-slate-600 dark:text-slate-400">No faculty found matching your search.</p></Card>
          ) : (
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filteredFaculty.map(faculty => (
                <Card key={faculty.faculty_id} className="hover-lift cursor-pointer transition-all bg-white dark:bg-slate-900 dark:border-slate-700" onClick={() => navigate(`/faculty/${faculty.faculty_id}`)} data-testid={`admin-faculty-card-${faculty.faculty_id}`}>
                  <CardContent className="p-6">
                    <div className="flex items-start gap-4 mb-4">
                      <Avatar className="w-16 h-16">
                        <AvatarImage src={faculty.image_url} />
                        <AvatarFallback>{faculty.name.charAt(0)}</AvatarFallback>
                      </Avatar>
                      <div className="flex-1">
                        <h3 className="font-semibold text-lg text-slate-900 dark:text-slate-100">{faculty.name}</h3>
                        <p className="text-sm text-slate-500 dark:text-slate-400 mb-1">{faculty.designation}</p>
                        <Badge variant="secondary" className="text-xs dark:bg-slate-800 dark:text-slate-300">{faculty.department}</Badge>
                      </div>
                    </div>
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-slate-500 dark:text-slate-400">Overall Rating</span>
                        <div className="flex items-center gap-1">
                          <Star className="w-4 h-4 fill-yellow-400 text-yellow-400" />
                          <span className="font-semibold text-slate-900 dark:text-slate-100">{faculty.avg_ratings.overall.toFixed(1)}</span>
                          <span className="text-xs text-slate-400 dark:text-slate-500">({faculty.rating_counts.overall})</span>
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

function StudentDashboard({ user }) {
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();

  const [preferences, setPreferences] = useState(user?.preferences || []);
  const [allFaculty, setAllFaculty] = useState([]);
  const [recommendationResults, setRecommendationResults] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [activeRecSource, setActiveRecSource] = useState(null);
  const [unreadCount, setUnreadCount] = useState(0);

  const [aiInterests, setAiInterests] = useState(() => {
    const saved = sessionStorage.getItem('dashboard_ai_interests');
    return saved ? JSON.parse(saved) : [];
  });

  const [customInterest, setCustomInterest] = useState('');

  useEffect(() => {
    sessionStorage.setItem('dashboard_ai_interests', JSON.stringify(aiInterests));
  }, [aiInterests]);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const facultyRes = await axios.get(`${API}/faculty`, { withCredentials: true });
      setAllFaculty(facultyRes.data);
      setRecommendationResults([]);
      setActiveRecSource(null);

      const countRes = await axios.get(`${API}/chats/unread-count`, { withCredentials: true });
      setUnreadCount(countRes.data.total_unread);
    } catch (error) {
      console.error('Error loading data:', error);
      toast.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  useEffect(() => {
    if (preferences.length > 0) {
      fetchPreferenceRecommendations();
    } else {
      if (activeRecSource === 'preferences') {
        setRecommendationResults([]);
        setActiveRecSource(null);
      }
    }
  }, [preferences]);

  const fetchPreferenceRecommendations = async () => {
    try {
      setLoading(true);
      const res = await axios.get(`${API}/recommendations`, {
        params: { preferences: preferences.join(",") },
        withCredentials: true
      });
      setRecommendationResults(res.data);
      setActiveRecSource('preferences');
      if (res.data.length === 0) {
        toast.info("No faculty found with ratings for selected preferences.");
      }
    } catch (error) {
      toast.error("Failed to fetch recommendations");
    } finally {
      setLoading(false);
    }
  };

  const fetchOnSpotRecommendations = async () => {
    if (aiInterests.length === 0) {
      toast.error("Please select or add interests first.");
      return;
    }
    try {
      setLoading(true);
      const res = await axios.get(`${API}/recommendations`, {
        params: { interests: aiInterests.join(","), preferences: preferences.join(",") },
        withCredentials: true
      });
      setRecommendationResults(res.data);
      setActiveRecSource('interests');
      toast.success(`Found ${res.data.length} matches`);
    } catch (error) {
      toast.error("Failed to fetch recommendations");
    } finally {
      setLoading(false);
    }
  };

  const loadProfileRecommendations = async () => {
    try {
      setLoading(true);
      const meRes = await axios.get(`${API}/auth/me`, { withCredentials: true });
      const profileInterests = meRes.data.ai_interests || [];

      setAiInterests(profileInterests);

      if (profileInterests.length === 0) {
        toast.info("No interests found in your profile. Please update your profile.");
        setLoading(false);
        return;
      }

      const recRes = await axios.get(`${API}/recommendations`, {
        params: { interests: profileInterests.join(",") },
        withCredentials: true
      });
      setRecommendationResults(recRes.data);
      setActiveRecSource('profile');
      toast.success("Loaded profile recommendations");
    } catch (error) {
      toast.error("Failed to load profile recommendations");
    } finally {
      setLoading(false);
    }
  };

  const clearSelections = () => {
    setAiInterests([]);
    setCustomInterest('');
    setRecommendationResults([]);
    setActiveRecSource(null);
    toast.info("Cleared AI interests selections and results");
  };

  const saveToProfile = async () => {
    try {
      await axios.patch(`${API}/users/me`,
        { ai_interests: aiInterests },
        { withCredentials: true }
      );
      toast.success("Interests saved to profile!");
    } catch (error) {
      console.error("Save error:", error);
      toast.error("Failed to save interests.");
    }
  };

  const handlePreferenceToggle = (value, type) => {
    if (type === 'rating') {
      setPreferences(prev => prev.includes(value) ? prev.filter(p => p !== value) : [...prev, value]);
    } else if (type === 'ai') {
      setAiInterests(prev => prev.includes(value) ? prev.filter(p => p !== value) : [...prev, value]);
    }
  };

  const addCustomInterest = () => {
    if (!customInterest.trim()) return;
    const interest = customInterest.trim();
    if (!aiInterests.includes(interest)) {
      setAiInterests(prev => [...prev, interest]);
      toast.success(`Added ${interest}`);
      setCustomInterest('');
    } else {
      toast.error('Interest already added');
    }
  };

  const removeInterest = (interest) => {
    setAiInterests(prev => prev.filter(i => i !== interest));
  };

  const handleLogout = async () => {
    try {
      await axios.post(`${API}/auth/logout`, {}, { withCredentials: true });
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

  const showSearch = searchQuery.length > 0;
  const showRecommendations = activeRecSource !== null;

  const displayFaculty = showSearch
    ? filteredFaculty
    : (showRecommendations ? recommendationResults : allFaculty);

  const showCompatibilityScore = showRecommendations;

  return (
    <div className={`min-h-screen transition-colors duration-300 ${theme === 'light' ? 'bg-gradient-to-br from-teal-50 via-white to-orange-50' : 'bg-slate-950'}`}>
      <header className="border-b border-border bg-white/80 dark:bg-slate-900/80 backdrop-blur-md sticky top-0 z-50">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-8">
              <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-teal-600 to-orange-500 cursor-pointer" onClick={() => navigate('/dashboard')}>
                VIT-AP Faculty Hub
              </h1>

              <nav className="hidden md:flex items-center gap-4">
                <Button variant="ghost" onClick={() => navigate('/dashboard')} className="text-slate-500 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800" data-testid="nav-home-button">Home</Button>
                <Button variant="ghost" onClick={() => navigate('/rankings')} className="text-slate-500 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800" data-testid="nav-rankings-button">
                  <TrendingUp className="w-4 h-4 mr-2" /> Rankings
                </Button>
                <Button variant="ghost" onClick={() => navigate('/contact')} className="text-slate-500 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800" data-testid="nav-contact-button">
                  Contact
                </Button>
              </nav>
            </div>

            <div className="flex items-center gap-3">
              <Button variant="ghost" size="icon" onClick={() => toggleTheme(theme === 'light' ? 'dark' : 'light')} className="text-slate-500 dark:text-slate-300" data-testid="theme-toggle">
                {theme === 'light' ? <Moon className="w-5 h-5" /> : <Sun className="w-5 h-5 text-orange-400" />}
              </Button>
              <Button variant="ghost" size="icon" onClick={() => navigate('/chats')} className="text-slate-500 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 relative" data-testid="nav-chats-button">
                <MessageSquare className="w-5 h-5" />
                {unreadCount > 0 && (
                  <span className="absolute -top-1 -right-1 bg-red-500 text-white text-[10px] font-bold rounded-full w-4 h-4 flex items-center justify-center">
                    {unreadCount}
                  </span>
                )}
              </Button>
              <Button variant="ghost" size="icon" onClick={() => navigate('/profile')} className="text-slate-500 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800" data-testid="nav-profile-button">
                <User className="w-5 h-5" />
              </Button>
              <Button variant="ghost" size="icon" onClick={handleLogout} className="text-slate-500 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800" data-testid="logout-button">
                <LogOut className="w-5 h-5" />
              </Button>
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-6 py-8">
        <Card className="mb-8 border-l-4 border-teal-600 dark:border-l-teal-500 bg-teal-50 dark:bg-slate-900 dark:border-slate-700" data-testid="ai-interests-section">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-slate-900 dark:text-slate-100">
              <BotIcon className="w-5 h-5 text-teal-600 dark:text-teal-400" />
              AI & Research Interests (Temporary Selection)
            </CardTitle>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Select topics for this session. These will persist until you close the tab or clear them.
            </p>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-4">
              {AI_OPTIONS.map(option => (
                <label key={option.value} className="flex items-center gap-2 cursor-pointer px-4 py-2 rounded-lg border border-border hover:bg-muted/50 transition-colors bg-white dark:bg-slate-800 dark:border-slate-700 shadow-sm" data-testid={`ai-interest-${option.value}`}>
                  <Checkbox checked={aiInterests.includes(option.value)} onCheckedChange={() => handlePreferenceToggle(option.value, 'ai')} />
                  <span className="text-sm font-medium text-slate-900 dark:text-slate-100">{option.label}</span>
                </label>
              ))}
            </div>

            <div className="mt-6">
              <div className="flex gap-2">
                <Input value={customInterest} onChange={(e) => setCustomInterest(e.target.value)} placeholder="Add custom interest (e.g. Quantum Computing)..." className="dark:bg-slate-900 dark:border-slate-700 dark:text-white" onKeyDown={(e) => e.key === 'Enter' && addCustomInterest()} />
                <Button onClick={addCustomInterest} variant="secondary">Add</Button>
                <Button onClick={clearSelections} variant="ghost" className="text-red-500 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-950 border border-red-200 dark:border-red-800">Clear</Button>
              </div>
            </div>

            <div className="mt-4 mb-4">
              <div className="flex flex-wrap gap-2">
                {aiInterests.map((interest, idx) => (
                  <Badge key={idx} variant="secondary" className="px-3 py-1 text-sm bg-teal-100 text-teal-800 dark:bg-teal-900 dark:text-teal-100 flex items-center gap-2">
                    {interest}
                    <button onClick={() => removeInterest(interest)} className="hover:text-red-500 focus:outline-none"><X className="w-3 h-3" /></button>
                  </Badge>
                ))}
              </div>
            </div>

            <div className="flex flex-col sm:flex-row gap-3 mt-2 w-full">
              <Button onClick={fetchOnSpotRecommendations} className="flex-1 bg-teal-600 hover:bg-teal-700" data-testid="get-recs-home">
                Get Recommendations (On-Spot)
              </Button>
              <Button onClick={loadProfileRecommendations} variant="outline" className="flex-1 border-teal-600 text-teal-600 hover:bg-teal-50 dark:hover:bg-teal-900" data-testid="load-profile-recs">
                Load Profile Recs
              </Button>
              <Button onClick={saveToProfile} variant="outline" className="flex-1 border-blue-600 text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900">
                <Save className="w-4 h-4 mr-2" /> Save to Profile
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card className="mb-8 hover-lift bg-white dark:bg-slate-900 dark:border-slate-800" data-testid="preferences-section">
          <CardHeader>
            <CardTitle className="text-slate-900 dark:text-slate-100">What matters most to you?</CardTitle>
            <p className="text-sm text-slate-600 dark:text-slate-400">Select your teaching preferences to get personalized recommendations. Results update automatically.</p>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-4">
              {RATING_OPTIONS.map(option => (
                <label key={option.value} className="flex items-center gap-2 cursor-pointer px-4 py-2 rounded-lg border border-border hover:bg-muted/50 transition-colors bg-white dark:bg-slate-800 dark:border-slate-700" data-testid={`preference-${option.value}`}>
                  <Checkbox checked={preferences.includes(option.value)} onCheckedChange={() => handlePreferenceToggle(option.value, 'rating')} />
                  <span className="text-sm font-medium text-slate-900 dark:text-slate-100">{option.label}</span>
                </label>
              ))}
            </div>
          </CardContent>
        </Card>

        <div className="mb-8">
          <div className="relative max-w-2xl mx-auto">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
            <Input type="text" placeholder="Search faculty by name or department..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="pl-12 h-14 text-lg border-2 dark:bg-slate-900 dark:border-slate-700 dark:text-white" data-testid="search-input" />
          </div>
        </div>

        <div>
          {showSearch && (
            <h2 className="text-2xl font-bold mb-4 text-slate-900 dark:text-slate-100" data-testid="search-results-header">
              Search Results ({filteredFaculty.length})
            </h2>
          )}

          {showRecommendations && (
            <h2 className="text-2xl font-bold mb-4 text-teal-600 dark:text-teal-400" data-testid="recommended-header">
              Recommendations ({recommendationResults.length})
            </h2>
          )}

          {!showSearch && !showRecommendations && (
            <h2 className="text-2xl font-bold mb-4 text-slate-900 dark:text-slate-100" data-testid="all-faculty-header">
              All Faculty
            </h2>
          )}

          {loading ? (
            <div className="flex justify-center py-20"><div className="animate-spin rounded-full h-12 w-12 border-4 border-teal-600 border-t-transparent"></div></div>
          ) : displayFaculty.length === 0 ? (
            <Card className="p-12 dark:bg-slate-900 dark:border-slate-800">
              <p className="text-center text-slate-600 dark:text-slate-400" data-testid="no-results-message">
                {searchQuery ? 'No faculty found matching your search' : 'No recommendations found matching your criteria.'}
              </p>
            </Card>
          ) : (
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
              {displayFaculty.map(faculty => (
                <Card key={faculty.faculty_id} className="hover-lift cursor-pointer transition-all relative bg-white dark:bg-slate-900 dark:border-slate-700" onClick={() => navigate(`/faculty/${faculty.faculty_id}`)} data-testid={`faculty-card-${faculty.faculty_id}`}>
                  <CardContent className="p-6">
                    <div className="flex items-start gap-4 mb-4">
                      <Avatar className="w-16 h-16">
                        <AvatarImage src={faculty.image_url} />
                        <AvatarFallback>{faculty.name.charAt(0)}</AvatarFallback>
                      </Avatar>
                      <div className="flex-1">
                        <h3 className="font-semibold text-lg text-slate-900 dark:text-slate-100">{faculty.name}</h3>
                        <p className="text-sm text-slate-500 dark:text-slate-400 mb-1">{faculty.designation}</p>
                        <Badge variant="secondary" className="text-xs dark:bg-slate-800 dark:text-slate-300">{faculty.department}</Badge>
                      </div>
                    </div>

                    {showRecommendations && faculty.recommendation_reason && (
                      <div className="mb-3 p-3 bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800 rounded-md text-xs">
                        <p className="font-semibold text-blue-900 dark:text-blue-200 mb-1">Why you?</p>
                        <p className="text-blue-800 dark:text-blue-300 leading-relaxed">{faculty.recommendation_reason}</p>
                      </div>
                    )}

                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-slate-500 dark:text-slate-400">Overall Rating</span>
                        <div className="flex items-center gap-1">
                          <Star className="w-4 h-4 fill-yellow-400 text-yellow-400" />
                          <span className="font-semibold text-slate-900 dark:text-slate-100">{faculty.avg_ratings.overall.toFixed(1)}</span>
                          <span className="text-xs text-slate-400 dark:text-slate-500">({faculty.rating_counts.overall})</span>
                        </div>
                      </div>

                      {showCompatibilityScore && faculty.compatibility_percentage !== undefined && (
                        <div className="mt-3 pt-3 border-t border-border dark:border-slate-700">
                          <div className="flex items-center justify-between">
                            <span className="text-sm font-medium text-teal-600 dark:text-teal-400">Compatibility</span>
                            <span className="text-lg font-bold text-teal-600 dark:text-teal-400">{faculty.compatibility_percentage}%</span>
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

export default function Dashboard({ user }) {
  if (user?.is_admin) {
    return <AdminView user={user} />;
  }
  return <StudentDashboard user={user} />;
}