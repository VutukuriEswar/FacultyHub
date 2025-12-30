import { useState, useEffect, useCallback } from 'react'; // Added useCallback
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Star, ArrowLeft, MessageSquare, Send, Reply } from 'lucide-react';
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
  }, [facultyId]); // Dependency: facultyId

  useEffect(() => {
    loadData();
  }, [loadData]); // Dependency: loadData

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
              <Avatar className="w-32 h-32">
                <AvatarImage src={faculty.image_url} />
                <AvatarFallback className="text-3xl">{faculty.name.charAt(0)}</AvatarFallback>
              </Avatar>

              <div className="flex-1">
                <h1 className="text-3xl font-bold mb-2" data-testid="faculty-name">{faculty.name}</h1>
                <p className="text-lg text-muted-foreground mb-2">{faculty.designation}</p>
                <Badge className="mb-4">{faculty.department}</Badge>

                {faculty.research_interests && (
                  <div className="mb-4">
                    <h3 className="font-semibold mb-1">Research Interests</h3>
                    <p className="text-sm text-muted-foreground">{faculty.research_interests}</p>
                  </div>
                )}

                {faculty.scholar_profile && (
                  <a
                    href={faculty.scholar_profile}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary hover:underline text-sm"
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