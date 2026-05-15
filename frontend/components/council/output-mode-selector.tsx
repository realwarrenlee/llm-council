"use client";

import * as React from "react";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Layers, Sparkles, LayoutGrid } from "lucide-react";

interface OutputModeSelectorProps {
  value: "perspectives" | "synthesis" | "both";
  onChange: (value: "perspectives" | "synthesis" | "both") => void;
  disabled?: boolean;
}

export function OutputModeSelector({
  value,
  onChange,
  disabled = false,
}: OutputModeSelectorProps) {
  return (
    <div className="space-y-3">
      <Label className="text-sm font-medium">Output Mode</Label>
      <RadioGroup
        value={value}
        onValueChange={(v) => onChange(v as "perspectives" | "synthesis" | "both")}
        disabled={disabled}
        className="space-y-2"
      >
        <div className="flex items-start space-x-3 space-y-0">
          <RadioGroupItem value="perspectives" id="perspectives" />
          <div className="flex-1 space-y-1">
            <Label
              htmlFor="perspectives"
              className="flex items-center gap-2 font-normal cursor-pointer"
            >
              <Layers className="h-4 w-4" />
              <span>Perspectives</span>
            </Label>
            <p className="text-xs text-muted-foreground">
              Show all role responses separately
            </p>
          </div>
        </div>

        <div className="flex items-start space-x-3 space-y-0">
          <RadioGroupItem value="synthesis" id="synthesis" />
          <div className="flex-1 space-y-1">
            <Label
              htmlFor="synthesis"
              className="flex items-center gap-2 font-normal cursor-pointer"
            >
              <Sparkles className="h-4 w-4" />
              <span>Synthesis</span>
            </Label>
            <p className="text-xs text-muted-foreground">
              Merge all perspectives into one unified answer
            </p>
          </div>
        </div>

        <div className="flex items-start space-x-3 space-y-0">
          <RadioGroupItem value="both" id="both" />
          <div className="flex-1 space-y-1">
            <Label
              htmlFor="both"
              className="flex items-center gap-2 font-normal cursor-pointer"
            >
              <LayoutGrid className="h-4 w-4" />
              <span>Both</span>
            </Label>
            <p className="text-xs text-muted-foreground">
              Show perspectives and synthesis
            </p>
          </div>
        </div>
      </RadioGroup>
    </div>
  );
}
