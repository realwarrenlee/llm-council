"use client";

import * as React from "react";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { 
  User, 
  RotateCcw,
  Save,
  AlertCircle
} from "lucide-react";
import { cn } from "@/lib/utils";

export interface CustomRole {
  name: string;
  prompt: string;
  model: string;
  description: string;
  weight: number;
  config: {
    temperature: number;
    max_tokens: number | null;
  };
}

interface CustomRoleEditorProps {
  roles: CustomRole[];
  onChange: (roles: CustomRole[]) => void;
  presetRoles?: Record<string, { prompt: string; description: string }>;
  disabled?: boolean;
}

export function CustomRoleEditor({
  roles,
  onChange,
  presetRoles = {},
  disabled = false,
}: CustomRoleEditorProps) {
  const [hasUnsavedChanges, setHasUnsavedChanges] = React.useState<Set<string>>(
    new Set()
  );

  const updateRole = (name: string, updates: Partial<CustomRole>) => {
    const newRoles = roles.map((role) =>
      role.name === name ? { ...role, ...updates } : role
    );
    onChange(newRoles);
    
    // Mark as having unsaved changes
    setHasUnsavedChanges(prev => new Set(prev).add(name));
  };

  const resetRole = (name: string) => {
    const preset = presetRoles[name];
    if (!preset) return;

    updateRole(name, {
      prompt: preset.prompt,
      description: preset.description,
    });
    
    // Remove from unsaved changes
    setHasUnsavedChanges(prev => {
      const next = new Set(prev);
      next.delete(name);
      return next;
    });
  };

  const saveChanges = (name: string) => {
    // In a real app, this would save to localStorage or backend
    setHasUnsavedChanges(prev => {
      const next = new Set(prev);
      next.delete(name);
      return next;
    });
  };

  const isModified = (role: CustomRole): boolean => {
    const preset = presetRoles[role.name];
    if (!preset) return false;
    
    return role.prompt !== preset.prompt || role.description !== preset.description;
  };

  if (roles.length === 0) {
    return (
      <div className="text-center py-8 border-2 border-dashed rounded-lg">
        <User className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
        <p className="text-sm text-muted-foreground">
          No roles available
        </p>
        <p className="text-xs text-muted-foreground mt-1">
          Select models to customize roles
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <User className="h-4 w-4 text-muted-foreground" />
        <Label className="text-sm font-medium">Custom Role Editor</Label>
        {hasUnsavedChanges.size > 0 && (
          <Badge variant="secondary" className="text-xs">
            {hasUnsavedChanges.size} unsaved
          </Badge>
        )}
      </div>

      <p className="text-xs text-muted-foreground">
        Customize role prompts, descriptions, and parameters. Changes apply to the current deliberation.
      </p>

      {/* Role List */}
      <Accordion type="single" collapsible className="space-y-0">
        {roles.map((role) => {
          const modified = isModified(role);
          const unsaved = hasUnsavedChanges.has(role.name);
          
          return (
            <AccordionItem
              key={role.name}
              value={role.name}
              className="border-b"
            >
              <AccordionTrigger className="py-4 hover:no-underline">
                <div className="flex items-center gap-2 flex-1 text-left">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">{role.name}</span>
                      {modified && (
                        <Badge variant="outline" className="text-xs">
                          Modified
                        </Badge>
                      )}
                      {unsaved && (
                        <Badge variant="secondary" className="text-xs">
                          <AlertCircle className="h-3 w-3 mr-1" />
                          Unsaved
                        </Badge>
                      )}
                    </div>
                    {role.description && (
                      <p className="text-xs text-muted-foreground truncate mt-0.5">
                        {role.description}
                      </p>
                    )}
                  </div>

                  <Badge variant="secondary" className="text-xs">
                    Weight: {role.weight}
                  </Badge>
                </div>
              </AccordionTrigger>

              <AccordionContent className="pb-4">
                <div className="space-y-3 pt-2">
                    {/* Description */}
                    <div className="space-y-1.5">
                      <Label htmlFor={`${role.name}-description`} className="text-xs">
                        Description
                      </Label>
                      <Input
                        id={`${role.name}-description`}
                        value={role.description}
                        onChange={(e) =>
                          updateRole(role.name, { description: e.target.value })
                        }
                        placeholder="Brief description of this role"
                        disabled={disabled}
                        className="h-8 text-xs"
                      />
                    </div>

                    {/* Prompt */}
                    <div className="space-y-1.5">
                      <div className="flex items-center justify-between">
                        <Label htmlFor={`${role.name}-prompt`} className="text-xs">
                          System Prompt
                        </Label>
                        {presetRoles[role.name] && modified && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => resetRole(role.name)}
                            disabled={disabled}
                            className="h-6 text-xs"
                          >
                            <RotateCcw className="h-3 w-3 mr-1" />
                            Reset
                          </Button>
                        )}
                      </div>
                      <Textarea
                        id={`${role.name}-prompt`}
                        value={role.prompt}
                        onChange={(e) =>
                          updateRole(role.name, { prompt: e.target.value })
                        }
                        placeholder="System prompt for this role..."
                        disabled={disabled}
                        className="min-h-[80px] text-xs font-mono resize-y"
                      />
                      <p className="text-xs text-muted-foreground">
                        {role.prompt.length} characters
                      </p>
                    </div>

                    {/* Model */}
                    <div className="space-y-1.5">
                      <Label htmlFor={`${role.name}-model`} className="text-xs">
                        Model
                      </Label>
                      <Input
                        id={`${role.name}-model`}
                        value={role.model}
                        onChange={(e) =>
                          updateRole(role.name, { model: e.target.value })
                        }
                        placeholder="e.g., anthropic/claude-sonnet-4"
                        disabled={disabled}
                        className="h-8 font-mono text-xs"
                      />
                    </div>

                    {/* Weight */}
                    <div className="space-y-1.5">
                      <Label htmlFor={`${role.name}-weight`} className="text-xs">
                        Weight
                      </Label>
                      <Input
                        id={`${role.name}-weight`}
                        type="number"
                        min={0.1}
                        max={10}
                        step={0.1}
                        value={role.weight}
                        onChange={(e) =>
                          updateRole(role.name, { 
                            weight: parseFloat(e.target.value) || 1.0 
                          })
                        }
                        disabled={disabled}
                        className="h-8"
                      />
                      <p className="text-xs text-muted-foreground">
                        Higher weight = more influence in aggregation
                      </p>
                    </div>

                    {/* Advanced Config */}
                    <div className="space-y-2 pt-2 border-t">
                      <p className="text-xs font-medium">Advanced Configuration</p>
                      
                      <div className="grid grid-cols-2 gap-2">
                        {/* Temperature */}
                        <div className="space-y-1.5">
                          <Label 
                            htmlFor={`${role.name}-temperature`} 
                            className="text-xs"
                          >
                            Temperature
                          </Label>
                          <Input
                            id={`${role.name}-temperature`}
                            type="number"
                            min={0}
                            max={2}
                            step={0.1}
                            value={role.config.temperature}
                            onChange={(e) =>
                              updateRole(role.name, {
                                config: {
                                  ...role.config,
                                  temperature: parseFloat(e.target.value) || 0.7,
                                },
                              })
                            }
                            disabled={disabled}
                            className="h-8"
                          />
                        </div>

                        {/* Max Tokens */}
                        <div className="space-y-1.5">
                          <Label 
                            htmlFor={`${role.name}-max-tokens`} 
                            className="text-xs"
                          >
                            Max Tokens
                          </Label>
                          <Input
                            id={`${role.name}-max-tokens`}
                            type="number"
                            min={100}
                            max={32000}
                            step={100}
                            value={role.config.max_tokens || ""}
                            onChange={(e) =>
                              updateRole(role.name, {
                                config: {
                                  ...role.config,
                                  max_tokens: e.target.value 
                                    ? parseInt(e.target.value) 
                                    : null,
                                },
                              })
                            }
                            placeholder="Auto"
                            disabled={disabled}
                            className="h-8"
                          />
                        </div>
                      </div>
                    </div>

                    {/* Actions */}
                    {unsaved && (
                      <div className="flex justify-end gap-2 pt-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => resetRole(role.name)}
                          disabled={disabled || !presetRoles[role.name]}
                          className="h-7 text-xs"
                        >
                          <RotateCcw className="h-3 w-3 mr-1" />
                          Discard
                        </Button>
                        <Button
                          size="sm"
                          onClick={() => saveChanges(role.name)}
                          disabled={disabled}
                          className="h-7 text-xs"
                        >
                          <Save className="h-3 w-3 mr-1" />
                          Save Changes
                        </Button>
                      </div>
                    )}
                  </div>
              </AccordionContent>
            </AccordionItem>
          );
        })}
      </Accordion>

      {/* Summary */}
      <Card className="p-3 bg-muted/30">
        <div className="space-y-2">
          <p className="text-xs font-medium">Summary</p>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div>
              <span className="text-muted-foreground">Total Roles:</span>{" "}
              <span className="font-medium">{roles.length}</span>
            </div>
            <div>
              <span className="text-muted-foreground">Modified:</span>{" "}
              <span className="font-medium">
                {roles.filter(r => isModified(r)).length}
              </span>
            </div>
            <div>
              <span className="text-muted-foreground">Avg Weight:</span>{" "}
              <span className="font-medium">
                {(roles.reduce((sum, r) => sum + r.weight, 0) / roles.length).toFixed(1)}
              </span>
            </div>
            <div>
              <span className="text-muted-foreground">Unsaved:</span>{" "}
              <span className="font-medium">{hasUnsavedChanges.size}</span>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}
