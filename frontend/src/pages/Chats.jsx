import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import axios from 'axios';
import { ArrowLeft, Send, MessageSquare } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function Chats({ user }) {
  const navigate = useNavigate();
  const location = useLocation();
  const [chats, setChats] = useState([]);
  const [selectedChat, setSelectedChat] = useState(null);
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [users, setUsers] = useState({});

  const loadChats = async () => {
    try {
      if (chats.length === 0) setLoading(true);

      const response = await axios.get(`${API}/chats`);
      setChats(response.data);

      if (selectedChat) {
        const updatedChat = response.data.find(c => c.chat_id === selectedChat.chat_id);
        if (updatedChat) {
          setSelectedChat(updatedChat);
        }
      }

      const userIds = new Set();
      response.data.forEach(chat => {
        chat.participants.forEach(p => userIds.add(p));
      });
    } catch (error) {
      console.error('Error loading chats:', error);
      if (chats.length === 0) toast.error('Failed to load chats');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/exhaustive-deps
    loadChats();

    if (location.state?.recipientId) {
      const existingChat = chats.find(c => c.participants.includes(location.state.recipientId));
      if (existingChat) {
        setSelectedChat(existingChat);
      }
    }
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      // eslint-disable-next-line react-hooks/exhaustive-deps
      loadChats();
    }, 3000);

    return () => clearInterval(interval);
  }, [selectedChat]);

  const handleSendMessage = async () => {
    if (!newMessage.trim()) return;

    const recipientId = location.state?.recipientId ||
      selectedChat?.participants.find(p => p !== user.user_id);

    if (!recipientId) {
      toast.error('No recipient selected');
      return;
    }

    try {
      await axios.post(`${API}/chats/messages`, {
        recipient_id: recipientId,
        content: newMessage
      });
      setNewMessage('');
      loadChats();
    } catch (error) {
      console.error('Error sending message:', error);
      toast.error('Failed to send message');
    }
  };

  const getOtherParticipantId = (chat) => {
    return chat.participants.find(p => p !== user.user_id);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-teal-50 via-white to-orange-50">
      <div className="container mx-auto px-6 py-8 max-w-6xl">
        <Button variant="ghost" onClick={() => navigate('/dashboard')} className="mb-6" data-testid="back-button">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Dashboard
        </Button>

        <div className="flex items-center gap-3 mb-8">
          <MessageSquare className="w-8 h-8 text-primary" />
          <h1 className="text-4xl font-bold gradient-text" data-testid="chats-header">Messages</h1>
        </div>

        {loading ? (
          <div className="flex justify-center py-20">
            <div className="animate-spin rounded-full h-12 w-12 border-4 border-primary border-t-transparent"></div>
          </div>
        ) : (
          <div className="grid md:grid-cols-3 gap-6 h-[600px]">
            <Card className="md:col-span-1" data-testid="chat-list">
              <CardHeader>
                <CardTitle>Conversations</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 overflow-y-auto h-[500px]">
                {chats.length === 0 ? (
                  <p className="text-sm text-muted-foreground text-center py-8" data-testid="no-chats-message">
                    No conversations yet. Start chatting by clicking the chat button on any comment.
                  </p>
                ) : (
                  chats.map(chat => {
                    const otherUserId = getOtherParticipantId(chat);
                    const lastMessage = chat.messages[chat.messages.length - 1];

                    return (
                      <div
                        key={chat.chat_id}
                        className={`p-3 rounded-lg cursor-pointer transition-colors ${selectedChat?.chat_id === chat.chat_id
                          ? 'bg-primary/10 border border-primary'
                          : 'hover:bg-muted/50'
                          }`}
                        onClick={() => setSelectedChat(chat)}
                        data-testid={`chat-${chat.chat_id}`}
                      >
                        <div className="flex items-center gap-3">
                          <Avatar>
                            <AvatarFallback>{otherUserId.charAt(0)}</AvatarFallback>
                          </Avatar>
                          <div className="flex-1 min-w-0">
                            <p className="font-semibold text-sm truncate">User {otherUserId.slice(-6)}</p>
                            <p className="text-xs text-muted-foreground truncate">
                              {lastMessage?.content || 'No messages'}
                            </p>
                          </div>
                        </div>
                      </div>
                    );
                  })
                )}
              </CardContent>
            </Card>

            <Card className="md:col-span-2" data-testid="chat-window">
              {selectedChat || location.state?.recipientId ? (
                <>
                  <CardHeader className="border-b">
                    <CardTitle>Chat</CardTitle>
                  </CardHeader>
                  <CardContent className="p-0 flex flex-col h-[500px]">
                    <div className="flex-1 overflow-y-auto p-6 space-y-4" data-testid="messages-container">
                      {selectedChat?.messages.map(msg => {
                        const isMe = msg.sender_id === user.user_id;
                        return (
                          <div
                            key={msg.message_id}
                            className={`flex ${isMe ? 'justify-end' : 'justify-start'} chat-message`}
                            data-testid={`message-${msg.message_id}`}
                          >
                            <div
                              className={`max-w-[70%] rounded-2xl px-4 py-2 ${isMe
                                ? 'bg-primary text-primary-foreground'
                                : 'bg-muted'
                                }`}
                            >
                              <p className="text-sm">{msg.content}</p>
                              <p className="text-xs opacity-70 mt-1">
                                {new Date(msg.created_at).toLocaleTimeString()}
                              </p>
                            </div>
                          </div>
                        );
                      })}
                    </div>

                    <div className="border-t p-4">
                      <div className="flex gap-2">
                        <Input
                          placeholder="Type a message..."
                          value={newMessage}
                          onChange={(e) => setNewMessage(e.target.value)}
                          onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                          data-testid="message-input"
                        />
                        <Button onClick={handleSendMessage} data-testid="send-button">
                          <Send className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </>
              ) : (
                <CardContent className="flex items-center justify-center h-[500px]">
                  <p className="text-muted-foreground" data-testid="select-chat-message">Select a conversation to start chatting</p>
                </CardContent>
              )}
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}