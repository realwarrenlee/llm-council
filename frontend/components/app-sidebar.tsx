"use client";

import * as React from "react";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarTrigger,
  useSidebar,
} from "@/components/ui/sidebar";
import { SquarePen, MessageSquare, UserCircle, Search, MoreHorizontal, Pin, Pencil, Trash2 } from "lucide-react";
import {
  CommandDialog,
  CommandEmpty,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Button } from "@/components/ui/button";
import { SettingsPopover } from "./settings-popover";

interface Chat {
  id: number;
  title: string;
  timestamp?: number;
}

interface AppSidebarProps {
  chats: Chat[];
  currentChatId?: number;
  onNewChat: () => void;
  onSelectChat: (chatId: number) => void;
  onPinChat?: (chatId: number) => void;
  onRenameChat?: (chatId: number, newTitle: string) => void;
  onDeleteChat?: (chatId: number) => void;
  pinnedChatIds?: Set<number>;
}

export function AppSidebar({
  chats,
  currentChatId,
  onNewChat,
  onSelectChat,
  onPinChat,
  onRenameChat,
  onDeleteChat,
  pinnedChatIds = new Set(),
}: AppSidebarProps) {
  const { state } = useSidebar();
  const isCollapsed = state === "collapsed";
  const [open, setOpen] = React.useState(false);
  const [renamingChat, setRenamingChat] = React.useState<number | null>(null);
  const [newTitle, setNewTitle] = React.useState("");

  React.useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((open) => !open);
      }
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, []);

  const handleSelectChat = (chatId: number) => {
    onSelectChat(chatId);
    setOpen(false);
  };

  const handleRename = (chatId: number, currentTitle: string) => {
    setRenamingChat(chatId);
    setNewTitle(currentTitle);
  };

  const submitRename = (chatId: number) => {
    if (newTitle.trim() && onRenameChat) {
      onRenameChat(chatId, newTitle.trim());
    }
    setRenamingChat(null);
    setNewTitle("");
  };

  return (
    <Sidebar collapsible="icon" className="border-r">
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            {isCollapsed ? (
              <div className="flex justify-center">
                <SidebarTrigger />
              </div>
            ) : (
              <div className="flex items-center justify-between px-2">
                <span className="text-sm font-semibold tracking-wide">LLM COUNCIL</span>
                <SidebarTrigger />
              </div>
            )}
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent className="p-2">
        {/* New Chat */}
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton onClick={onNewChat} tooltip="New Chat">
              <SquarePen />
              <span>New Chat</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>

        {/* Search Chats */}
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              onClick={() => setOpen(true)}
              tooltip="Search Chats"
            >
              <Search />
              <span>Search Chats</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>

        {/* Command Dialog for searching */}
        <CommandDialog open={open} onOpenChange={setOpen}>
          <CommandInput placeholder="Search chat..." />
          <CommandList>
            <CommandEmpty>No chats found.</CommandEmpty>
            {chats.map((chat) => (
              <CommandItem
                key={chat.id}
                onSelect={() => handleSelectChat(chat.id)}
              >
                <MessageSquare className="mr-2 h-4 w-4" />
                <span>{chat.title}</span>
              </CommandItem>
            ))}
          </CommandList>
        </CommandDialog>

        {/* Your Chats Section - only visible when expanded */}
        {!isCollapsed && (
          <>
            <div className="mt-4 px-2">
              <h3 className="text-xs font-medium text-muted-foreground tracking-wide">
                Your chats
              </h3>
            </div>

            <SidebarMenu className="mt-2">
              {chats.length === 0 ? (
                <div className="px-4 py-4 text-sm text-muted-foreground text-center">
                  No chats yet
                </div>
              ) : (
                chats.map((chat) => (
                  <SidebarMenuItem key={chat.id} className="group">
                    <div className="flex items-center w-full">
                      <SidebarMenuButton
                        onClick={() => onSelectChat(chat.id)}
                        tooltip={chat.title}
                        isActive={currentChatId === chat.id}
                        className="flex-1"
                      >
                        <MessageSquare />
                        {renamingChat === chat.id ? (
                          <input
                            type="text"
                            value={newTitle}
                            onChange={(e) => setNewTitle(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === "Enter") submitRename(chat.id);
                              if (e.key === "Escape") {
                                setRenamingChat(null);
                                setNewTitle("");
                              }
                            }}
                            onBlur={() => submitRename(chat.id)}
                            autoFocus
                            className="bg-transparent border-none outline-none text-sm w-full"
                            onClick={(e) => e.stopPropagation()}
                          />
                        ) : (
                          <span className="truncate flex-1">{chat.title}</span>
                        )}
                        {pinnedChatIds.has(chat.id) && (
                          <Pin className="h-3 w-3 ml-2 text-muted-foreground" />
                        )}
                      </SidebarMenuButton>

                      {/* Popover Menu */}
                      <Popover>
                        <PopoverTrigger asChild>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity"
                            onClick={(e) => e.stopPropagation()}
                          >
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </PopoverTrigger>
                        <PopoverContent align="end" side="right" className="w-48 p-2">
                          <div className="flex flex-col gap-1">
                            {onPinChat && (
                              <Button
                                variant="ghost"
                                size="sm"
                                className="justify-start gap-2"
                                onClick={() => onPinChat(chat.id)}
                              >
                                <Pin className={`h-4 w-4 ${pinnedChatIds.has(chat.id) ? 'fill-current' : ''}`} />
                                <span>{pinnedChatIds.has(chat.id) ? 'Unpin' : 'Pin'}</span>
                              </Button>
                            )}
                            {onRenameChat && (
                              <Button
                                variant="ghost"
                                size="sm"
                                className="justify-start gap-2"
                                onClick={() => handleRename(chat.id, chat.title)}
                              >
                                <Pencil className="h-4 w-4" />
                                <span>Rename</span>
                              </Button>
                            )}
                            {onDeleteChat && (
                              <Button
                                variant="ghost"
                                size="sm"
                                className="justify-start gap-2 text-destructive hover:text-destructive"
                                onClick={() => onDeleteChat(chat.id)}
                              >
                                <Trash2 className="h-4 w-4" />
                                <span>Delete</span>
                              </Button>
                            )}
                          </div>
                        </PopoverContent>
                      </Popover>
                    </div>
                  </SidebarMenuItem>
                ))
              )}
            </SidebarMenu>
          </>
        )}
      </SidebarContent>

      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <SettingsPopover />
          </SidebarMenuItem>
        </SidebarMenu>

        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton tooltip="User">
              <UserCircle />
              <span>User</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  );
}
