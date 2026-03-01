import { useState, useEffect, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import axios from 'axios';
import { io } from "socket.io-client";
import { ArrowLeft, Send, MessageSquare, ShieldCheck } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { useTheme } from '@/App';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;
const socket = io(BACKEND_URL, {
  transports: ['websocket', 'polling'],
  withCredentials: true
});

const formatMessageDate = (dateString) => {
  const date = new Date(dateString);
  const now = new Date();
  const isToday = date.toDateString() === now.toDateString();

  const yesterday = new Date(now);
  yesterday.setDate(yesterday.getDate() - 1);
  const isYesterday = date.toDateString() === yesterday.toDateString();

  const timeStr = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  if (isToday) {
    return timeStr;
  } else if (isYesterday) {
    return `Yesterday, ${timeStr}`;
  } else {
    const dateStr = date.toLocaleDateString([], { month: 'numeric', day: 'numeric', year: 'numeric' });
    return `${dateStr}, ${timeStr}`;
  }
};

export default function Chats({ user }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { theme } = useTheme();
  const [chats, setChats] = useState([]);
  const [selectedChat, setSelectedChat] = useState(null);
  const [newMessage, setNewMessage] = useState(location.state?.initialMessage || '');
  const [loading, setLoading] = useState(true);

  const loadChats = useCallback(async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/chats`);
      if (Array.isArray(response.data)) {
        setChats(response.data);
      } else {
        setChats([]);
      }
    } catch (error) {
      console.error('Error loading chats:', error);
      toast.error('Failed to load chats');
      setChats([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadChats();
  }, [loadChats]);

  useEffect(() => {
    if (location.state?.recipientId && chats.length > 0) {
      const existingChat = chats.find(c =>
        c.participants && c.participants.some((p) => p.user_id === location.state.recipientId)
      );
      if (existingChat) {
        setSelectedChat(existingChat);
        window.history.replaceState({}, document.title);
      }
    }
  }, [chats, location.state?.recipientId]);

  useEffect(() => {
    socket.on('connect', () => {
      console.log('Connected to WebSocket');
    });

    socket.on('message', (message) => {
      console.log('New message received:', message);

      setChats(prevChats => {
        const chatIndex = prevChats.findIndex(c => c.chat_id === message.chat_id);
        if (chatIndex !== -1) {
          const updatedChats = [...prevChats];
          if (updatedChats[chatIndex]) {
            updatedChats[chatIndex] = {
              ...updatedChats[chatIndex],
              messages: [...(updatedChats[chatIndex].messages || []), message]
            };
          }
          return updatedChats;
        }
        return prevChats;
      });

      setSelectedChat(prev => {
        if (prev && prev.chat_id === message.chat_id) {
          return {
            ...prev,
            messages: [...(prev.messages || []), message]
          };
        }
        return prev;
      });
    });

    return () => {
      socket.off('connect');
      socket.off('message');
    };
  }, []);

  const handleSendMessage = async () => {
    if (!newMessage.trim()) return;
    let recipientId = location.state?.recipientId;
    if (!recipientId && selectedChat) {
      const other = selectedChat.participants.find((p) => p.user_id !== user.user_id);
      recipientId = other?.user_id;
    }

    if (!recipientId) {
      toast.error('No recipient selected');
      return;
    }

    const tempMsg = {
      message_id: `temp_${Date.now()}`,
      sender_id: user.user_id,
      sender_anonymous_id: "You",
      content: newMessage,
      created_at: new Date()
    };

    setSelectedChat(prev => {
      if (!prev) {
        return {
          chat_id: 'temp_new',
          participants: [],
          messages: [tempMsg]
        };
      }
      return {
        ...prev,
        messages: [...(prev.messages || []), tempMsg]
      };
    });

    const contentToSend = newMessage;
    setNewMessage('');

    try {
      await axios.post(`${API}/chats/messages`, {
        recipient_id: recipientId,
        content: contentToSend
      });

      if (!selectedChat) {
        loadChats();
      }
    } catch (error) {
      console.error('Error sending message:', error);
      toast.error('Failed to send message');
      setSelectedChat(prev => {
        if (!prev) return null;
        return {
          ...prev,
          messages: prev.messages.filter(m => m.message_id !== tempMsg.message_id)
        };
      });
      setNewMessage(contentToSend);
    }
  };

  const getOtherParticipant = (chat) => {
    if (!chat || !chat.participants) return null;
    return chat.participants.find((p) => p.user_id !== user.user_id);
  };

  return (
    <div className={`min-h-screen transition-colors duration-300 ${theme === 'light' ? 'bg-gradient-to-br from-teal-50 via-white to-orange-50' : 'bg-slate-950'}`}>
      <div className="container mx-auto px-6 py-8 max-w-6xl">
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
          <MessageSquare className="w-8 h-8 text-primary dark:text-teal-400" />
          <h1 className="text-4xl font-bold gradient-text text-slate-900 dark:text-slate-100" data-testid="chats-header">Messages</h1>
        </div>

        {loading ? (
          <div className="flex justify-center py-20">
            <div className="animate-spin rounded-full h-12 w-12 border-4 border-primary border-t-transparent"></div>
          </div>
        ) : (
          <div className="grid md:grid-cols-3 gap-6 h-[600px]">
            <Card className="md:col-span-1 bg-white dark:bg-slate-900 dark:border-slate-800" data-testid="chat-list">
              <CardHeader>
                <CardTitle className="text-slate-900 dark:text-slate-100">Conversations</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 overflow-y-auto h-[500px]">
                {chats.length === 0 ? (
                  <p className="text-sm text-slate-500 dark:text-slate-400 text-center py-8" data-testid="no-chats-message">
                    No conversations yet. Start chatting by clicking chat button on any comment.
                  </p>
                ) : (
                  chats.map(chat => {
                    const otherParticipant = getOtherParticipant(chat);
                    const messagesList = chat.messages || [];
                    const lastMessage = messagesList.length > 0
                      ? messagesList[messagesList.length - 1]
                      : null;

                    const unreadCount = chat.unread_count || 0;

                    return (
                      <div
                        key={chat.chat_id}
                        className={`p-3 rounded-lg cursor-pointer transition-colors relative ${selectedChat?.chat_id === chat.chat_id
                          ? 'bg-primary/10 border border-primary'
                          : 'hover:bg-muted/50'
                          }`}
                        onClick={() => setSelectedChat(chat)}
                        data-testid={`chat-${chat.chat_id}`}
                      >
                        <div className="flex items-center gap-3">
                          <Avatar className="w-10 h-10">
                            <AvatarFallback className="bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                              {otherParticipant?.anonymous_chat_id?.charAt(0) || '?'}
                            </AvatarFallback>
                          </Avatar>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-1">
                              <p className={`font-semibold text-sm truncate ${otherParticipant?.is_admin ? 'text-amber-600' : 'text-slate-900 dark:text-slate-100'}`}>
                                {otherParticipant?.anonymous_chat_id || 'Unknown'}
                              </p>
                              {otherParticipant?.is_admin && (
                                <ShieldCheck className="w-3 h-3 text-amber-600" />
                              )}
                            </div>
                            <p className="text-xs text-slate-500 dark:text-slate-400 truncate">
                              {lastMessage?.content || 'No messages'}
                            </p>
                          </div>
                          {unreadCount > 0 && (
                            <span className="bg-red-500 text-white text-[10px] font-bold rounded-full w-5 h-5 flex items-center justify-center">
                              {unreadCount}
                            </span>
                          )}
                        </div>
                      </div>
                    );
                  })
                )}
              </CardContent>
            </Card>

            <Card className="md:col-span-2 bg-white dark:bg-slate-900 dark:border-slate-800" data-testid="chat-window">
              {selectedChat || location.state?.recipientId ? (
                <>
                  <CardHeader className="border-b border-border dark:border-slate-700">
                    <CardTitle className="text-slate-900 dark:text-slate-100 flex items-center gap-2">
                      <div>
                        {selectedChat
                          ? (
                            <div className="flex items-center gap-1">
                              {getOtherParticipant(selectedChat)?.anonymous_chat_id || 'Chat'}
                              {getOtherParticipant(selectedChat)?.is_admin && (
                                <ShieldCheck className="w-4 h-4 text-amber-600" title="Verified Administrator" />
                              )}
                            </div>
                          )
                          : 'New Chat'
                        }
                      </div>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-0 flex flex-col h-[500px]">
                    <div className="flex-1 overflow-y-auto p-6 space-y-4" data-testid="messages-container">
                      {(selectedChat?.messages || []).map(msg => {
                        const isMe = msg.sender_id === user.user_id;
                        const isAdminSender = msg.is_admin_sender && !isMe;

                        return (
                          <div
                            key={msg.message_id}
                            className={`flex ${isMe ? 'justify-end' : 'justify-start'} chat-message`}
                            data-testid={`message-${msg.message_id}`}
                          >
                            <div
                              className={`max-w-[70%] rounded-2xl px-4 py-2 ${isAdminSender
                                ? 'bg-gradient-to-r from-amber-600 to-orange-600 text-white border border-amber-500'
                                : isMe
                                  ? 'bg-primary text-primary-foreground dark:bg-indigo-600 dark:text-white'
                                  : 'bg-muted dark:bg-slate-700 dark:text-slate-200'
                                }`}
                            >
                              <p className="text-sm dark:text-slate-100">{msg.content}</p>
                              <div className={`flex items-center justify-end gap-2 mt-1 ${isAdminSender ? 'text-white/80' : 'text-muted-foreground dark:text-slate-400'}`}>
                                <div className="flex items-center gap-1">
                                  <p className={`text-[10px] opacity-90 font-semibold ${isAdminSender ? 'text-amber-600' : ''}`}>
                                    {isMe ? 'You' : (msg.sender_anonymous_id || 'Unknown')}
                                  </p>
                                  {isAdminSender && (
                                    <ShieldCheck className="w-3 h-3 text-white" title="Verified Administrator" />
                                  )}
                                </div>
                              </div>
                              <p className={`text-xs opacity-70`}>
                                {formatMessageDate(msg.created_at)}
                              </p>
                            </div>
                          </div>
                        );
                      })}
                    </div>

                    <div className="border-t border-border dark:border-slate-700 p-4">
                      <div className="flex gap-2">
                        <Input
                          placeholder="Type a message..."
                          value={newMessage}
                          onChange={(e) => setNewMessage(e.target.value)}
                          onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                          data-testid="message-input"
                          className="bg-slate-50 dark:bg-slate-950 dark:border-slate-700 dark:text-white dark:placeholder:text-slate-500"
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
                  <p className="text-muted-foreground dark:text-slate-400" data-testid="select-chat-message">Select a conversation to start chatting</p>
                </CardContent>
              )}
            </Card>
          </div>
        )}
      </div>
    </div >
  );
}