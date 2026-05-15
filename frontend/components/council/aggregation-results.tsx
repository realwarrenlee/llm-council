"use client";

import * as React from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { BarChart3, TrendingUp, Target, Info } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { ArrowUpDown, ArrowUp, ArrowDown } from "lucide-react";
import type { AggregationScores } from "@/lib/api";

interface AggregationResultsProps {
  aggregationScores: Record<string, AggregationScores>;
  primaryMethod?: string;
}

const METHOD_INFO = {
  borda: {
    name: "Borda Count",
    icon: BarChart3,
    description: "Simple points-based ranking. Each position earns points (1st = N-1, 2nd = N-2, etc.)",
    color: "bg-blue-500/10 text-blue-700 dark:text-blue-400",
  },
  bradley_terry: {
    name: "Bradley-Terry",
    icon: TrendingUp,
    description: "Probability model from pairwise wins. Shows relative strength between models.",
    color: "bg-purple-500/10 text-purple-700 dark:text-purple-400",
  },
  elo: {
    name: "ELO Rating",
    icon: Target,
    description: "Chess-style rating with confidence intervals. Dynamic competitive scoring.",
    color: "bg-orange-500/10 text-orange-700 dark:text-orange-400",
  },
};

export function AggregationResults({ aggregationScores, primaryMethod = "borda" }: AggregationResultsProps) {
  const [sortBy, setSortBy] = React.useState<string>(primaryMethod);
  const [sortDirection, setSortDirection] = React.useState<"asc" | "desc">("desc");

  // Get visible methods (those with scores)
  const visibleMethods = React.useMemo(() => {
    return Object.keys(METHOD_INFO).filter(key => {
      if (!aggregationScores[key]) return false;
      return Object.keys(aggregationScores[key].scores || {}).length > 0;
    });
  }, [aggregationScores]);

  // Get all unique model names across all methods
  const allRoles = React.useMemo(() => {
    const models = new Set<string>();
    Object.values(aggregationScores).forEach((method) => {
      Object.keys(method.scores).forEach((model) => models.add(model));
    });
    return Array.from(models);
  }, [aggregationScores]);

  // Sort models by selected method and direction
  const sortedRoles = React.useMemo(() => {
    const scores = aggregationScores[sortBy]?.scores || {};
    return [...allRoles].sort((a, b) => {
      const scoreA = scores[a] || 0;
      const scoreB = scores[b] || 0;
      return sortDirection === "desc" ? scoreB - scoreA : scoreA - scoreB;
    });
  }, [allRoles, aggregationScores, sortBy, sortDirection]);

  // Handle column header click
  const handleSort = (method: string) => {
    if (sortBy === method) {
      // Toggle direction if clicking same column
      setSortDirection(sortDirection === "desc" ? "asc" : "desc");
    } else {
      // Sort by new column, default to descending
      setSortBy(method);
      setSortDirection("desc");
    }
  };

  // Calculate rank for each model in each method
  const getRank = (method: string, modelName: string): number => {
    const scores = aggregationScores[method]?.scores || {};
    const sortedByScore = Object.entries(scores).sort(([, a], [, b]) => b - a);
    return sortedByScore.findIndex(([name]) => name === modelName) + 1;
  };

  // Check if ranks are consistent across methods
  const getRankConsistency = (modelName: string): "high" | "medium" | "low" => {
    const ranks = Object.keys(aggregationScores).map((method) => getRank(method, modelName));
    const maxDiff = Math.max(...ranks) - Math.min(...ranks);
    if (maxDiff <= 1) return "high";
    if (maxDiff <= 2) return "medium";
    return "low";
  };

  if (!aggregationScores || Object.keys(aggregationScores).length === 0) {
    return null;
  }

  return (
    <Card className="mt-6">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          Model Rankings
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger>
                <Info className="h-4 w-4 text-muted-foreground" />
              </TooltipTrigger>
              <TooltipContent className="max-w-sm">
                <p>All three aggregation methods are computed simultaneously. When they agree, you have high confidence. When they diverge, it reveals different perspectives on quality.</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </CardTitle>
        <CardDescription>
          Comparing {visibleMethods.length} aggregation method{visibleMethods.length !== 1 ? 's' : ''}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[200px]">Model</TableHead>
              {Object.entries(METHOD_INFO).map(([key, info]) => {
                if (!aggregationScores[key]) return null;
                // Hide column if no models have scores for this method
                const hasAnyScores = Object.keys(aggregationScores[key].scores || {}).length > 0;
                if (!hasAnyScores) return null;
                
                const Icon = info.icon;
                const isSorted = sortBy === key;
                return (
                  <TableHead key={key} className="text-center">
                    <button
                      onClick={() => handleSort(key)}
                      className="flex items-center justify-center gap-2 mx-auto hover:text-foreground transition-colors cursor-pointer"
                    >
                      <Icon className="h-4 w-4" />
                      <span>{info.name}</span>
                      {isSorted ? (
                        sortDirection === "desc" ? (
                          <ArrowDown className="h-3 w-3" />
                        ) : (
                          <ArrowUp className="h-3 w-3" />
                        )
                      ) : (
                        <ArrowUpDown className="h-3 w-3 opacity-30" />
                      )}
                    </button>
                  </TableHead>
                );
              })}
            </TableRow>
          </TableHeader>
          <TableBody>
            {sortedRoles.map((modelName) => {
              return (
                <TableRow key={modelName}>
                  <TableCell className="font-medium">
                    {modelName}
                  </TableCell>
                  {Object.entries(METHOD_INFO).map(([key, info]) => {
                    if (!aggregationScores[key]) return null;
                    // Hide column if no models have scores for this method
                    const hasAnyScores = Object.keys(aggregationScores[key].scores || {}).length > 0;
                    if (!hasAnyScores) return null;
                    
                    const score = aggregationScores[key].scores[modelName];
                    const rank = getRank(key, modelName);
                    const ci = aggregationScores[key].confidence_intervals?.[modelName];

                    if (score === undefined) {
                      return <TableCell key={key} className="text-center text-muted-foreground">-</TableCell>;
                    }

                    return (
                      <TableCell key={key} className="text-center">
                        <div className="flex items-center justify-center gap-2">
                          <span className="text-sm font-medium">
                            {score.toFixed(1)}
                          </span>
                          {ci && (
                            <TooltipProvider>
                              <Tooltip>
                                <TooltipTrigger className="text-xs text-muted-foreground">
                                  ±
                                </TooltipTrigger>
                                <TooltipContent>
                                  <p>95% CI: [{ci[0].toFixed(1)}, {ci[1].toFixed(1)}]</p>
                                </TooltipContent>
                              </Tooltip>
                            </TooltipProvider>
                          )}
                        </div>
                      </TableCell>
                    );
                  })}
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
