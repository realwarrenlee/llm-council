"use client";

import * as React from "react";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";

interface ChairmanSelectorProps {
  selectedChairman: string | null;
  onChairmanChange: (model: string | null) => void;
  disabled?: boolean;
}

export function ChairmanSelector({
  selectedChairman,
  onChairmanChange,
  disabled = false,
}: ChairmanSelectorProps) {
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

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium">Chairman Model</h3>
        <p className="text-xs text-muted-foreground">Synthesizes final answer</p>
      </div>
      {availableModels.length > 0 ? (
        <div className="border rounded-lg">
          <ScrollArea className="h-[200px] p-4">
            <RadioGroup
              value={selectedChairman || ""}
              onValueChange={(value) => onChairmanChange(value || null)}
              disabled={disabled}
            >
              <div className="space-y-2">
                {availableModels.map((model) => (
                  <div
                    key={model}
                    className={cn(
                      "flex items-center space-x-3 p-2 rounded-md hover:bg-muted/50 cursor-pointer transition-colors",
                      disabled && "opacity-50 cursor-not-allowed"
                    )}
                    onClick={() => !disabled && onChairmanChange(model)}
                  >
                    <RadioGroupItem
                      value={model}
                      id={`chairman-${model}`}
                      disabled={disabled}
                    />
                    <Label
                      htmlFor={`chairman-${model}`}
                      className="text-sm font-medium leading-none cursor-pointer flex-1"
                    >
                      {model}
                    </Label>
                  </div>
                ))}
              </div>
            </RadioGroup>
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
