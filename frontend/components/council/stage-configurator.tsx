"use client";

import * as React from "react";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Layers,
  Plus,
  Trash2,
  GripVertical,
  ChevronDown,
  ChevronRight,
} from "lucide-react";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";

export interface StageConfig {
  name: string;
  description: string;
  output_mode: "perspectives" | "synthesis" | "both";
  anonymize: boolean;
  reviewers: string[];
  min_reviewers: number;
  aggregation_method: "borda" | "bradley_terry" | "elo";
  pass_through: boolean;
}

interface StageConfiguratorProps {
  stages: StageConfig[];
  onChange: (stages: StageConfig[]) => void;
  availableRoles: string[];
  disabled?: boolean;
}

export function StageConfigurator({
  stages,
  onChange,
  disabled = false,
}: StageConfiguratorProps) {
  const [expandedStages, setExpandedStages] = React.useState<Set<number>>(
    new Set([0])
  );

  const addStage = () => {
    const newStage: StageConfig = {
      name: `Stage ${stages.length + 1}`,
      description: "",
      output_mode: "perspectives",
      anonymize: false,
      reviewers: [],
      min_reviewers: 2,
      aggregation_method: "borda",
      pass_through: false,
    };
    onChange([...stages, newStage]);
    setExpandedStages(new Set([...expandedStages, stages.length]));
  };

  const removeStage = (index: number) => {
    const newStages = stages.filter((_, i) => i !== index);
    onChange(newStages);
    const newExpanded = new Set(expandedStages);
    newExpanded.delete(index);
    setExpandedStages(newExpanded);
  };

  const updateStage = (index: number, updates: Partial<StageConfig>) => {
    const newStages = stages.map((stage, i) =>
      i === index ? { ...stage, ...updates } : stage
    );
    onChange(newStages);
  };

  const toggleExpanded = (index: number) => {
    const newExpanded = new Set(expandedStages);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedStages(newExpanded);
  };

  const moveStage = (index: number, direction: "up" | "down") => {
    if (
      (direction === "up" && index === 0) ||
      (direction === "down" && index === stages.length - 1)
    ) {
      return;
    }

    const newStages = [...stages];
    const targetIndex = direction === "up" ? index - 1 : index + 1;
    [newStages[index], newStages[targetIndex]] = [
      newStages[targetIndex],
      newStages[index],
    ];
    onChange(newStages);
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Layers className="h-4 w-4 text-muted-foreground" />
          <Label className="text-sm font-medium">Multi-Stage Pipeline</Label>
          {stages.length > 0 && (
            <Badge variant="secondary" className="text-xs">
              {stages.length} {stages.length === 1 ? "stage" : "stages"}
            </Badge>
          )}
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={addStage}
          disabled={disabled}
          className="h-7 text-xs"
        >
          <Plus className="h-3 w-3 mr-1" />
          Add Stage
        </Button>
      </div>

      {stages.length === 0 ? (
        <div className="text-center py-8 border-2 border-dashed rounded-lg">
          <Layers className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
          <p className="text-sm text-muted-foreground mb-2">
            No stages configured
          </p>
          <p className="text-xs text-muted-foreground mb-3">
            Add stages to create a multi-step deliberation pipeline
          </p>
          <Button
            variant="outline"
            size="sm"
            onClick={addStage}
            disabled={disabled}
          >
            <Plus className="h-3 w-3 mr-1" />
            Add First Stage
          </Button>
        </div>
      ) : (
        <div className="space-y-2">
          {stages.map((stage, index) => (
            <Collapsible
              key={index}
              open={expandedStages.has(index)}
              onOpenChange={() => toggleExpanded(index)}
            >
              <div className="border rounded-lg">
                {/* Stage Header */}
                <div className="flex items-center gap-2 p-3 bg-muted/50">
                  <div className="flex items-center gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-6 w-6 p-0 cursor-move"
                      disabled={disabled}
                    >
                      <GripVertical className="h-3 w-3" />
                    </Button>
                    <CollapsibleTrigger asChild>
                      <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
                        {expandedStages.has(index) ? (
                          <ChevronDown className="h-3 w-3" />
                        ) : (
                          <ChevronRight className="h-3 w-3" />
                        )}
                      </Button>
                    </CollapsibleTrigger>
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="text-xs">
                        {index + 1}
                      </Badge>
                      <span className="text-sm font-medium truncate">
                        {stage.name || `Stage ${index + 1}`}
                      </span>
                    </div>
                    {stage.description && (
                      <p className="text-xs text-muted-foreground truncate mt-0.5">
                        {stage.description}
                      </p>
                    )}
                  </div>

                  <div className="flex items-center gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-6 w-6 p-0"
                      onClick={() => moveStage(index, "up")}
                      disabled={disabled || index === 0}
                    >
                      ↑
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-6 w-6 p-0"
                      onClick={() => moveStage(index, "down")}
                      disabled={disabled || index === stages.length - 1}
                    >
                      ↓
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-6 w-6 p-0 text-destructive hover:text-destructive"
                      onClick={() => removeStage(index)}
                      disabled={disabled}
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </div>
                </div>

                {/* Stage Content */}
                <CollapsibleContent>
                  <div className="p-3 space-y-3 border-t">
                    {/* Name */}
                    <div className="space-y-1">
                      <Label htmlFor={`stage-${index}-name`} className="text-xs">
                        Name
                      </Label>
                      <Input
                        id={`stage-${index}-name`}
                        value={stage.name}
                        onChange={(e) =>
                          updateStage(index, { name: e.target.value })
                        }
                        placeholder="e.g., Initial Analysis"
                        disabled={disabled}
                        className="h-8"
                      />
                    </div>

                    {/* Description */}
                    <div className="space-y-1">
                      <Label
                        htmlFor={`stage-${index}-description`}
                        className="text-xs"
                      >
                        Description
                      </Label>
                      <Textarea
                        id={`stage-${index}-description`}
                        value={stage.description}
                        onChange={(e) =>
                          updateStage(index, { description: e.target.value })
                        }
                        placeholder="What happens in this stage?"
                        disabled={disabled}
                        className="h-16 text-xs"
                      />
                    </div>

                    {/* Output Mode */}
                    <div className="space-y-1">
                      <Label
                        htmlFor={`stage-${index}-output`}
                        className="text-xs"
                      >
                        Output Mode
                      </Label>
                      <Select
                        value={stage.output_mode}
                        onValueChange={(value: StageConfig["output_mode"]) =>
                          updateStage(index, { output_mode: value })
                        }
                        disabled={disabled}
                      >
                        <SelectTrigger
                          id={`stage-${index}-output`}
                          className="h-8"
                        >
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="perspectives">
                            Perspectives
                          </SelectItem>
                          <SelectItem value="synthesis">Synthesis</SelectItem>
                          <SelectItem value="both">Both</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    {/* Aggregation Method */}
                    <div className="space-y-1">
                      <Label
                        htmlFor={`stage-${index}-aggregation`}
                        className="text-xs"
                      >
                        Aggregation Method
                      </Label>
                      <Select
                        value={stage.aggregation_method}
                        onValueChange={(value: StageConfig["aggregation_method"]) =>
                          updateStage(index, { aggregation_method: value })
                        }
                        disabled={disabled}
                      >
                        <SelectTrigger
                          id={`stage-${index}-aggregation`}
                          className="h-8"
                        >
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="borda">Borda Count</SelectItem>
                          <SelectItem value="bradley_terry">
                            Bradley-Terry
                          </SelectItem>
                          <SelectItem value="elo">ELO Rating</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    {/* Anonymize */}
                    <div className="flex items-center justify-between">
                      <Label
                        htmlFor={`stage-${index}-anonymize`}
                        className="text-xs"
                      >
                        Anonymize Responses
                      </Label>
                      <Switch
                        id={`stage-${index}-anonymize`}
                        checked={stage.anonymize}
                        onCheckedChange={(checked) =>
                          updateStage(index, { anonymize: checked })
                        }
                        disabled={disabled}
                      />
                    </div>

                    {/* Pass Through */}
                    <div className="flex items-center justify-between">
                      <div className="space-y-0.5">
                        <Label
                          htmlFor={`stage-${index}-passthrough`}
                          className="text-xs"
                        >
                          Pass Through Results
                        </Label>
                        <p className="text-xs text-muted-foreground">
                          Make results available to next stage
                        </p>
                      </div>
                      <Switch
                        id={`stage-${index}-passthrough`}
                        checked={stage.pass_through}
                        onCheckedChange={(checked) =>
                          updateStage(index, { pass_through: checked })
                        }
                        disabled={disabled}
                      />
                    </div>
                  </div>
                </CollapsibleContent>
              </div>
            </Collapsible>
          ))}
        </div>
      )}

      {stages.length > 0 && (
        <p className="text-xs text-muted-foreground">
          Stages execute sequentially. Each stage can see results from previous
          stages if pass-through is enabled.
        </p>
      )}
    </div>
  );
}
