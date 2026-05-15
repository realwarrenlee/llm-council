"use client";

import * as React from "react";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Switch } from "@/components/ui/switch";
import { SidebarMenuButton } from "@/components/ui/sidebar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Settings, Moon, Sun, Bell, Key, Cpu, Trash2 } from "lucide-react";

interface ApiKey {
  id: string;
  name: string;
  key: string;
}

export function SettingsPopover() {
  const [isDark, setIsDark] = React.useState(false);
  const [notifications, setNotifications] = React.useState(false);
  const [apiKeys, setApiKeys] = React.useState<ApiKey[]>([]);
  const [newKeyName, setNewKeyName] = React.useState("");
  const [newKeyValue, setNewKeyValue] = React.useState("");
  const [models, setModels] = React.useState<string[]>([]);
  const [newModel, setNewModel] = React.useState("");

  React.useEffect(() => {
    // Check saved theme preference (default to dark if not set)
    const savedTheme = localStorage.getItem("llm-council-theme");
    const isDarkMode = savedTheme === "dark" || savedTheme === null;
    setIsDark(isDarkMode);
    if (isDarkMode) {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }

    // Check saved notification preference (default to on if not set)
    const savedNotifications = localStorage.getItem("llm-council-notifications");
    setNotifications(savedNotifications !== "false");

    const savedKeys = localStorage.getItem("llm-council-api-keys");
    if (savedKeys) {
      setApiKeys(JSON.parse(savedKeys));
    }

    const savedModels = localStorage.getItem("llm-council-available-models");
    if (savedModels) {
      setModels(JSON.parse(savedModels));
    }
  }, []);

  const toggleTheme = (checked: boolean) => {
    setIsDark(checked);
    localStorage.setItem("llm-council-theme", checked ? "dark" : "light");
    if (checked) {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  };

  const toggleNotifications = (checked: boolean) => {
    setNotifications(checked);
    localStorage.setItem("llm-council-notifications", checked ? "true" : "false");
  };

  const saveApiKeys = (keys: ApiKey[]) => {
    setApiKeys(keys);
    localStorage.setItem("llm-council-api-keys", JSON.stringify(keys));
  };

  const saveModels = (nextModels: string[]) => {
    const cleaned = Array.from(new Set(nextModels.map((model) => model.trim()).filter(Boolean)));
    setModels(cleaned);
    localStorage.setItem("llm-council-available-models", JSON.stringify(cleaned));
    window.dispatchEvent(new Event("llm-council-models-updated"));
  };

  const addApiKey = () => {
    if (!newKeyName.trim() || !newKeyValue.trim()) return;

    saveApiKeys([
      ...apiKeys,
      {
        id: crypto.randomUUID(),
        name: newKeyName.trim(),
        key: newKeyValue.trim(),
      },
    ]);
    setNewKeyName("");
    setNewKeyValue("");
  };

  const addModel = () => {
    if (!newModel.trim()) return;
    saveModels([...models, newModel]);
    setNewModel("");
  };

  return (
    <Popover>
      <PopoverTrigger asChild>
        <SidebarMenuButton tooltip="Settings">
          <Settings />
          <span>Settings</span>
        </SidebarMenuButton>
      </PopoverTrigger>
      <PopoverContent side="right" align="end" className="w-96">
        <div className="space-y-5">
          <h4 className="font-medium leading-none">Settings</h4>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Bell className="h-4 w-4" />
              <span className="text-sm">Notifications</span>
            </div>
            <Switch checked={notifications} onCheckedChange={toggleNotifications} />
          </div>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {isDark ? (
                <Moon className="h-4 w-4" />
              ) : (
                <Sun className="h-4 w-4" />
              )}
              <span className="text-sm">Dark Mode</span>
            </div>
            <Switch checked={isDark} onCheckedChange={toggleTheme} />
          </div>

          <div className="space-y-3 border-t pt-4">
            <div className="flex items-center gap-2 text-sm font-medium">
              <Key className="h-4 w-4" />
              <span>API Key</span>
            </div>
            <div className="grid grid-cols-[1fr_1.4fr_auto] gap-2">
              <Input
                placeholder="Name"
                value={newKeyName}
                onChange={(event) => setNewKeyName(event.target.value)}
              />
              <Input
                placeholder="Key"
                type="password"
                value={newKeyValue}
                onChange={(event) => setNewKeyValue(event.target.value)}
              />
              <Button size="sm" onClick={addApiKey} disabled={!newKeyName.trim() || !newKeyValue.trim()}>
                Add
              </Button>
            </div>
            {apiKeys.length > 0 && (
              <div className="space-y-1">
                {apiKeys.map((apiKey) => (
                  <div key={apiKey.id} className="flex items-center justify-between rounded-md border px-2 py-1.5 text-sm">
                    <span className="truncate">{apiKey.name}</span>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7"
                      onClick={() => saveApiKeys(apiKeys.filter((item) => item.id !== apiKey.id))}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="space-y-3 border-t pt-4">
            <div className="flex items-center gap-2 text-sm font-medium">
              <Cpu className="h-4 w-4" />
              <span>Models</span>
            </div>
            <div className="grid grid-cols-[1fr_auto] gap-2">
              <Input
                placeholder="openai/gpt-4o-mini"
                value={newModel}
                onChange={(event) => setNewModel(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") addModel();
                }}
              />
              <Button size="sm" onClick={addModel} disabled={!newModel.trim()}>
                Add
              </Button>
            </div>
            {models.length > 0 && (
              <div className="max-h-40 space-y-1 overflow-auto">
                {models.map((model) => (
                  <div key={model} className="flex items-center justify-between rounded-md border px-2 py-1.5 text-sm">
                    <span className="truncate">{model}</span>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7"
                      onClick={() => saveModels(models.filter((item) => item !== model))}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </PopoverContent>
    </Popover>
  );
}
