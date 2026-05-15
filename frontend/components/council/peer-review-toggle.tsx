"use client";

import * as React from "react";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Users, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";

interface PeerReviewToggleProps {
  enabled: boolean;
  onEnabledChange: (enabled: boolean) => void;
  reviewers: string[];
  onReviewersChange: (reviewers: string[]) => void;
  minReviewers: number;
  onMinReviewersChange: (min: number) => void;
  availableRoles: string[];
  disabled?: boolean;
}

export function PeerReviewToggle({
  enabled,
  onEnabledChange,
  reviewers,
  onReviewersChange,
  minReviewers,
  onMinReviewersChange,
  availableRoles,
  disabled = false,
}: PeerReviewToggleProps) {
  const [open, setOpen] = React.useState(false);

  const handleToggleReviewer = (roleName: string) => {
    if (reviewers.includes(roleName)) {
      onReviewersChange(reviewers.filter((r) => r !== roleName));
    } else {
      onReviewersChange([...reviewers, roleName]);
    }
  };

  const handleRemoveReviewer = (roleName: string) => {
    onReviewersChange(reviewers.filter((r) => r !== roleName));
  };

  return (
    <div className="space-y-4">
      {/* Main Toggle */}
      <div className="flex items-center justify-between space-x-2">
        <div className="flex items-center gap-2 flex-1">
          <Users className="h-4 w-4 text-muted-foreground" />
          <div className="space-y-0.5">
            <Label htmlFor="peer-review" className="text-sm font-medium cursor-pointer">
              Peer Review
            </Label>
            <p className="text-xs text-muted-foreground">
              Enable roles to review each other&apos;s outputs
            </p>
          </div>
        </div>
        <Switch
          id="peer-review"
          checked={enabled}
          onCheckedChange={onEnabledChange}
          disabled={disabled}
        />
      </div>

      {/* Review Configuration (shown when enabled) */}
      {enabled && (
        <div className="pl-6 space-y-3 border-l-2 border-muted">
          {/* Reviewer Selection */}
          <div className="space-y-2">
            <Label className="text-xs font-medium text-muted-foreground">
              Reviewers
            </Label>
            <Popover open={open} onOpenChange={setOpen}>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full justify-start text-left font-normal"
                  disabled={disabled || availableRoles.length === 0}
                >
                  {reviewers.length === 0 ? (
                    <span className="text-muted-foreground">Select reviewers...</span>
                  ) : (
                    <span>{reviewers.length} selected</span>
                  )}
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-[300px] p-0" align="start">
                <Command>
                  <CommandInput placeholder="Search roles..." />
                  <CommandList>
                    <CommandEmpty>No roles found.</CommandEmpty>
                    <CommandGroup>
                      {availableRoles.map((role) => (
                        <CommandItem
                          key={role}
                          value={role}
                          onSelect={() => handleToggleReviewer(role)}
                        >
                          <div className="flex items-center gap-2 flex-1">
                            <div
                              className={`h-4 w-4 border rounded flex items-center justify-center ${
                                reviewers.includes(role)
                                  ? "bg-primary border-primary"
                                  : "border-input"
                              }`}
                            >
                              {reviewers.includes(role) && (
                                <div className="h-2 w-2 bg-primary-foreground rounded-sm" />
                              )}
                            </div>
                            <span>{role}</span>
                          </div>
                        </CommandItem>
                      ))}
                    </CommandGroup>
                  </CommandList>
                </Command>
              </PopoverContent>
            </Popover>

            {/* Selected Reviewers */}
            {reviewers.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {reviewers.map((reviewer) => (
                  <Badge
                    key={reviewer}
                    variant="secondary"
                    className="text-xs pl-2 pr-1 py-0.5"
                  >
                    {reviewer}
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-auto p-0 ml-1 hover:bg-transparent"
                      onClick={() => handleRemoveReviewer(reviewer)}
                      disabled={disabled}
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  </Badge>
                ))}
              </div>
            )}
          </div>

          {/* Minimum Reviewers */}
          <div className="space-y-2">
            <Label htmlFor="min-reviewers" className="text-xs font-medium text-muted-foreground">
              Minimum Reviewers
            </Label>
            <Input
              id="min-reviewers"
              type="number"
              min={1}
              max={reviewers.length || 10}
              value={minReviewers}
              onChange={(e) => onMinReviewersChange(parseInt(e.target.value) || 1)}
              disabled={disabled}
              className="h-8"
            />
            <p className="text-xs text-muted-foreground">
              Minimum number of reviewers required per response
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
