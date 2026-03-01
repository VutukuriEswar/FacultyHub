import { useNavigate } from 'react-router-dom';
import { Mail, Github, ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useTheme } from '@/App';

export default function Contact({ user }) {
    const navigate = useNavigate();
    const { theme } = useTheme();

    if (user?.is_admin) {
        navigate('/dashboard');
        return null;
    }

    const handleEmailContact = () => {
        const email = "vitapfacultyhub@gmail.com";
        const subject = encodeURIComponent("Inquiry from VIT-AP Faculty Hub");
        const body = encodeURIComponent("Hello,\n\nI am writing to you regarding the Faculty Hub platform.\n\n");
        const link = document.createElement("a");
        link.href = `mailto:${email}?subject=${subject}&body=${body}`;
        link.click();
    };

    const handleReportBug = () => {
        window.open("https://github.com/VutukuriEswar/FacultyHub/issues", "_blank");
    };

    return (
        <div className={`min-h-screen transition-colors duration-300 ${theme === 'light' ? 'bg-gradient-to-br from-teal-50 via-white to-orange-50' : 'bg-slate-950'}`}>
            <div className="container mx-auto px-6 py-8 max-w-5xl">
                <Button
                    variant="ghost"
                    onClick={() => navigate('/dashboard')}
                    className="mb-6 text-slate-500 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
                >
                    <ArrowLeft className="w-4 h-4 mr-2" />
                    Back to Dashboard
                </Button>

                <div className="mb-8 text-center">
                    <h1 className="text-4xl font-bold gradient-text text-slate-900 dark:text-slate-100 mb-2">Contact & Support</h1>
                    <p className="text-slate-600 dark:text-slate-400">How can we help you today?</p>
                </div>

                <div className="grid md:grid-cols-2 gap-6">
                    <Card className="hover-lift bg-white dark:bg-slate-900 dark:border-slate-800 border-t-4 border-t-teal-500">
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2 text-slate-900 dark:text-slate-100">
                                <div className="p-2 bg-teal-100 dark:bg-teal-900/30 rounded-lg">
                                    <Mail className="w-6 h-6 text-teal-600 dark:text-teal-400" />
                                </div>
                                General Support
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
                                Do you have questions, suggestions, or need help with the platform? Write to us directly.
                            </p>
                            <Button
                                onClick={handleEmailContact}
                                className="w-full bg-teal-600 hover:bg-teal-700 text-white"
                            >
                                <Mail className="w-4 h-4 mr-2" />
                                Write us an Email
                            </Button>
                        </CardContent>
                    </Card>

                    <Card className="hover-lift bg-white dark:bg-slate-900 dark:border-slate-800 border-t-4 border-t-slate-700">
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2 text-slate-900 dark:text-slate-100">
                                <div className="p-2 bg-slate-100 dark:bg-slate-800 rounded-lg">
                                    <Github className="w-6 h-6 text-slate-900 dark:text-slate-100" />
                                </div>
                                Report a Bug
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
                                Found a technical glitch, incorrect data, or an unexpected error? Report it on our GitHub Issues page.
                            </p>
                            <Button
                                onClick={handleReportBug}
                                variant="outline"
                                className="w-full border-slate-700 text-slate-700 hover:bg-slate-50 dark:text-slate-300 dark:border-slate-600 dark:hover:bg-slate-800"
                            >
                                <Github className="w-4 h-4 mr-2" />
                                Report on GitHub
                            </Button>
                        </CardContent>
                    </Card>
                </div>
            </div>
        </div>
    );
}