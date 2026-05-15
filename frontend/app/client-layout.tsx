"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { AppSidebar } from "@/components/app-sidebar";
import { SidebarInset } from "@/components/ui/sidebar";
import { api } from "@/lib/api";

interface Chat {
  id: number;
  title: string;
  timestamp?: number;
}

interface ClientLayoutProps {
  children: React.ReactNode;
  currentChatId?: number;
  onSelectChat: (chatId: number) => void;
  onNewChat: () => void;
}

export function ClientLayout({ children, currentChatId, onSelectChat, onNewChat }: ClientLayoutProps) {
  const [chats, setChats] = React.useState<Chat[]>([]);
  const [pinnedChats, setPinnedChats] = React.useState<Set<number>>(new Set());
  const router = useRouter();

  // Load conversations from backend on mount
  React.useEffect(() => {
    const loadConversations = async () => {
      try {
        const data = await api.getConversations(50, 0);
        const formattedChats = data.conversations.map((c) => ({
          id: c.id,
          title: c.title,
          timestamp: new Date(c.updated_at).getTime(),
        }));
        setChats(formattedChats);
      } catch (err) {
        console.error("Failed to load conversations:", err);
      }
    };
    loadConversations();
  }, []);

  const handleNewChat = () => {
    onNewChat();
    router.push("/");
  };

  const handleSelectChat = (chatId: number) => {
    // Call the parent's onSelectChat handler
    // This will either navigate (from /api or /roles) or update state (from home page)
    onSelectChat(chatId);
  };

  const handlePinChat = (chatId: number) => {
    setPinnedChats((prev) => {
      const newPinned = new Set(prev);
      if (newPinned.has(chatId)) {
        newPinned.delete(chatId);
      } else {
        newPinned.add(chatId);
      }
      return newPinned;
    });
  };

  const handleRenameChat = async (chatId: number, newTitle: string) => {
    try {
      await api.updateConversation(chatId, newTitle);
      setChats((prev) =>
        prev.map((chat) =>
          chat.id === chatId ? { ...chat, title: newTitle } : chat
        )
      );
    } catch (err) {
      console.error("Failed to rename chat:", err);
    }
  };

  const handleDeleteChat = async (chatId: number) => {
    try {
      await api.deleteConversation(chatId);
      setChats((prev) => prev.filter((chat) => chat.id !== chatId));
      // If currently viewing this chat, go to home
      if (currentChatId === chatId) {
        router.push("/");
        onNewChat();
      }
    } catch (err) {
      console.error("Failed to delete chat:", err);
    }
  };

  // Sort chats: pinned first, then by timestamp
  const sortedChats = React.useMemo(() => {
    return [...chats].sort((a, b) => {
      const aPinned = pinnedChats.has(a.id);
      const bPinned = pinnedChats.has(b.id);
      if (aPinned && !bPinned) return -1;
      if (!aPinned && bPinned) return 1;
      return (b.timestamp || 0) - (a.timestamp || 0);
    });
  }, [chats, pinnedChats]);

  return (
    <>
      <AppSidebar
        chats={sortedChats}
        currentChatId={currentChatId}
        onNewChat={handleNewChat}
        onSelectChat={handleSelectChat}
        onPinChat={handlePinChat}
        onRenameChat={handleRenameChat}
        onDeleteChat={handleDeleteChat}
        pinnedChatIds={pinnedChats}
      />
      <SidebarInset>{children}</SidebarInset>
    </>
  );
}
