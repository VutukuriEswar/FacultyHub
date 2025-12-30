import { useState, useEffect, useCallback } from 'react'; // Added useCallback
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { ArrowLeft, TrendingUp, Star, Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const DEPARTMENTS = [
  { value: 'all', label: 'All Faculty' },
  { value: 'SCOPE', label: 'Computer Science (SCOPE)' },
  { value: 'SENSE', label: 'Electronics (SENSE)' },
  { value: 'SMEC', label: 'Mechanical (SMEC)' },
  { value: 'SAS', label: 'Advanced Science (SAS)' },
  { value: 'VSB', label: 'Business (VSB)' },
  { value: 'VSL', label: 'Law (VSL)' },
  { value: 'VISH', label: 'Social Science (VISH)' }
];

const CATEGORIES = [
  { value: 'overall', label: 'Overall' },
  { value: 'teaching', label: 'Teaching Quality' },
  { value: 'attendance', label: 'Attendance Leniency' },
  { value: 'doubt_clarification', label: 'Doubt Clarification' }
];

export default function Rankings({ user }) {
  const navigate = useNavigate();
  const [department, setDepartment] = useState('all');
  const [category, setCategory] = useState('overall');
  const [method, setMethod] = useState('weighted');
  const [rankings, setRankings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  const loadRankings = useCallback(async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();

      if (department && department !== 'all') {
        params.append('department', department);
      }

      params.append('category', category);
      params.append('method', method);

      const response = await axios.get(`${API}/rankings?${params}`);
      setRankings(response.data);
    } catch (error) {
      console.error('Error loading rankings:', error);
      toast.error('Failed to load rankings');
    } finally {
      setLoading(false);
    }
  }, [department, category, method]); // Dependencies

  useEffect(() => {
    loadRankings();
  }, [loadRankings]); // Dependency: loadRankings

  const filteredRankings = rankings.filter(faculty => {
    const query = searchQuery.toLowerCase();
    return (
      faculty.name.toLowerCase().includes(query) ||
      faculty.department.toLowerCase().includes(query)
    );
  });

  return (
    <div className="min-h-screen bg-gradient-to-br from-teal-50 via-white to-orange-50">
      <div className="container mx-auto px-6 py-8 max-w-6xl">
        <Button variant="ghost" onClick={() => navigate('/dashboard')} className="mb-6" data-testid="back-button">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Dashboard
        </Button>

        <div className="flex items-center gap-3 mb-8">
          <TrendingUp className="w-8 h-8 text-primary" />
          <h1 className="text-4xl font-bold gradient-text" data-testid="rankings-header">Faculty Rankings</h1>
        </div>

        {/* Filters */}
        <Card className="mb-8" data-testid="filters-section">
          <CardContent className="p-6">
            <div className="grid md:grid-cols-3 gap-4">
              <div>
                <label className="text-sm font-medium mb-2 block">Department</label>
                <Select value={department} onValueChange={setDepartment}>
                  <SelectTrigger data-testid="department-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {DEPARTMENTS.map(dept => (
                      <SelectItem key={dept.value} value={dept.value}>
                        {dept.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <label className="text-sm font-medium mb-2 block">Category</label>
                <Select value={category} onValueChange={setCategory}>
                  <SelectTrigger data-testid="category-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {CATEGORIES.map(cat => (
                      <SelectItem key={cat.value} value={cat.value}>
                        {cat.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <label className="text-sm font-medium mb-2 block">Ranking Method</label>
                <Tabs value={method} onValueChange={setMethod} className="w-full">
                  <TabsList className="grid w-full grid-cols-2">
                    <TabsTrigger value="weighted" data-testid="weighted-tab">Weighted</TabsTrigger>
                    <TabsTrigger value="average" data-testid="average-tab">Average</TabsTrigger>
                  </TabsList>
                </Tabs>
              </div>
            </div>

            <div className="mt-6 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                type="text"
                placeholder="Search by name or department..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9"
                data-testid="rankings-search-input"
              />
            </div>

            <div className="mt-4 p-3 bg-muted/50 rounded-lg">
              <p className="text-sm text-muted-foreground">
                <strong>Weighted:</strong> Bayesian average that prevents bias from limited ratings.
                <br />
                <strong>Average:</strong> Simple mean of all ratings.
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Rankings List */}
        {loading ? (
          <div className="flex justify-center py-20">
            <div className="animate-spin rounded-full h-12 w-12 border-4 border-primary border-t-transparent"></div>
          </div>
        ) : filteredRankings.length === 0 ? (
          <Card className="p-12">
            <p className="text-center text-muted-foreground" data-testid="no-rankings-message">
              {searchQuery ? 'No rankings found matching your search' : 'No rankings available'}
            </p>
          </Card>
        ) : (
          <div className="space-y-4">
            {filteredRankings.map((faculty, index) => (
              <Card
                key={faculty.faculty_id}
                className={`hover-lift cursor-pointer transition-all ${index === 0 ? 'border-2 border-primary' : ''
                  }`}
                onClick={() => navigate(`/faculty/${faculty.faculty_id}`)}
                data-testid={`rank-${faculty.rank}`}
              >
                <CardContent className="p-6">
                  <div className="flex items-center gap-6">
                    {/* Rank */}
                    <div className="text-center">
                      <div
                        className={`text-3xl font-bold ${index === 0
                          ? 'text-yellow-500'
                          : index === 1
                            ? 'text-gray-400'
                            : index === 2
                              ? 'text-orange-600'
                              : 'text-muted-foreground'
                          }`}
                      >
                        #{faculty.rank}
                      </div>
                    </div>

                    {/* Avatar */}
                    <Avatar className="w-16 h-16">
                      <AvatarImage src={faculty.image_url} />
                      <AvatarFallback>{faculty.name.charAt(0)}</AvatarFallback>
                    </Avatar>

                    {/* Info */}
                    <div className="flex-1">
                      <h3 className="text-xl font-semibold mb-1">{faculty.name}</h3>
                      <p className="text-sm text-muted-foreground mb-2">{faculty.designation}</p>
                      <Badge variant="secondary">{faculty.department}</Badge>
                    </div>

                    {/* Score */}
                    <div className="text-right">
                      <div className="flex items-center gap-2 mb-1">
                        <Star className="w-5 h-5 fill-yellow-400 text-yellow-400" />
                        <span className="text-2xl font-bold">{faculty.score}</span>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        {faculty.rating_counts[category]} ratings
                      </p>
                    </div>
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