"use client";

import * as React from "react";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { 
  ArrowRight, 
  Layers, 
  Users,
  CheckCircle2
} from "lucide-react";
import { cn } from "@/lib/utils";

export interface PipelineStage {
  name: string;
  description: string;
  output_mode: string;
  anonymize: boolean;
  pass_through: boolean;
}

export interface PipelineRole {
  name: string;
  stage: string;
}

interface PipelineVisualizerProps {
  stages: PipelineStage[];
  roles: PipelineRole[];
}

export function PipelineVisualizer({ stages, roles }: PipelineVisualizerProps) {
  // Group roles by stage
  const rolesByStage = React.useMemo(() => {
    const grouped = new Map<string, PipelineRole[]>();
    
    roles.forEach(role => {
      const stage = role.stage || "default";
      if (!grouped.has(stage)) {
        grouped.set(stage, []);
      }
      grouped.get(stage)!.push(role);
    });
    
    return grouped;
  }, [roles]);

  // Check for issues
  const hasIssues = React.useMemo(() => {
    const rolesWithoutStages = roles.filter(r => !r.stage || r.stage === "default");
    
    return {
      hasRolesWithoutStages: rolesWithoutStages.length > 0 && stages.length > 0,
      rolesWithoutStages
    };
  }, [roles, stages]);

  // If no stages configured, show simple role list
  if (stages.length === 0) {
    return (
      <Card className="p-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Users className="h-4 w-4 text-muted-foreground" />
            <Label className="text-sm font-medium">Single Stage Pipeline</Label>
          </div>
          <Badge variant="outline" className="text-xs">
            <CheckCircle2 className="h-3 w-3 mr-1" />
            {roles.length} {roles.length === 1 ? 'role' : 'roles'}
          </Badge>
        </div>

        <div className="flex flex-wrap gap-2">
          {roles.map(role => (
            <Badge key={role.name} variant="secondary">
              {role.name}
            </Badge>
          ))}
        </div>
      </Card>
    );
  }

  return (
    <Card className="p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Layers className="h-4 w-4 text-muted-foreground" />
          <Label className="text-sm font-medium">Pipeline Visualization</Label>
        </div>
        <Badge variant="outline" className="text-xs">
          <CheckCircle2 className="h-3 w-3 mr-1" />
          {stages.length} {stages.length === 1 ? 'stage' : 'stages'}
        </Badge>
      </div>

      {/* Stages */}
      <div className="space-y-3">
        {stages.map((stage, index) => {
          const stageRoles = rolesByStage.get(stage.name) || [];
          
          return (
            <div key={stage.name} className="space-y-2">
              {/* Stage Card */}
              <Card className={cn(
                "p-3 border-2",
                stage.anonymize && "border-primary/30 bg-primary/5"
              )}>
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <Badge variant="outline" className="text-xs">
                        Stage {index + 1}
                      </Badge>
                      <span className="font-medium text-sm">{stage.name}</span>
                    </div>
                    
                    {stage.description && (
                      <p className="text-xs text-muted-foreground mb-2">
                        {stage.description}
                      </p>
                    )}
                    
                    <div className="flex flex-wrap gap-1.5 text-xs">
                      <Badge variant="secondary" className="text-xs">
                        {stage.output_mode}
                      </Badge>
                      {stage.anonymize && (
                        <Badge variant="secondary" className="text-xs">
                          anonymized
                        </Badge>
                      )}
                      {stage.pass_through && (
                        <Badge variant="secondary" className="text-xs">
                          pass-through
                        </Badge>
                      )}
                    </div>
                  </div>
                </div>

                {/* Roles in this stage */}
                {stageRoles.length > 0 && (
                  <div className="mt-3 pt-3 border-t">
                    <div className="flex items-center gap-2 mb-2">
                      <Users className="h-3 w-3 text-muted-foreground" />
                      <span className="text-xs font-medium text-muted-foreground">
                        Roles ({stageRoles.length})
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {stageRoles.map(role => (
                        <Badge key={role.name} variant="outline" className="text-xs">
                          {role.name}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </Card>

              {/* Arrow between stages */}
              {index < stages.length - 1 && (
                <div className="flex justify-center py-1">
                  <ArrowRight className="h-4 w-4 text-muted-foreground" />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Roles without stages warning */}
      {hasIssues.hasRolesWithoutStages && (
        <Card className="p-3 border-amber-500/50 bg-amber-500/5">
          <p className="text-xs font-medium text-amber-700 dark:text-amber-400 mb-1">
            Roles not assigned to stages
          </p>
          <div className="flex flex-wrap gap-1.5">
            {hasIssues.rolesWithoutStages.map(role => (
              <Badge key={role.name} variant="secondary" className="text-xs">
                {role.name}
              </Badge>
            ))}
          </div>
        </Card>
      )}
    </Card>
  );
}
