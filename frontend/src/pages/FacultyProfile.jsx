import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Star, ArrowLeft, MessageSquare, Send, Reply, MapPin, Mail, Phone as PhoneIcon, BookOpen, ExternalLink } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const RATING_CATEGORIES = [
  { key: 'overall', label: 'Overall' },
  { key: 'teaching', label: 'Teaching Quality' },
  { key: 'attendance', label: 'Attendance Leniency' },
  { key: 'doubt_clarification', label: 'Doubt Clarification' }
];

export default function FacultyProfile({ user }) {
  const { facultyId } = useParams();
  const navigate = useNavigate();
  const [faculty, setFaculty] = useState(null);
  const [myRating, setMyRating] = useState(null);
  const [comments, setComments] = useState([]);
  const [newComment, setNewComment] = useState('');
  const [replyingTo, setReplyingTo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [tempRatings, setTempRatings] = useState({});
  const [showAllPublications, setShowAllPublications] = useState(false);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [facultyRes, ratingRes, commentsRes] = await Promise.all([
        axios.get(`${API}/faculty/${facultyId}`),
        axios.get(`${API}/faculty/${facultyId}/ratings/me`),
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
      await axios.post(`${API}/faculty/${facultyId}/ratings`, tempRatings);
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
      await axios.post(`${API}/faculty/${facultyId}/comments`, {
        content: newComment,
        parent_comment_id: replyingTo
      });
      setNewComment('');
      setReplyingTo(null);
      toast.success('Comment posted');
      loadData();
    } catch (error) {
      console.error('Error posting comment:', error);
      toast.error('Failed to post comment');
    }
  };

  const handleStartChat = (recipientId) => {
    navigate('/chats', { state: { recipientId } });
  };

  const renderStars = (category, value) => {
    return (
      <div className="star-rating" data-testid={`rating-${category}`}>
        {[1, 2, 3, 4, 5].map(star => (
          <Star
            key={star}
            className={`w-6 h-6 ${star <= (value || 0) ? 'fill-yellow-400 text-yellow-400' : 'text-gray-300'}`}
            onClick={() => setTempRatings(prev => ({ ...prev, [category]: star }))}
          />
        ))}
      </div>
    );
  };

  const topLevelComments = comments.filter(c => !c.parent_comment_id);
  const getReplies = (commentId) => comments.filter(c => c.parent_comment_id === commentId);

  // --- STRICT FIELD DEFINITIONS ---

  // Fields that should NEVER be shown (System/Internal fields)
  const SYSTEM_FIELDS = [
    'faculty_id', 'name', 'department', 'designation',
    'scholar_profile', 'publications', 'research_interests', 'office_address',
    'email', 'phone',
    'avg_ratings', 'rating_counts', 'created_at', 'updated_at',
    'openalex_projects', 'recommendation_reason',
    'image_url', 'Image URL', 'Image', 'Profile Picture', 'Profile_Picture' // Hide all variations
  ];

  // Helper to check if a key is a system field
  const isSystemField = (key) => {
    if (SYSTEM_FIELDS.includes(key)) return true;

    const lowerKey = key.toLowerCase();
    if (lowerKey.includes('image') || lowerKey.includes('picture') || lowerKey.includes('url')) {
      return true;
    }

    return false;
  };

  // Helper to check if a key is a display field (public/excel data)
  const isDisplayField = (key) => !isSystemField(key);

  const renderDetailsList = (data) => {
    if (!data) return [];

    return Object.keys(data)
      .map(key => {
        if (isSystemField(key)) return null;

        const value = data[key];
        if (!value || value === 'Unknown' || value === 'null' || value === '') return null;

        return (
          <div key={key} className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <span className="text-sm font-semibold text-muted-foreground capitalize">
              {key.replace(/_/g, ' ')}:
            </span>
            <span className="text-sm">{value}</span>
          </div>
        );
      })
      .filter(item => item !== null);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-4 border-primary border-t-transparent"></div>
      </div>
    );
  }

  if (!faculty) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-muted-foreground">Faculty not found</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-teal-50 via-white to-orange-50">
      <div className="container mx-auto px-6 py-8 max-w-6xl">
        <Button variant="ghost" onClick={() => navigate(-1)} className="mb-6" data-testid="back-button">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back
        </Button>

        {/* Faculty Info */}
        <Card className="mb-8" data-testid="faculty-profile-card">
          <CardContent className="p-8">
            <div className="flex flex-col md:flex-row gap-8">

              {/* --- UPDATED PROFILE IMAGE SECTION --- */}
              <Avatar className="w-32 h-32 h-auto border-2 border-border">
                {/* 
                   1. src={faculty.image_url}: Uses the URL fetched from backend
                   2. onLoadingError: Hides the image if it fails, showing the Fallback (Initials)
                   3. className="object-cover": Ensures the image fills the circle without stretching
                */}
                <AvatarImage
                  src={faculty.image_url}
                  alt={faculty.name}
                  className="object-cover"
                  onLoadingError={(e) => {
                    e.currentTarget.style.display = 'none'; // Hide broken image
                  }}
                />
                <AvatarFallback className="text-3xl bg-primary/10 text-primary">
                  {faculty.name ? faculty.name.charAt(0).toUpperCase() : '?'}
                </AvatarFallback>
              </Avatar>

              <div className="flex-1 space-y-4">
                <div>
                  <h1 className="text-3xl font-bold mb-2" data-testid="faculty-name">{faculty.name}</h1>
                  <p className="text-lg text-muted-foreground mb-2">{faculty.designation}</p>
                  <Badge className="mb-4">{faculty.department}</Badge>
                </div>

                {/* Email & Phone - Prioritized Contact Info */}
                <div className="flex flex-wrap gap-4">
                  {faculty.email && (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Mail className="w-4 h-4" />
                      <span>{faculty.email}</span>
                    </div>
                  )}
                  {faculty.phone && (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <PhoneIcon className="w-4 h-4" />
                      <span>{faculty.phone}</span>
                    </div>
                  )}
                </div>

                {/* Office Address */}
                {faculty.office_address && (
                  <div className="flex items-start gap-2">
                    <MapPin className="w-4 h-4 text-muted-foreground mt-1" />
                    <div>
                      <h3 className="font-semibold mb-1">Office Address</h3>
                      <p className="text-sm text-muted-foreground">{faculty.office_address}</p>
                    </div>
                  </div>
                )}

                {/* Research Interests / Specialisation */}
                {faculty.research_interests && (
                  <div>
                    <h3 className="font-semibold mb-1">Research Interests</h3>
                    <p className="text-sm text-muted-foreground">{faculty.research_interests}</p>
                  </div>
                )}

                {faculty.scholar_profile && (
                  <a
                    href={faculty.scholar_profile}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary hover:underline text-sm inline-block"
                  >
                    View Google Scholar Profile →
                  </a>
                )}
              </div>

              <div className="space-y-3">
                {RATING_CATEGORIES.map(cat => (
                  <div key={cat.key} className="flex items-center gap-3">
                    <span className="text-sm font-medium w-32">{cat.label}:</span>
                    <Star className="w-4 h-4 fill-yellow-400 text-yellow-400" />
                    <span className="font-semibold" data-testid={`avg-${cat.key}`}>
                      {faculty.avg_ratings[cat.key].toFixed(1)}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      ({faculty.rating_counts[cat.key]})
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* --- UPDATED SECTION: OPENALEX PROJECTS WITH PAGINATION --- */}
            {faculty.openalex_projects && faculty.openalex_projects.length > 0 ? (
              <div className="mt-8 pt-6 border-t border-border">
                <h3 className="text-xl font-semibold mb-6 flex items-center gap-2">
                  <BookOpen className="w-5 h-5 text-primary" />
                  Research Projects ({faculty.openalex_projects.length})
                </h3>
                <div className="space-y-3">
                  {(showAllPublications
                    ? faculty.openalex_projects
                    : faculty.openalex_projects.slice(0, 10)
                  ).map((project, idx) => (
                    <div
                      key={idx}
                      className="group p-4 bg-white border border-border rounded-lg shadow-sm hover:shadow-md transition-all duration-300 hover:border-primary/50"
                    >
                      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                        {/* Left: Type and Title */}
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <Badge variant="secondary" className="text-[10px] uppercase tracking-wide font-bold px-2 py-0.5 bg-slate-100 text-slate-600">
                              {project.type || "Article"}
                            </Badge>
                            <span className="text-xs text-muted-foreground font-mono">
                              {project.publication_year || "Unknown"}
                            </span>
                          </div>
                          <h4 className="font-semibold text-slate-800 leading-snug">
                            {project.title || "Untitled Project"}
                          </h4>
                        </div>

                        {/* Right: View Button */}
                        <a
                          href={`https://openalex.org/work/${project.openalex_id}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-2 text-sm font-medium text-primary hover:text-primary/80 transition-colors whitespace-nowrap bg-primary/5 px-4 py-2 rounded-md hover:bg-primary/10"
                        >
                          <BookOpen className="w-4 h-4" />
                          View on OpenAlex
                        </a>
                      </div>
                    </div>
                  ))}
                </div>

                {/* View All / Show Less Button */}
                {faculty.openalex_projects.length > 10 && (
                  <div className="mt-6 flex justify-center">
                    <Button
                      variant="outline"
                      onClick={() => setShowAllPublications(!showAllPublications)}
                      className="px-6 py-2 font-medium"
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
              <div className="mt-8 pt-6 border-t border-border">
                <p className="text-sm text-muted-foreground italic">
                  No OpenAlex projects synced for this faculty member yet.
                </p>
              </div>
            )}

            {/* DYNAMIC "EVERYTHING" SECTION */}
            {renderDetailsList(faculty).length > 0 && (
              <div className="mt-8 pt-6 border-t border-border">
                <h3 className="text-xl font-semibold mb-4">Additional Details</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-y-2 gap-x-4">
                  {renderDetailsList(faculty)}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Rating Section */}
        <Card className="mb-8" data-testid="rating-section">
          <CardHeader>
            <CardTitle>Rate This Professor</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {RATING_CATEGORIES.map(cat => (
              <div key={cat.key} className="flex items-center justify-between">
                <span className="font-medium">{cat.label} {cat.key === 'overall' && '*'}</span>
                {renderStars(cat.key, tempRatings[cat.key])}
              </div>
            ))}
            <Button onClick={handleRatingSubmit} className="w-full" data-testid="submit-rating-button">
              {myRating ? 'Update Rating' : 'Submit Rating'}
            </Button>
          </CardContent>
        </Card>

        {/* Comments Section */}
        <Card data-testid="comments-section">
          <CardHeader>
            <CardTitle>Student Reviews</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Comment Input */}
            <div className="space-y-2">
              {replyingTo && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Reply className="w-4 h-4" />
                  Replying to comment
                  <Button variant="ghost" size="sm" onClick={() => setReplyingTo(null)}>
                    Cancel
                  </Button>
                </div>
              )}
              <Textarea
                placeholder="Share your experience..."
                value={newComment}
                onChange={(e) => setNewComment(e.target.value)}
                rows={3}
                data-testid="comment-input"
              />
              <Button onClick={handleCommentSubmit} className="w-full" data-testid="post-comment-button">
                <Send className="w-4 h-4 mr-2" />
                Post Comment
              </Button>
            </div>

            {/* Comments List */}
            <div className="space-y-4">
              {topLevelComments.map(comment => (
                <div key={comment.comment_id} className="space-y-3" data-testid={`comment-${comment.comment_id}`}>
                  <div className="flex gap-3">
                    <Avatar className="w-10 h-10">
                      <AvatarImage src={comment.user_picture} />
                      <AvatarFallback>{comment.user_name.charAt(0)}</AvatarFallback>
                    </Avatar>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-semibold text-sm">{comment.user_name}</span>
                        <span className="text-xs text-muted-foreground">
                          {new Date(comment.created_at).toLocaleDateString()}
                        </span>
                      </div>
                      <p className="text-sm mb-2">{comment.content}</p>
                      <div className="flex gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setReplyingTo(comment.comment_id)}
                          data-testid={`reply-button-${comment.comment_id}`}
                        >
                          <Reply className="w-3 h-3 mr-1" />
                          Reply
                        </Button>
                        {comment.user_id !== user.user_id && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleStartChat(comment.user_id)}
                            data-testid={`chat-button-${comment.comment_id}`}
                          >
                            <MessageSquare className="w-3 h-3 mr-1" />
                            Chat
                          </Button>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Replies */}
                  {getReplies(comment.comment_id).map(reply => (
                    <div key={reply.comment_id} className="comment-reply ml-12" data-testid={`reply-${reply.comment_id}`}>
                      <div className="flex gap-3">
                        <Avatar className="w-8 h-8">
                          <AvatarImage src={reply.user_picture} />
                          <AvatarFallback>{reply.user_name.charAt(0)}</AvatarFallback>
                        </Avatar>
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-semibold text-sm">{reply.user_name}</span>
                            <span className="text-xs text-muted-foreground">
                              {new Date(reply.created_at).toLocaleDateString()}
                            </span>
                          </div>
                          <p className="text-sm mb-2">{reply.content}</p>
                          {reply.user_id !== user.user_id && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleStartChat(reply.user_id)}
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