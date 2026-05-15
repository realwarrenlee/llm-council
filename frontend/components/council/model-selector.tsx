"use client";

import * as React from "react";
import { Checkbox } from "@/components/ui/checkbox";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";

interface ModelSelectorProps {
  selectedModels: string[];
  onModelsChange: (models: string[]) => void;
  disabled?: boolean;
}

export function ModelSelector({
  selectedModels,
  onModelsChange,
  disabled = false,
}: ModelSelectorProps) {
  const [availableModels, setAvailableModels] = React.useState<string[]>([]);

  React.useEffect(() => {
    const loadModels = () => {
      const saved = localStorage.getItem("llm-council-available-models");
      setAvailableModels(saved ? JSON.parse(saved) : []);
    };

    loadModels();
    window.addEventListener("llm-council-models-updated", loadModels);
    return () => window.removeEventListener("llm-council-models-updated", loadModels);
  }, []);

  const handleToggle = (model: string) => {
    if (selectedModels.includes(model)) {
      onModelsChange(selectedModels.filter((m) => m !== model));
    } else {
      onModelsChange([...selectedModels, model]);
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium">Council Members</h3>
        <p className="text-xs text-muted-foreground">Provide perspectives</p>
      </div>
      {availableModels.length > 0 ? (
        <div className="border rounded-lg">
          <ScrollArea className="h-[200px] p-4">
            <div className="space-y-2">
              {availableModels.map((model) => (
                <div
                  key={model}
                  className={cn(
                    "flex items-center space-x-3 p-2 rounded-md hover:bg-muted/50 cursor-pointer transition-colors",
                    disabled && "opacity-50 cursor-not-allowed"
                  )}
                  onClick={() => !disabled && handleToggle(model)}
                >
                  <Checkbox
                    id={`model-${model}`}
                    checked={selectedModels.includes(model)}
                    onCheckedChange={() => handleToggle(model)}
                    disabled={disabled}
                  />
                  <label
                    htmlFor={`model-${model}`}
                    className="text-sm font-medium leading-none cursor-pointer flex-1"
                  >
                    {model}
                  </label>
                </div>
              ))}
            </div>
          </ScrollArea>
        </div>
      ) : (
        <div className="border rounded-lg p-6 text-center">
          <p className="text-sm text-muted-foreground">
            No models available. Add model IDs in Settings.
          </p>
        </div>
      )}
    </div>
  );
}
