"use client";

import * as React from "react";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { EyeOff } from "lucide-react";

interface AnonymizationToggleProps {
  value: boolean;
  onChange: (value: boolean) => void;
  disabled?: boolean;
}

export function AnonymizationToggle({
  value,
  onChange,
  disabled = false,
}: AnonymizationToggleProps) {
  return (
    <div className="flex items-center justify-between space-x-2">
      <div className="flex items-center gap-2 flex-1">
        <EyeOff className="h-4 w-4 text-muted-foreground" />
        <div className="space-y-0.5">
          <Label htmlFor="anonymize" className="text-sm font-medium cursor-pointer">
            Anonymous Review
          </Label>
          <p className="text-xs text-muted-foreground">
            Hide role identities during deliberation for unbiased feedback
          </p>
        </div>
      </div>
      <Switch
        id="anonymize"
        checked={value}
        onCheckedChange={onChange}
        disabled={disabled}
      />
    </div>
  );
}
