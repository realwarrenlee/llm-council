"use client";

import * as React from "react";
import { useSearchParams } from "next/navigation";
import { toast } from "sonner";
import { ModelCard, SynthesisCard } from "@/components/model-card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { ArrowUp } from "lucide-react";
import { api, type Role as ApiRole, type CouncilOutput } from "@/lib/api";
import { formatChatId, parseChatId } from "@/lib/format";
import { ClientLayout } from "./client-layout";
import { ModelSelector } from "@/components/council/model-selector";
import { ChairmanSelector } from "@/components/council/chairman-selector";
import { AggregationResults } from "@/components/council/aggregation-results";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";

const PLACEHOLDERS = [
  "What should we deliberate on?",
  "What decision are you wrestling with?",
  "What's worth debating?",
  "What's on the agenda today?",
  "What's on your mind?",
];

interface CouncilResult {
  role_name: string;
  content: string;
  model: string;
  loading: boolean;
  error?: string;
}

function CouncilPage() {
  const searchParams = useSearchParams();
  const [prompt, setPrompt] = React.useState("");
  const [generating, setGenerating] = React.useState(false);
  const [currentTask, setCurrentTask] = React.useState<string | null>(null);
  const [synthesis, setSynthesis] = React.useState<string | null>(null);
  const [results, setResults] = React.useState<CouncilResult[]>([]);
  const [currentPlaceholder, setCurrentPlaceholder] = React.useState("");
  const [currentOutput, setCurrentOutput] = React.useState<CouncilOutput | null>(null);
  const [currentChatId, setCurrentChatId] = React.useState<number | undefined>(undefined);
  const [loadingChat, setLoadingChat] = React.useState(false);
  const containerRef = React.useRef<HTMLDivElement>(null);
  
  // Model-based options state
  const [selectedModels, setSelectedModels] = React.useState<string[]>([]);
  const [chairmanModel, setChairmanModel] = React.useState<string | null>(null);
  const [outputMode, setOutputMode] = React.useState<"perspectives" | "synthesis" | "both">("both");
  const [anonymize, setAnonymize] = React.useState(true); // Keep anonymized during peer review to avoid bias
  const [viewMode, setViewMode] = React.useState<"aggregation" | "synthesis">("aggregation");
  
  const [customRoles, setCustomRoles] = React.useState<Array<{
    name: string;
    prompt: string;
    model: string;
    description: string;
    weight: number;
    config: {
      temperature: number;
      max_tokens: number | null;
    };
  }>>([]);

  React.useEffect(() => {
    setCurrentPlaceholder(
      PLACEHOLDERS[Math.floor(Math.random() * PLACEHOLDERS.length)]
    );
  }, [searchParams]);

  React.useEffect(() => {
    const chatId = searchParams.get("chat");
    const newChatId = chatId ? parseChatId(chatId) : undefined;
    
    if (newChatId !== currentChatId) {
      if (newChatId) {
        setCurrentChatId(newChatId);
        setLoadingChat(true);
        React.startTransition(() => {
          loadConversation(newChatId);
        });
      } else {
        setCurrentChatId(undefined);
        setLoadingChat(false);
      }
    }
  }, [searchParams, currentChatId]);

  const loadConversation = async (chatId: number) => {
    try {
      const conversation = await api.getConversation(chatId);
      setCurrentTask(conversation.task);
      const synthesisMsg = conversation.messages.find((m) => m.role === "synthesis");
      setSynthesis(synthesisMsg?.content || null);
      setResults(
        conversation.messages
          .filter((m) => m.role !== "user" && m.role !== "synthesis")
          .map((m) => ({
            role_name: m.role,
            content: m.content,
            model: m.model || "",
            loading: false,
          }))
      );
      
      // Load aggregation scores if available
      if (conversation.aggregation_scores) {
        setCurrentOutput({
          task: conversation.task,
          results: conversation.messages
            .filter((m) => m.role !== "user" && m.role !== "synthesis")
            .map((m) => ({
              role_name: m.role,
              content: m.content,
              model: m.model || "",
              success: true,
            })),
          output_mode: conversation.output_mode,
          synthesis: synthesisMsg?.content || undefined,
          metadata: {},
          confidence_scores: {},
          aggregate_rankings: {},
          aggregation_scores: conversation.aggregation_scores,
        });
      }
      
      setLoadingChat(false);
    } catch (err) {
      console.error("Failed to load conversation:", err);
      setLoadingChat(false);
    }
  };

  const initNewChat = () => {
    setCurrentTask(null);
    setSynthesis(null);
    setResults([]);
    setPrompt("");
    setGenerating(false);
    setCurrentOutput(null);
    setCurrentChatId(undefined);
    setLoadingChat(false);
    setSelectedModels([]);
    setChairmanModel(null);
    setOutputMode("both");
    setAnonymize(true); // Keep anonymized during peer review
    setCustomRoles([]);
    setCurrentPlaceholder(
      PLACEHOLDERS[Math.floor(Math.random() * PLACEHOLDERS.length)]
    );
  };



  const handleSelectChat = (chatId: number) => {
    setCurrentChatId(chatId);
    window.history.replaceState(null, '', `/?chat=${formatChatId(chatId)}`);
  };

  const scrollToBottom = (behavior: ScrollBehavior = "auto") => {
    if (containerRef.current) {
      containerRef.current.scrollTo({
        top: containerRef.current.scrollHeight,
        behavior,
      });
    }
  };

  const handleSubmit = async () => {
    if (!prompt.trim()) return;
    if (selectedModels.length < 2) {
      toast.error("Please select at least two council members");
      return;
    }
    if (!chairmanModel) {
      toast.error("Please select a chairman model");
      return;
    }

    const task = prompt.trim();
    setCurrentTask(task);
    setGenerating(true);
    setSynthesis(null);

    setResults(
      selectedModels.map((model) => ({
        role_name: model,
        content: "",
        model: "",
        loading: true,
      }))
    );

    setPrompt("");
    setTimeout(() => scrollToBottom("smooth"), 0);

    const apiKeys = JSON.parse(localStorage.getItem("llm-council-api-keys") || "[]");
    const apiKey = apiKeys.length > 0 ? apiKeys[0].key : "";

    if (!apiKey) {
      setResults((prev) =>
        prev.map((r) => ({
          ...r,
          loading: false,
          error: "No API key configured. Please add an API key in Settings > API Key.",
        }))
      );
      setGenerating(false);
      return;
    }

    const requestRoles: ApiRole[] = selectedModels.map((model) => {
      const customRole = customRoles.find(cr => cr.model === model);
      
      return {
        name: customRole?.name || model,
        prompt: customRole?.prompt || "",
        model: model,
        description: customRole?.description || "",
        config: {
          temperature: customRole?.config.temperature || 0.7,
          max_tokens: customRole?.config.max_tokens || null,
          top_p: null,
          presence_penalty: null,
          frequency_penalty: null,
          extra: {},
        },
        weight: customRole?.weight || 1.0,
      };
    });

    console.log("Sending deliberation request:", { task, roles: requestRoles, apiKey: apiKey ? "present" : "missing" });

    try {
      const data = await api.runDeliberation({
        task,
        roles: requestRoles,
        options: { 
          output_mode: outputMode,
          anonymize: anonymize,
          aggregation: "borda", // Always use borda as primary for sorting, but all methods computed
          review: true, // Peer review always enabled
          chairman_model: chairmanModel || undefined, // Use selected chairman model for synthesis
        },
        api_key: apiKey,
      });

      console.log("Received deliberation response:", data);
      console.log("Aggregation scores:", data.aggregation_scores);
      console.log("Metadata:", data.metadata);

      setResults(
        data.results.map((result) => ({
          role_name: result.role_name,
          content: result.content,
          model: result.model,
          loading: false,
        }))
      );

      console.log("Results set:", data.results.map(r => ({ name: r.role_name, contentLength: r.content?.length || 0 })));

      setSynthesis(data.synthesis || null);
      setCurrentOutput(data);

      try {
        await api.saveCouncilOutput({ task, output: data });
      } catch (err) {
        console.error("Auto-save failed:", err);
      }

      setTimeout(() => scrollToBottom("smooth"), 0);

      const notifications = localStorage.getItem("llm-council-notifications");
      if (notifications !== "false") {
        toast.success("Council deliberation complete!", {
          description: `${data.results.length} perspectives gathered`,
        });
      }
    } catch (err) {
      setResults((prev) =>
        prev.map((r) => ({
          ...r,
          loading: false,
          error: err instanceof Error ? err.message : "Error",
        }))
      );
    } finally {
      setGenerating(false);
    }
  };

  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSubmit();
    }
  };

  const hasResults = results.length > 0;

  return (
    <ClientLayout
      currentChatId={currentChatId}
      onSelectChat={handleSelectChat}
      onNewChat={initNewChat}
    >
      <div ref={containerRef} className="flex-1 overflow-y-auto">
        {loadingChat ? (
          <div className="max-w-4xl mx-auto px-4 py-6 min-h-full flex flex-col">
            <div className="mb-6">
              <Skeleton className="h-8 w-3/4" />
            </div>
            <Separator className="mb-6" />
            <div className="flex-1 space-y-6">
              <div className="space-y-3">
                <Skeleton className="h-6 w-32" />
                <Skeleton className="h-24 w-full" />
                <Skeleton className="h-4 w-48" />
              </div>
              <div className="space-y-3">
                <Skeleton className="h-6 w-32" />
                <Skeleton className="h-24 w-full" />
                <Skeleton className="h-4 w-48" />
              </div>
              <div className="space-y-3">
                <Skeleton className="h-6 w-32" />
                <Skeleton className="h-24 w-full" />
                <Skeleton className="h-4 w-48" />
              </div>
            </div>
          </div>
        ) : !hasResults ? (
          <div className="min-h-[calc(100vh-3.5rem)] flex flex-col px-4 py-12">
            <div className="flex-1 flex flex-col items-center justify-center">
              <p className="text-2xl text-muted-foreground mb-8 text-center">
                {currentPlaceholder}
              </p>
              <div className="w-full max-w-4xl space-y-6">
                <div className="grid grid-cols-2 gap-6">
                  <ModelSelector
                    selectedModels={selectedModels}
                    onModelsChange={setSelectedModels}
                    disabled={generating}
                  />
                  
                  <ChairmanSelector
                    selectedChairman={chairmanModel}
                    onChairmanChange={setChairmanModel}
                    disabled={generating}
                  />
                </div>
                
                {selectedModels.length >= 2 && chairmanModel && (
                  <>
                    <div className="relative">
                      <Textarea
                        value={prompt}
                        onChange={(e) => setPrompt(e.target.value)}
                        placeholder="Ask anything"
                        className="w-full px-4 py-3 pr-12 resize-none rounded-2xl"
                        rows={3}
                        onKeyDown={handleKeyDown}
                        autoFocus
                      />
                      <Button
                        onClick={handleSubmit}
                        disabled={!prompt.trim() || generating}
                        size="icon"
                        className="absolute bottom-3 right-3 rounded-lg"
                      >
                        <ArrowUp className="h-4 w-4" />
                      </Button>
                    </div>
                  </>
                )}
                
                {(selectedModels.length < 2 || !chairmanModel) && (
                  <p className="text-center text-sm text-muted-foreground">
                    Select two or more council members and one chairman model to start deliberating
                  </p>
                )}
              </div>
            </div>
          </div>
        ) : (
          <div className="max-w-4xl mx-auto px-4 py-6 min-h-full flex flex-col">
            <div className="mb-6 flex items-center justify-between">
              <h1 className="text-xl font-medium">{currentTask}</h1>
              {hasResults && !generating && (
                <Tabs value={viewMode} onValueChange={(v) => setViewMode(v as "aggregation" | "synthesis")}>
                  <TabsList>
                    <TabsTrigger value="aggregation">Rankings</TabsTrigger>
                    <TabsTrigger value="synthesis">Synthesis</TabsTrigger>
                  </TabsList>
                </Tabs>
              )}
            </div>
            <Separator className="mb-6" />
            <div className="flex-1">
              {viewMode === "aggregation" ? (
                <>
                  {results.map((result) => (
                    <ModelCard
                      key={result.role_name}
                      roleName={result.role_name}
                      content={result.content}
                      model={result.model}
                      loading={result.loading}
                      error={result.error || null}
                    />
                  ))}
                  
                  {currentOutput?.aggregation_scores && Object.keys(currentOutput.aggregation_scores).length > 0 ? (
                    <AggregationResults
                      aggregationScores={currentOutput.aggregation_scores}
                      primaryMethod="borda"
                    />
                  ) : currentOutput && results.length > 1 ? (
                    <div className="mt-6 border rounded-lg p-6 bg-muted/30">
                      <p className="text-sm text-muted-foreground text-center">
                        💡 Peer review rankings require an API key. Add your OpenRouter API key in settings to enable multi-method aggregation analysis.
                      </p>
                    </div>
                  ) : null}
                </>
              ) : viewMode === "synthesis" && synthesis ? (
                <SynthesisCard content={synthesis} />
              ) : null}
            </div>
            <div className="mt-8 pt-6 sticky bottom-0 bg-background">
              <div className="relative">
                <Textarea
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="Ask a follow-up..."
                  className="w-full px-4 py-3 pr-12 resize-none rounded-2xl"
                  rows={2}
                  onKeyDown={handleKeyDown}
                />
                <Button
                  onClick={handleSubmit}
                  disabled={!prompt.trim() || generating}
                  size="icon"
                  className="absolute bottom-3 right-3 rounded-lg"
                >
                  <ArrowUp className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </ClientLayout>
  );
}

export default function Page() {
  return (
    <React.Suspense fallback={<div>Loading...</div>}>
      <CouncilPage />
    </React.Suspense>
  );
}

