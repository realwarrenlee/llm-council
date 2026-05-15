"use client";

import * as React from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { ChevronDown, ChevronUp } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";

// Role to icon mapping
const ROLE_ICONS: Record<string, string> = {
  advocate: "",
  critic: "",
  pragmatist: "",
  visionary: "",
  analyst: "",
  creative: "",
  researcher: "",
  security: "",
  performance: "",
  synthesizer: "",
  builder: "",
  optimist: "",
  pessimist: "",
  domain_expert: "",
  reviewer: "",
  architect: "",
  explorer: "",
  editor: "",
  stylist: "",
  proofreader: "",
  audience_rep: "",
  vc_investor: "",
  technologist: "",
  customer_rep: "",
  competitor: "",
  default: "",
};

// Extract "leans" position from content based on keywords
function extractLeans(content: string): string {
  const lower = content.toLowerCase();

  // Strong proceed indicators
  if (
    /\b(recommend|proceed|yes|go ahead|do it|advantage|benefit|opportunity)\b/i.test(
      lower
    ) &&
    !/(not recommend|don't proceed|caution|however|but|concern|risk)/i.test(
      lower.slice(0, 200)
    )
  ) {
    return "Proceed";
  }

  // Strong caution indicators
  if (
    /\b(caution|concern|risk|warning|however|but|challenge|problem|issue|complexity|difficult)\b/i.test(
      lower
    ) &&
    !/(recommend|proceed|advantage|benefit)/i.test(lower.slice(0, 200))
  ) {
    return "Caution";
  }

  // Conditional indicators
  if (
    /\b(if|conditional|depends|consider|before|when|context|situation|careful|measure)\b/i.test(
      lower
    )
  ) {
    return "Conditional";
  }

  // Neutral/default
  return "Neutral";
}

interface ModelCardProps {
  roleName: string;
  content: string;
  model?: string;
  loading?: boolean;
  error?: string | null;
}

export function ModelCard({ roleName, content, model, loading, error }: ModelCardProps) {
  const [isExpanded, setIsExpanded] = React.useState(false);
  const icon = ROLE_ICONS[roleName.toLowerCase()] || ROLE_ICONS.default;
  const leans = !loading && !error ? extractLeans(content) : "";
  const displayName = roleName.charAt(0).toUpperCase() + roleName.slice(1).replace(/_/g, " ");

  return (
    <>
      <div>
        {loading ? (
          // Loading State
          <div className="py-6 px-4">
            <div className="flex items-center gap-3 mb-3">
              <span className="text-sm font-semibold tracking-wider uppercase">
                {displayName}
              </span>
              <span className="text-sm text-muted-foreground">→ Thinking...</span>
            </div>
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-4 w-1/2 mt-2" />
          </div>
        ) : error ? (
          // Error State
          <div className="py-6 px-4">
            <div className="flex items-center gap-3 mb-3">
              <span className="text-sm font-semibold tracking-wider uppercase">
                {displayName}
              </span>
            </div>
            <p className="text-sm text-destructive">{error}</p>
          </div>
        ) : (
          // Content State
          <div className="py-6 px-4">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <span className="text-sm font-semibold tracking-wider uppercase">
                  {displayName}
                </span>
                {leans && (
                  <span className="text-sm text-muted-foreground">
                    → Leans: {leans}
                  </span>
                )}
              </div>
              <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
              >
                {isExpanded ? (
                  <>
                    Show less <ChevronUp className="h-3 w-3" />
                  </>
                ) : (
                  <>
                    Show more <ChevronDown className="h-3 w-3" />
                  </>
                )}
              </button>
            </div>
            {isExpanded && (
              <div className="prose prose-sm dark:prose-invert max-w-none text-muted-foreground prose-headings:text-foreground prose-strong:text-foreground prose-a:text-primary">
                <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>
                  {content}
                </ReactMarkdown>
              </div>
            )}
          </div>
        )}
      </div>
      <Separator />
    </>
  );
}

interface SynthesisCardProps {
  content: string;
}

export function SynthesisCard({ content }: SynthesisCardProps) {
  return (
    <div>
      <div className="py-6 px-4">
        <div className="mb-4">
          <span className="text-sm font-semibold tracking-wider uppercase">
            What the Council Recommends
          </span>
        </div>
        <div className="prose prose-sm dark:prose-invert max-w-none text-muted-foreground prose-headings:text-foreground prose-strong:text-foreground prose-a:text-primary">
          <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>
            {content}
          </ReactMarkdown>
        </div>
      </div>
    </div>
  );
}
