"use client";

import * as React from "react";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { BarChart3, TrendingUp, Target } from "lucide-react";

interface AggregationSelectorProps {
  value: "borda" | "bradley_terry" | "elo";
  onChange: (value: "borda" | "bradley_terry" | "elo") => void;
  disabled?: boolean;
}

export function AggregationSelector({
  value,
  onChange,
  disabled = false,
}: AggregationSelectorProps) {
  return (
    <div className="space-y-3">
      <Label className="text-sm font-medium">Aggregation Method</Label>
      <RadioGroup
        value={value}
        onValueChange={(v) => onChange(v as "borda" | "bradley_terry" | "elo")}
        disabled={disabled}
        className="space-y-2"
      >
        <div className="flex items-start space-x-3 space-y-0">
          <RadioGroupItem value="borda" id="borda" />
          <div className="flex-1 space-y-1">
            <Label
              htmlFor="borda"
              className="flex items-center gap-2 font-normal cursor-pointer"
            >
              <BarChart3 className="h-4 w-4" />
              <span>Borda Count</span>
            </Label>
            <p className="text-xs text-muted-foreground">
              Rank-based voting system, balanced and intuitive
            </p>
          </div>
        </div>

        <div className="flex items-start space-x-3 space-y-0">
          <RadioGroupItem value="bradley_terry" id="bradley_terry" />
          <div className="flex-1 space-y-1">
            <Label
              htmlFor="bradley_terry"
              className="flex items-center gap-2 font-normal cursor-pointer"
            >
              <TrendingUp className="h-4 w-4" />
              <span>Bradley-Terry</span>
            </Label>
            <p className="text-xs text-muted-foreground">
              Pairwise comparison model, statistically robust
            </p>
          </div>
        </div>

        <div className="flex items-start space-x-3 space-y-0">
          <RadioGroupItem value="elo" id="elo" />
          <div className="flex-1 space-y-1">
            <Label
              htmlFor="elo"
              className="flex items-center gap-2 font-normal cursor-pointer"
            >
              <Target className="h-4 w-4" />
              <span>ELO Rating</span>
            </Label>
            <p className="text-xs text-muted-foreground">
              Chess-style rating system, dynamic and competitive
            </p>
          </div>
        </div>
      </RadioGroup>
    </div>
  );
}
