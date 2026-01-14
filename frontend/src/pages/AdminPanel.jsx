import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { ArrowLeft, Plus, Edit, Trash, Save, X, Database } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { toast } from 'sonner';
import { useTheme } from '@/App';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

axios.defaults.withCredentials = true;

const DEPARTMENTS = [
  'SCOPE',
  'SENSE',
  'SMEC',
  'SAS',
  'VSB',
  'VSL',
  'VISH'
];

export default function AdminPanel({ user }) {
  const navigate = useNavigate();
  const { theme } = useTheme();
  const [faculty, setFaculty] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingFaculty, setEditingFaculty] = useState(null);
  const [isSyncing, setIsSyncing] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    department: 'SCOPE',
    designation: '',
    image_url: '',
    scholar_profile: '',
    publications: '',
    research_interests: ''
  });

  useEffect(() => {
    if (!user?.is_admin) {
      toast.error('Admin access required');
      navigate('/dashboard');
      return;
    }
    loadFaculty();
  }, [user, navigate]);

  const loadFaculty = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/faculty`);
      setFaculty(response.data);
    } catch (error) {
      console.error('Error loading faculty:', error);
      toast.error('Failed to load faculty');
    } finally {
      setLoading(false);
    }
  };

  const handleSyncOpenAlex = async () => {
    const confirm = window.confirm("This will update all faculty profiles with OpenAlex project data. It may take a moment. Continue?");
    if (!confirm) return;

    setIsSyncing(true);
    try {
      const response = await axios.post(`${API}/admin/sync-openalex`);
      toast.success(`Sync Completed! Updated: ${response.data.updated_count}, Failed: ${response.data.failed_count}`);
      loadFaculty();
    } catch (error) {
      console.error('Sync error:', error);
      toast.error('Failed to sync OpenAlex data. Check console.');
    } finally {
      setIsSyncing(false);
    }
  };

  const handleOpenDialog = (facultyData = null) => {
    if (facultyData) {
      setEditingFaculty(facultyData);
      setFormData({
        name: facultyData.name,
        department: facultyData.department,
        designation: facultyData.designation,
        image_url: facultyData.image_url || '',
        scholar_profile: facultyData.scholar_profile || '',
        publications: Array.isArray(facultyData.publications) ? facultyData.publications.join('\n') : '',
        research_interests: facultyData.research_interests || ''
      });
    } else {
      setEditingFaculty(null);
      setFormData({
        name: '',
        department: 'SCOPE',
        designation: '',
        image_url: '',
        scholar_profile: '',
        publications: '',
        research_interests: ''
      });
    }
    setIsDialogOpen(true);
  };

  const handleSubmit = async () => {
    if (!formData.name || !formData.designation) {
      toast.error('Name and designation are required');
      return;
    }

    try {
      const submitData = {
        ...formData,
        publications: formData.publications
          .split('\n')
          .filter(p => p.trim())
          .map(p => p.trim())
      };

      if (editingFaculty) {
        await axios.patch(`${API}/faculty/${editingFaculty.faculty_id}`, submitData);
        toast.success('Faculty updated successfully');
      } else {
        await axios.post(`${API}/faculty`, submitData);
        toast.success('Faculty added successfully');
      }

      setIsDialogOpen(false);
      loadFaculty();
    } catch (error) {
      console.error('Error saving faculty:', error);
      toast.error('Failed to save faculty');
    }
  };

  const handleDelete = async (facultyId) => {
    if (!window.confirm('Are you sure you want to delete this faculty member?')) {
      return;
    }

    try {
      await axios.delete(`${API}/faculty/${facultyId}`);
      toast.success('Faculty deleted successfully');
      loadFaculty();
    } catch (error) {
      console.error('Error deleting faculty:', error);
      toast.error('Failed to delete faculty');
    }
  };

  if (!user?.is_admin) {
    return null;
  }

  return (
    <div className={`min-h-screen transition-colors duration-300 ${theme === 'light' ? 'bg-gradient-to-br from-teal-50 via-white to-orange-50' : 'bg-slate-950'}`}>
      <div className="container mx-auto px-6 py-8 max-w-7xl">
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
          <h1 className="text-4xl font-bold gradient-text text-slate-900 dark:text-slate-100" data-testid="admin-header">Faculty</h1>
          <div className="flex gap-2">
            <Button
              onClick={handleSyncOpenAlex}
              disabled={isSyncing}
              variant="outline"
              className="border-blue-500 text-blue-600 hover:bg-blue-50 dark:text-blue-400 dark:border-blue-600 dark:hover:bg-blue-900"
            >
              <Database className="w-4 h-4 mr-2" />
              {isSyncing ? 'Syncing...' : 'Sync OpenAlex Data'}
            </Button>

            <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
              <DialogTrigger asChild>
                <Button onClick={() => handleOpenDialog()} data-testid="add-faculty-button">
                  <Plus className="w-4 h-4 mr-2" />
                  Add Faculty
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto dark:bg-slate-900 dark:border-slate-800">
                <DialogHeader>
                  <DialogTitle className="dark:text-slate-100">{editingFaculty ? 'Edit Faculty' : 'Add New Faculty'}</DialogTitle>
                </DialogHeader>
                <div className="space-y-4 py-4">
                  <div>
                    <Label htmlFor="name" className="dark:text-slate-300">Full Name *</Label>
                    <Input
                      id="name"
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      data-testid="faculty-name-input"
                      className="dark:bg-slate-950 dark:border-slate-700 dark:text-white"
                    />
                  </div>

                  <div>
                    <Label htmlFor="department" className="dark:text-slate-300">Department *</Label>
                    <Select value={formData.department} onValueChange={(val) => setFormData({ ...formData, department: val })}>
                      <SelectTrigger data-testid="faculty-department-select" className="dark:bg-slate-950 dark:border-slate-700 dark:text-white">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="dark:bg-slate-950 dark:border-slate-700">
                        {DEPARTMENTS.map(dept => (
                          <SelectItem key={dept} value={dept} className="dark:text-slate-100">{dept}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <Label htmlFor="designation" className="dark:text-slate-300">Designation *</Label>
                    <Input
                      id="designation"
                      value={formData.designation}
                      onChange={(e) => setFormData({ ...formData, designation: e.target.value })}
                      placeholder="e.g., Associate Professor"
                      data-testid="faculty-designation-input"
                      className="dark:bg-slate-950 dark:border-slate-700 dark:text-white"
                    />
                  </div>

                  <div>
                    <Label htmlFor="image_url" className="dark:text-slate-300">Profile Image URL</Label>
                    <Input
                      id="image_url"
                      value={formData.image_url}
                      onChange={(e) => setFormData({ ...formData, image_url: e.target.value })}
                      placeholder="https://..."
                      data-testid="faculty-image-input"
                      className="dark:bg-slate-950 dark:border-slate-700 dark:text-white"
                    />
                  </div>

                  <div>
                    <Label htmlFor="scholar_profile" className="dark:text-slate-300">Google Scholar Profile URL</Label>
                    <Input
                      id="scholar_profile"
                      value={formData.scholar_profile}
                      onChange={(e) => setFormData({ ...formData, scholar_profile: e.target.value })}
                      placeholder="https://scholar.google.com/..."
                      data-testid="faculty-scholar-input"
                      className="dark:bg-slate-950 dark:border-slate-700 dark:text-white"
                    />
                  </div>

                  <div>
                    <Label htmlFor="publications" className="dark:text-slate-300">Publications (one per line)</Label>
                    <Textarea
                      id="publications"
                      value={formData.publications}
                      onChange={(e) => setFormData({ ...formData, publications: e.target.value })}
                      rows={4}
                      placeholder="Publication title 1&#10;Publication title 2&#10;..."
                      data-testid="faculty-publications-input"
                      className="dark:bg-slate-950 dark:border-slate-700 dark:text-white"
                    />
                  </div>

                  <div>
                    <Label htmlFor="research_interests" className="dark:text-slate-300">Research Interests</Label>
                    <Textarea
                      id="research_interests"
                      value={formData.research_interests}
                      onChange={(e) => setFormData({ ...formData, research_interests: e.target.value })}
                      rows={3}
                      data-testid="faculty-research-input"
                      className="dark:bg-slate-950 dark:border-slate-700 dark:text-white"
                    />
                  </div>

                  <div className="flex gap-2 pt-4">
                    <Button onClick={handleSubmit} className="flex-1" data-testid="save-faculty-button">
                      <Save className="w-4 h-4 mr-2" />
                      {editingFaculty ? 'Update' : 'Create'}
                    </Button>
                    <Button variant="outline" onClick={() => setIsDialogOpen(false)} data-testid="cancel-faculty-button">
                      <X className="w-4 h-4 mr-2" />
                      Cancel
                    </Button>
                  </div>
                </div>
              </DialogContent>
            </Dialog>
          </div>
        </div>

        {loading ? (
          <div className="flex justify-center py-20">
            <div className="animate-spin rounded-full h-12 w-12 border-4 border-teal-600 border-t-transparent"></div>
          </div>
        ) : faculty.length === 0 ? (
          <Card className="p-12 dark:bg-slate-900 dark:border-slate-800">
            <p className="text-center text-slate-600 dark:text-slate-400" data-testid="no-faculty-message">
              No faculty members yet. Click "Add Faculty" to get started.
            </p>
          </Card>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {faculty.map(fac => (
              <Card key={fac.faculty_id} className="hover-lift bg-white dark:bg-slate-900 dark:border-slate-700" data-testid={`admin-faculty-card-${fac.faculty_id}`}>
                <CardContent className="p-6">
                  <div className="flex items-start gap-4 mb-4">
                    <Avatar className="w-16 h-16">
                      <AvatarImage src={fac.image_url} />
                      <AvatarFallback className="bg-slate-100 dark:bg-slate-800">{fac.name.charAt(0)}</AvatarFallback>
                    </Avatar>
                    <div className="flex-1">
                      <h3 className="font-semibold text-lg text-slate-900 dark:text-slate-100">{fac.name}</h3>
                      <p className="text-sm text-slate-500 dark:text-slate-400 mb-1">{fac.designation}</p>
                      <Badge variant="secondary" className="text-xs dark:bg-slate-800 dark:text-slate-300">{fac.department}</Badge>
                    </div>
                  </div>

                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleOpenDialog(fac)}
                      className="flex-1 dark:text-slate-300 dark:border-slate-700 dark:hover:bg-slate-800"
                      data-testid={`edit-faculty-${fac.faculty_id}`}
                    >
                      <Edit className="w-4 h-4 mr-1" />
                      Edit
                    </Button>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => handleDelete(fac.faculty_id)}
                      className="flex-1"
                      data-testid={`delete-faculty-${fac.faculty_id}`}
                    >
                      <Trash className="w-4 h-4 mr-1" />
                      Delete
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