import { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import {
  Star, ArrowLeft, MessageSquare, Send, Reply,
  MapPin, Mail, Phone as PhoneIcon, BookOpen,
  ExternalLink, Trash, Building2, Layers, TrendingUp, ShieldCheck
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import { toast } from 'sonner';
import { useTheme } from '@/App';
import {
  PieChart, Pie, Cell, AreaChart, Area,
  XAxis, YAxis, CartesianGrid, BarChart, Bar,
  Tooltip, ResponsiveContainer,
} from 'recharts';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const RATING_CATEGORIES = [
  { key: 'overall', label: 'Overall' },
  { key: 'teaching', label: 'Teaching Quality' },
  { key: 'attendance', label: 'Attendance Leniency' },
  { key: 'doubt_clarification', label: 'Doubt Clarification' }
];

const COLORS_TYPE = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    const value = payload[0].value;
    const name = payload[0].name || payload[0].payload.name;
    return (
      <div className="bg-white/90 dark:bg-slate-800/90 backdrop-blur-sm p-3 border border-gray-200 dark:border-slate-700 rounded-lg shadow-lg text-sm z-50 text-slate-900 dark:text-slate-100">
        <p className="font-semibold">{label}</p>
        <p className="text-gray-600 dark:text-slate-300">
          <span className="inline-block w-2 h-2 rounded-full mr-2" style={{ backgroundColor: payload[0].payload.fill || '#8b5cf6' }}></span>
          {name}: <span className="font-bold">{value}</span>
        </p>
      </div>
    );
  }
  return null;
};

const RadialProgressCard = ({ label, value, total, color }) => {
  const percentage = total > 0 ? Math.round((value / total) * 100) : 0;
  const radius = 18;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (percentage / 100) * circumference;

  return (
    <div
      className="group flex items-center gap-3 p-2 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors duration-300 cursor-default border border-transparent hover:border-slate-100 dark:hover:border-slate-700"
    >
      <div className="relative w-10 h-10 flex-shrink-0">
        <svg className="w-full h-full transform -rotate-90" viewBox="0 0 50 50">
          <circle
            className="text-slate-100 dark:text-slate-800"
            strokeWidth="6"
            stroke="currentColor"
            fill="transparent"
            r={radius}
            cx="25"
            cy="25"
          />
          <circle
            className="transition-all duration-1000 ease-out group-hover:opacity-80"
            strokeWidth="6"
            strokeLinecap="round"
            stroke={color}
            fill="transparent"
            r={radius}
            cx="25"
            cy="25"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center text-[9px] font-bold text-slate-600 dark:text-slate-300">
          {percentage}%
        </div>
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-[10px] font-medium text-slate-400 dark:text-slate-500 uppercase tracking-wider truncate">{label}</p>
        <p className="text-sm font-bold text-slate-700 dark:text-slate-200">{value} Papers</p>
      </div>
    </div>
  );
};

