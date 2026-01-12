import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import axios from 'axios';
import { io } from "socket.io-client";
import { ArrowLeft, Send, MessageSquare } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { toast } from 'sonner';

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
                    No conversations yet. Start chatting by clicking chat button on any comment.
                  </p>
                ) : (
                  chats.map(chat => {
                    const otherParticipant = getOtherParticipant(chat);
                    const messagesList = chat.messages || [];
                    const lastMessage = messagesList.length > 0
                      ? messagesList[messagesList.length - 1]
                      : null;

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
                            <AvatarFallback>
                              {otherParticipant?.anonymous_chat_id?.charAt(0) || '?'}
                            </AvatarFallback>
                          </Avatar>
                          <div className="flex-1 min-w-0">
                            <p className={`font-semibold text-sm truncate ${otherParticipant?.anonymous_chat_id === 'Admin' ? 'admin-highlight' : ''}`}>
                              {otherParticipant?.anonymous_chat_id || 'Unknown'}
                            </p>
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
                    <CardTitle>
                      {selectedChat
                        ? (
                          <span className={getOtherParticipant(selectedChat)?.anonymous_chat_id === 'Admin' ? 'admin-highlight' : ''}>
                            {getOtherParticipant(selectedChat)?.anonymous_chat_id || 'Chat'}
                          </span>
                        )
                        : 'New Chat'
                      }
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-0 flex flex-col h-[500px]">
                    <div className="flex-1 overflow-y-auto p-6 space-y-4" data-testid="messages-container">
                      {(selectedChat?.messages || []).map(msg => {
                        const isMe = msg.sender_id === user.user_id;
                        const isAdminSender = msg.sender_anonymous_id === "Admin" && !isMe;
                        return (
                          <div
                            key={msg.message_id}
                            className={`flex ${isMe ? 'justify-end' : 'justify-start'} chat-message`}
                            data-testid={`message-${msg.message_id}`}
                          >
                            <div
                              className={`max-w-[70%] rounded-2xl px-4 py-2 ${isAdminSender
                                ? 'bg-gradient-to-r from-pink-500 to-red-500 text-white'
                                : isMe
                                  ? 'bg-primary text-primary-foreground'
                                  : 'bg-muted'
                                }`}
                            >
                              <p className="text-sm">{msg.content}</p>
                              <div className={`flex items-center justify-end gap-2 mt-1 ${isAdminSender ? 'text-white' : 'text-muted-foreground'}`}>
                                <p className={`text-[10px] opacity-70 font-mono`}>
                                  {isMe ? 'You' : (msg.sender_anonymous_id || 'Unknown')}
                                </p>
                                <p className={`text-xs opacity-70`}>
                                  {formatMessageDate(msg.created_at)}
                                </p>
                              </div>
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