export default function FacultyProfile({ user }) {
  const { facultyId } = useParams();
  const navigate = useNavigate();
  const { theme } = useTheme();

  const [faculty, setFaculty] = useState(null);
  const [myRating, setMyRating] = useState(null);
  const [comments, setComments] = useState([]);
  const [newComment, setNewComment] = useState('');
  const [replyingTo, setReplyingTo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [tempRatings, setTempRatings] = useState({});
  const [showAllPublications, setShowAllPublications] = useState(false);

  const chartData = useMemo(() => {
    if (!faculty?.openalex_projects) return { typeData: [], citationsData: [], yearData: [], totalWorks: 0 };

    const typeCounts = {};
    const yearCounts = {};
    const citationsByYear = {};
    let totalWorks = 0;
    let totalCitations = 0;

    faculty.openalex_projects.forEach(p => {
      let type = p.type || 'Unknown';
      type = type.charAt(0).toUpperCase() + type.slice(1).toLowerCase();
      typeCounts[type] = (typeCounts[type] || 0) + 1;
      totalWorks++;
      const year = p.publication_year || 'Unknown';
      yearCounts[year] = (yearCounts[year] || 0) + 1;
      const citations = p.cited_by_count || 0;
      if (year !== 'Unknown') {
        citationsByYear[year] = (citationsByYear[year] || 0) + citations;
      }
      totalCitations += citations;
    });

    const typeData = Object.keys(typeCounts)
      .map((key, index) => ({
        name: key,
        value: typeCounts[key],
        fill: COLORS_TYPE[index % COLORS_TYPE.length]
      }))
      .sort((a, b) => b.value - a.value);

    const yearData = Object.keys(yearCounts)
      .sort()
      .map(year => ({
        year: year,
        count: yearCounts[year]
      }));

    const citationsData = Object.keys(citationsByYear)
      .sort()
      .map(year => ({
        year: year,
        citations: citationsByYear[year]
      }));

    return { typeData, citationsData, yearData, totalWorks, totalCitations };
  }, [faculty]);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [facultyRes, ratingRes, commentsRes] = await Promise.all([
        axios.get(`${API}/faculty/${facultyId}`),
        axios.get(`${API}/faculty/${facultyId}/ratings/me`, { withCredentials: true }),
        axios.get(`${API}/faculty/${facultyId}/comments`)
      ]);

      setFaculty(facultyRes.data);
      setMyRating(ratingRes.data);
      setComments(commentsRes.data);

      if (ratingRes.data) {
        setTempRatings({
          overall: ratingRes.data.overall,
          teaching: ratingRes.data.teaching,
          attendance: ratingRes.data.attendance,
          doubt_clarification: ratingRes.data.doubt_clarification
        });
      }
    } catch (error) {
      console.error('Error loading faculty:', error);
      toast.error('Failed to load faculty details');
    } finally {
      setLoading(false);
    }
  }, [facultyId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleRatingSubmit = async () => {
    if (!tempRatings.overall) {
      toast.error('Overall rating is required');
      return;
    }

    try {
      await axios.post(
        `${API}/faculty/${facultyId}/ratings`,
        tempRatings,
        { withCredentials: true }
      );
      toast.success('Rating submitted successfully');
      loadData();
    } catch (error) {
      console.error('Error submitting rating:', error);
      toast.error('Failed to submit rating');
    }
  };

  const handleCommentSubmit = async () => {
    if (!newComment.trim()) return;

    try {
      const response = await axios.post(
        `${API}/faculty/${facultyId}/comments`,
        {
          content: newComment,
          parent_comment_id: replyingTo
        },
        { withCredentials: true }
      );
      setNewComment('');
      setReplyingTo(null);

      if (response.data.profanity_detected) {
        toast.error('⚠️ Warning: Your comment contains inappropriate language. An administrator has been notified.');
      } else {
        toast.success('Comment posted');
      }
      loadData();
    } catch (error) {
      console.error('Error posting comment:', error);
      toast.error('Failed to post comment');
    }
  };

  const handleDeleteComment = async (commentId) => {
    if (!window.confirm('Are you sure you want to delete this comment?')) {
      return;
    }

    try {
      await axios.delete(`${API}/comments/${commentId}`);
      toast.success('Comment deleted');
      loadData();
    } catch (error) {
      console.error('Error deleting comment:', error);
      toast.error('Failed to delete comment');
    }
  };

  const handleStartChat = (recipientId) => {
    navigate('/chats', { state: { recipientId, initialMessage: '' } });
  };

  const renderStars = (category, value) => {
    return (
      <div className="star-rating" data-testid={`rating-${category}`}>
        {[1, 2, 3, 4, 5].map(star => (
          <Star
            key={star}
            className={`w-6 h-6 cursor-pointer ${star <= (value || 0) ? 'fill-yellow-400 text-yellow-400' : 'text-slate-300 dark:text-slate-700'}`}
            onClick={() => setTempRatings(prev => ({ ...prev, [category]: star }))}
          />
        ))}
      </div>
    );
  };

  const topLevelComments = comments.filter(c => !c.parent_comment_id);
  const getReplies = (commentId) => comments.filter(c => c.parent_comment_id === commentId);

  const SYSTEM_FIELDS = [
    'faculty_id', 'name', 'department', 'designation',
    'scholar_profile', 'publications', 'research_interests', 'office_address',
    'email', 'phone',
    'avg_ratings', 'rating_counts', 'created_at', 'updated_at',
    'openalex_projects', 'recommendation_reason',
    'image_url', 'Image URL', 'Image', 'Profile Picture', 'Profile_Picture'
  ];

  const isSystemField = (key) => {
    if (SYSTEM_FIELDS.includes(key)) return true;
    const lowerKey = key.toLowerCase();
    if (lowerKey.includes('image') || lowerKey.includes('picture') || lowerKey.includes('url')) return true;
    return false;
  };

  const renderDetailsList = (data) => {
    if (!data) return [];

    return Object.keys(data)
      .map(key => {
        if (isSystemField(key)) return null;

        const value = data[key];
        if (!value || value === 'Unknown' || value === 'null' || value === '') return null;

        return (
          <div key={key} className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <span className="text-sm font-semibold text-slate-500 dark:text-slate-400 capitalize">
              {key.replace(/_/g, ' ')}:
            </span>
            <span className="text-sm text-slate-900 dark:text-slate-100">{value}</span>
          </div>
        );
      })
      .filter(item => item !== null);
  };

  const displayResearchInterests = () => {
    if (!faculty.research_interests) return null;
    if (Array.isArray(faculty.research_interests)) {
      return faculty.research_interests.join(', ');
    }
    return faculty.research_interests;
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950 dark:bg-slate-950">
        <div className="animate-spin rounded-full h-12 w-12 border-4 border-primary border-t-transparent"></div>
      </div>
    );
  }

  if (!faculty) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950 dark:bg-slate-950">
        <p className="text-slate-500 dark:text-slate-400">Faculty not found</p>
      </div>
    );
  }

  return (
    <div className={`min-h-screen transition-colors duration-300 ${theme === 'light' ? 'bg-gradient-to-br from-teal-50 via-white to-orange-50' : 'bg-slate-950'}`}>
      <div className="container mx-auto px-6 py-8 max-w-6xl">
        <Button variant="ghost" onClick={() => navigate(-1)} className="mb-6 dark:text-slate-300 dark:hover:bg-slate-800" data-testid="back-button">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back
        </Button>

        <Card className="mb-8 animate-in fade-in slide-in-from-bottom-4 duration-500 bg-white dark:bg-slate-900 dark:border-slate-800" data-testid="faculty-profile-card">
          <CardContent className="p-8">
            <div className="flex flex-col md:flex-row gap-8">
              <Avatar className="w-32 h-32 border-2 border-border shadow-lg">
                <AvatarImage
                  src={faculty.image_url}
                  alt={faculty.name}
                  className="object-cover"
                  onLoadingError={(e) => {
                    e.currentTarget.style.display = 'none';
                  }}
                />
                <AvatarFallback className="text-3xl bg-slate-100 dark:bg-slate-800 text-primary">
                  {faculty.name ? faculty.name.charAt(0).toUpperCase() : '?'}
                </AvatarFallback>
              </Avatar>

              <div className="flex-1 space-y-4">
                <div>
                  <h1 className="text-3xl font-bold mb-2 text-slate-900 dark:text-slate-100" data-testid="faculty-name">{faculty.name}</h1>
                  <p className="text-lg text-slate-600 dark:text-slate-400 mb-2">{faculty.designation}</p>
                  <Badge className="mb-4 shadow-sm bg-teal-100 text-teal-800 dark:bg-teal-900 dark:text-teal-100">{faculty.department}</Badge>
                </div>

                <div className="flex flex-wrap gap-4">
                  {faculty.email && (
                    <div className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400 bg-slate-50 dark:bg-slate-800 px-3 py-1.5 rounded-full border border-slate-100 dark:border-slate-700">
                      <Mail className="w-4 h-4" />
                      <span>{faculty.email}</span>
                    </div>
                  )}
                  {faculty.phone && (
                    <div className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400 bg-slate-50 dark:bg-slate-800 px-3 py-1.5 rounded-full border border-slate-100 dark:border-slate-700">
                      <PhoneIcon className="w-4 h-4" />
                      <span>{faculty.phone}</span>
                    </div>
                  )}
                </div>

                {faculty.office_address && (
                  <div className="flex items-start gap-2 bg-blue-50/50 dark:bg-blue-900/20 p-3 rounded-lg border border-blue-100 dark:border-blue-900">
                    <MapPin className="w-4 h-4 text-blue-600 dark:text-blue-400 mt-1" />
                    <div>
                      <h3 className="font-semibold mb-1 text-blue-900 dark:text-blue-200">Office Address</h3>
                      <p className="text-sm text-blue-700 dark:text-blue-300">{faculty.office_address}</p>
                    </div>
                  </div>
                )}

                {faculty.research_interests && (
                  <div>
                    <h3 className="font-semibold mb-1 text-slate-800 dark:text-slate-200">Research Interests</h3>
                    <p className="text-sm text-slate-600 dark:text-slate-400">{displayResearchInterests()}</p>
                  </div>
                )}
              </div>

              <div className="space-y-3 bg-slate-50 dark:bg-slate-800 p-4 rounded-xl border border-slate-100 dark:border-slate-700">
                {RATING_CATEGORIES.map(cat => (
                  <div key={cat.key} className="flex items-center justify-between">
                    <span className="text-sm font-medium w-32 text-slate-600 dark:text-slate-400">{cat.label}:</span>
                    <div className="flex items-center gap-2">
                      <Star className="w-4 h-4 fill-yellow-400 text-yellow-400" />
                      <span className="font-bold text-slate-900 dark:text-slate-100" data-testid={`avg-${cat.key}`}>
                        {faculty.avg_ratings[cat.key].toFixed(1)}
                      </span>
                      <span className="text-xs text-slate-400 dark:text-slate-500">
                        ({faculty.rating_counts[cat.key]})
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {faculty.openalex_projects && faculty.openalex_projects.length > 0 ? (
              <div className="mt-8 pt-6 border-t border-border dark:border-slate-800">
                <h3 className="text-2xl font-bold mb-6 flex items-center gap-2 text-slate-900 dark:text-slate-100">
                  <Layers className="w-6 h-6 text-teal-600 dark:text-teal-400" />
                  Research Analytics
                </h3>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                  <Card className="shadow-md hover:shadow-xl transition-shadow duration-300 bg-white dark:bg-slate-900 dark:border-slate-800">
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium text-slate-600 dark:text-slate-400 flex items-center gap-1">
                        Impact Over Time
                        <TrendingUp className="w-3 h-3 text-purple-500" />
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="text-2xl font-bold text-center mb-2 text-purple-700 dark:text-purple-400">
                        {chartData.totalCitations}
                      </div>
                      <div className="text-xs text-center mb-4 text-slate-500 dark:text-slate-400">Total Citations</div>
                      <ResponsiveContainer width="100%" height={140}>
                        <AreaChart data={chartData.citationsData}>
                          <defs>
                            <linearGradient id="colorCitations" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.8} />
                              <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
                            </linearGradient>
                          </defs>
                          <XAxis dataKey="year" style={{ fontSize: '10px' }} hide />
                          <Tooltip content={<CustomTooltip />} />
                          <Area
                            type="monotone"
                            dataKey="citations"
                            stroke="#8b5cf6"
                            fillOpacity={1}
                            fill="url(#colorCitations)"
                          />
                        </AreaChart>
                      </ResponsiveContainer>
                    </CardContent>
                  </Card>

                  <Card className="shadow-md hover:shadow-xl transition-shadow duration-300 bg-white dark:bg-slate-900 dark:border-slate-800">
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium text-slate-600 dark:text-slate-400">Publication Types</CardTitle>
                    </CardHeader>
                    <CardContent className="h-[240px] overflow-y-auto pt-2">
                      <div className="space-y-2 pr-2">
                        {chartData.typeData.slice(0, 10).map((item, index) => (
                          <RadialProgressCard
                            key={index}
                            label={item.name}
                            value={item.value}
                            total={chartData.totalWorks}
                            color={item.fill}
                          />
                        ))}
                        {chartData.typeData.length === 0 && (
                          <div className="text-xs text-slate-500 dark:text-slate-400 text-center py-4">No data available</div>
                        )}
                      </div>
                    </CardContent>
                  </Card>

                  <Card className="shadow-md hover:shadow-xl transition-shadow duration-300 bg-white dark:bg-slate-900 dark:border-slate-800">
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium text-slate-600 dark:text-slate-400">Productivity</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <ResponsiveContainer width="100%" height={200}>
                        <BarChart data={chartData.yearData}>
                          <XAxis dataKey="year" style={{ fontSize: '10px' }} axisLine={false} tickLine={false} />
                          <YAxis allowDecimals={false} style={{ fontSize: '10px' }} axisLine={false} tickLine={false} />
                          <Tooltip content={<CustomTooltip />} cursor={{ fill: 'transparent' }} />
                          <Bar dataKey="count" fill="#14b8a6" radius={[4, 4, 0, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                      <div className="text-center text-xs text-slate-500 dark:text-slate-400 mt-2">
                        Publications per Year
                      </div>
                    </CardContent>
                  </Card>

                </div>

                <h3 className="text-xl font-semibold mb-4 flex items-center gap-2 text-slate-900 dark:text-slate-100">
                  All Publications ({faculty.openalex_projects.length})
                </h3>
                <div className="space-y-3">
                  {(showAllPublications
                    ? faculty.openalex_projects
                    : faculty.openalex_projects.slice(0, 10)
                  ).map((project, idx) => (
                    <div
                      key={idx}
                      className={`group p-4 border rounded-xl shadow-sm hover:shadow-lg hover:-translate-y-0.5 transition-all duration-300 ${project.is_vitap
                        ? 'bg-teal-50/50 border-teal-100 hover:border-teal-400 dark:bg-teal-900/20 dark:border-teal-900 dark:hover:border-teal-500'
                        : 'bg-white border-gray-200 hover:border-gray-400 dark:bg-slate-800 dark:border-slate-700 dark:hover:border-slate-600'
                        }`}
                    >
                      <div className="flex flex-col md:flex-row md:items-start justify-between gap-3">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1 flex-wrap">
                            <Badge
                              variant="secondary"
                              className={`text-[10px] uppercase tracking-wide font-bold px-2 py-0.5 ${project.is_vitap ? 'bg-teal-100 text-teal-800 dark:bg-teal-900 dark:text-teal-200' : 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300'
                                }`}
                            >
                              {project.type ? (project.type.charAt(0).toUpperCase() + project.type.slice(1).toLowerCase()) : "Article"}
                            </Badge>

                            <span className="text-xs text-slate-500 dark:text-slate-400 font-mono bg-white dark:bg-slate-800 px-1 rounded border border-gray-100 dark:border-slate-700">
                              {project.publication_year || "Unknown"}
                            </span>
                            {project.cited_by_count !== undefined && (
                              <span className="text-xs text-purple-600 dark:text-purple-400 font-bold bg-purple-50 dark:bg-purple-900/30 px-1 rounded border border-purple-100 dark:border-purple-800 flex items-center gap-1">
                                <TrendingUp className="w-2 h-2" />
                                {project.cited_by_count} Citations
                              </span>
                            )}
                          </div>
                          <h4 className="font-semibold text-slate-800 dark:text-slate-200 leading-snug group-hover:text-teal-600 dark:group-hover:text-teal-400 transition-colors">
                            {project.title || "Untitled Project"}
                          </h4>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                {faculty.openalex_projects.length > 10 && (
                  <div className="mt-6 flex justify-center">
                    <Button
                      variant="outline"
                      onClick={() => setShowAllPublications(!showAllPublications)}
                      className="px-6 py-2 font-medium shadow-sm hover:shadow-md transition-all dark:border-slate-700 dark:text-slate-300"
                      data-testid="toggle-publications-button"
                    >
                      {showAllPublications
                        ? `Show Less`
                        : `View All (${faculty.openalex_projects.length} publications)`
                      }
                    </Button>
                  </div>
                )}
              </div>
            ) : (
              <div className="mt-8 pt-6 border-t border-border dark:border-slate-800">
                <p className="text-sm text-slate-500 dark:text-slate-400 italic">
                  No OpenAlex projects synced for this faculty member yet.
                </p>
              </div>
            )}

            {renderDetailsList(faculty).length > 0 && (
              <div className="mt-8 pt-6 border-t border-border dark:border-slate-800">
                <h3 className="text-xl font-semibold mb-4 text-slate-900 dark:text-slate-100">Additional Details</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-y-2 gap-x-4">
                  {renderDetailsList(faculty)}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="mb-8 animate-in fade-in slide-in-from-bottom-4 duration-700 delay-100 bg-white dark:bg-slate-900 dark:border-slate-800" data-testid="rating-section">
          <CardHeader>
            <CardTitle className="text-slate-900 dark:text-slate-100">Rate This Professor</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {!user && (
              <div className="p-3 bg-orange-50 dark:bg-orange-900/30 border border-orange-200 dark:border-orange-900 rounded-md flex items-center gap-2 text-sm text-orange-800 dark:text-orange-200">
                <span className="font-bold">Login Required</span>
                <span>Please login to rate and comment.</span>
              </div>
            )}
            {RATING_CATEGORIES.map(cat => (
              <div key={cat.key} className="flex items-center justify-between">
                <span className="font-medium text-slate-900 dark:text-slate-200">{cat.label} {cat.key === 'overall' && '*'}</span>
                {renderStars(cat.key, tempRatings[cat.key])}
              </div>
            ))}
            <Button
              onClick={handleRatingSubmit}
              className="w-full shadow-md hover:shadow-lg transition-all bg-teal-600 hover:bg-teal-700"
              data-testid="submit-rating-button"
              disabled={!user}
            >
              {myRating ? 'Update Rating' : 'Submit Rating'}
            </Button>
          </CardContent>
        </Card>

        <Card className="animate-in fade-in slide-in-from-bottom-4 duration-700 delay-200 bg-white dark:bg-slate-900 dark:border-slate-800" data-testid="comments-section">
          <CardHeader>
            <CardTitle className="text-slate-900 dark:text-slate-100">Student Reviews</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-2">
              {replyingTo && (
                <div className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
                  <Reply className="w-4 h-4" />
                  Replying to comment
                  <Button variant="ghost" size="sm" onClick={() => setReplyingTo(null)}>
                    Cancel
                  </Button>
                </div>
              )}
              <Textarea
                placeholder={myRating ? "Share your experience..." : "You must rate this professor to comment."}
                value={newComment}
                onChange={(e) => setNewComment(e.target.value)}
                rows={3}
                disabled={!myRating && user}
                readOnly={!user}
                data-testid="comment-input"
                className="focus:ring-2 ring-primary/20 dark:bg-slate-950 dark:border-slate-700 dark:text-white dark:placeholder:text-slate-600"
              />
              <Button
                onClick={handleCommentSubmit}
                className="w-full bg-teal-600 hover:bg-teal-700"
                data-testid="post-comment-button"
                disabled={!myRating && user}
              >
                <Send className="w-4 h-4 mr-2" />
                Post Comment
              </Button>
            </div>

            <div className="space-y-4">
              {topLevelComments.map(comment => (
                <div key={comment.comment_id} className="space-y-3" data-testid={`comment-${comment.comment_id}`}>
                  <div className="flex gap-3">
                    <Avatar className="w-10 h-10">
                      <AvatarImage src={comment.user_picture} />
                      <AvatarFallback className="bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                        {comment.anonymous_handle
                          ? comment.anonymous_handle.charAt(comment.anonymous_handle.length - 1)
                          : (comment.user_name ? comment.user_name.charAt(0) : '?')
                        }
                      </AvatarFallback>
                    </Avatar>
                    <div className="flex-1">
                      <div className="flex items-center justify-between mb-1">
                        <div className="flex items-center gap-2">
                          <span className={`font-semibold text-sm text-slate-900 dark:text-slate-200 flex items-center gap-1 ${comment.is_admin_commenter ? 'text-amber-600' : ''}`}>
                            {comment.anonymous_handle || comment.user_name}
                            {comment.is_admin_commenter && <ShieldCheck className="w-3 h-3 text-amber-600" title="Verified Administrator" />}
                          </span>
                          <span className="text-xs text-slate-500 dark:text-slate-400">
                            {new Date(comment.created_at).toLocaleDateString()}
                          </span>
                        </div>
                        {(comment.user_id === user?.user_id || user?.is_admin) && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDeleteComment(comment.comment_id)}
                            className="text-red-500 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-900/20"
                            data-testid={`delete-comment-${comment.comment_id}`}
                          >
                            <Trash className="w-3 h-3" />
                          </Button>
                        )}
                      </div>
                      <p className="text-sm mb-2 text-slate-700 dark:text-slate-300">{comment.content}</p>
                      <div className="flex gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setReplyingTo(comment.comment_id)}
                          data-testid={`reply-button-${comment.comment_id}`}
                          disabled={!user || !myRating}
                          className="text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-white"
                        >
                          <Reply className="w-3 h-3 mr-1" />
                          Reply
                        </Button>
                        {comment.user_id !== user?.user_id && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleStartChat(comment.user_id)}
                            data-testid={`chat-button-${comment.comment_id}`}
                            className="text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-white"
                          >
                            <MessageSquare className="w-3 h-3 mr-1" />
                            Chat
                          </Button>
                        )}
                      </div>
                    </div>
                  </div>

                  {getReplies(comment.comment_id).map(reply => (
                    <div key={reply.comment_id} className="comment-reply ml-12" data-testid={`reply-${reply.comment_id}`}>
                      <div className="flex gap-3">
                        <Avatar className="w-8 h-8">
                          <AvatarImage src={reply.user_picture} />
                          <AvatarFallback className="bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                            {reply.anonymous_handle
                              ? reply.anonymous_handle.charAt(reply.anonymous_handle.length - 1)
                              : (reply.user_name ? reply.user_name.charAt(0) : '?')
                            }
                          </AvatarFallback>
                        </Avatar>
                        <div className="flex-1">
                          <div className="flex items-center justify-between mb-1">
                            <div className="flex items-center gap-2">
                              <span className={`font-semibold text-sm text-slate-900 dark:text-slate-200 flex items-center gap-1 ${reply.is_admin_commenter ? 'text-amber-600' : ''}`}>
                                {reply.anonymous_handle || reply.user_name}
                                {reply.is_admin_commenter && <ShieldCheck className="w-3 h-3 text-amber-600" title="Verified Administrator" />}
                              </span>
                              <span className="text-xs text-slate-500 dark:text-slate-400">
                                {new Date(reply.created_at).toLocaleDateString()}
                              </span>
                            </div>
                            {(reply.user_id === user?.user_id || user?.is_admin) && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleDeleteComment(reply.comment_id)}
                                className="text-red-500 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-900/20"
                                data-testid={`delete-reply-${reply.comment_id}`}
                              >
                                <Trash className="w-3 h-3" />
                              </Button>
                            )}
                          </div>
                          <p className="text-sm mb-2 text-slate-700 dark:text-slate-300">{reply.content}</p>
                          {reply.user_id !== user?.user_id && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleStartChat(reply.user_id)}
                              className="text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-white"
                            >
                              <MessageSquare className="w-3 h-3 mr-1" />
                              Chat
                            </Button>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}