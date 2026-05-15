const API_URL = "http://localhost:8000";

export interface Role {
  name: string;
  prompt: string;
  model: string;
  description: string;
  config: {
    temperature: number;
    max_tokens: number | null;
    top_p: number | null;
    presence_penalty: number | null;
    frequency_penalty: number | null;
    extra: Record<string, unknown>;
  };
  weight: number;
}

export interface CouncilResult {
  role_name: string;
  content: string;
  model: string;
  tokens_used?: number;
  latency_ms?: number;
  error?: string;
  success: boolean;
}

export interface AggregationScores {
  scores: Record<string, number>;
  confidence_intervals?: Record<string, [number, number]> | null;
}

export interface CouncilOutput {
  task: string;
  results: CouncilResult[];
  output_mode: string;
  synthesis?: string;
  metadata: Record<string, unknown>;
  confidence_scores: Record<string, number>;
  aggregate_rankings?: Record<string, number>; // Legacy: primary method scores
  aggregation_scores?: Record<string, AggregationScores>; // New: all methods
}

export interface DeliberationRequest {
  task: string;
  roles: Role[];
  options?: {
    output_mode?: "synthesis" | "perspectives" | "both";
    anonymize?: boolean;
    review?: boolean;
    reviewers?: string[];
    aggregation?: string;
    chairman_model?: string;  // Model to use for synthesis
    stages?: Array<{
      name: string;
      description: string;
      output_mode: string;
      anonymize: boolean;
      reviewers: string[];
      min_reviewers: number;
      aggregation_method: string;
      pass_through: boolean;
    }>;
  };
  api_key?: string;
}

export interface Conversation {
  id: number;
  title: string;
  task: string;
  output_mode: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  aggregation_scores?: {
    [method: string]: {
      scores: { [role: string]: number };
      confidence_intervals?: { [role: string]: [number, number] } | null;
    };
  };
}

export interface Message {
  id: number;
  conversation_id: number;
  role: string;
  content: string;
  model?: string;
  tokens_used?: number;
  latency_ms?: number;
  created_at: string;
}

export interface ConversationWithMessages extends Conversation {
  messages: Message[];
}

export interface SaveCouncilOutputRequest {
  task: string;
  output: CouncilOutput;
  title?: string;
}

export const api = {
  async getRoles(): Promise<Role[]> {
    const res = await fetch(`${API_URL}/api/council/roles`);
    if (!res.ok) throw new Error("Failed to fetch roles");
    return res.json();
  },

  // Conversation endpoints
  async getConversations(limit = 50, offset = 0): Promise<{ conversations: Conversation[]; total: number }> {
    const res = await fetch(`${API_URL}/api/conversations?limit=${limit}&offset=${offset}`);
    if (!res.ok) throw new Error("Failed to fetch conversations");
    return res.json();
  },

  async getConversation(id: number): Promise<ConversationWithMessages> {
    const res = await fetch(`${API_URL}/api/conversations/${id}`);
    if (!res.ok) {
      const error = await res.text();
      throw new Error(`Failed to fetch conversation: ${res.status} ${error}`);
    }
    return res.json();
  },

  async createConversation(title: string, task: string, output_mode = "perspectives"): Promise<Conversation> {
    const res = await fetch(`${API_URL}/api/conversations`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, task, output_mode }),
    });
    if (!res.ok) throw new Error("Failed to create conversation");
    return res.json();
  },

  async updateConversation(id: number, title: string): Promise<Conversation> {
    const res = await fetch(`${API_URL}/api/conversations/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title }),
    });
    if (!res.ok) throw new Error("Failed to update conversation");
    return res.json();
  },

  async deleteConversation(id: number): Promise<void> {
    const res = await fetch(`${API_URL}/api/conversations/${id}`, {
      method: "DELETE",
    });
    if (!res.ok) throw new Error("Failed to delete conversation");
  },

  async saveCouncilOutput(request: SaveCouncilOutputRequest): Promise<Conversation> {
    const res = await fetch(`${API_URL}/api/conversations/save-council-output`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Unknown error" }));
      console.error("Save council output error:", err);
      throw new Error(err.detail || "Failed to save council output");
    }
    return res.json();
  },

  async runDeliberation(request: DeliberationRequest): Promise<CouncilOutput> {
    const { api_key, ...body } = request;
    const url = new URL(`${API_URL}/api/council/run`);
    if (api_key) {
      url.searchParams.append("api_key", api_key);
    }
    const res = await fetch(url.toString(), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Deliberation failed");
    }
    return res.json();
  },

  async streamDeliberation(
    request: DeliberationRequest,
    onMessage: (msg: unknown) => void
  ): Promise<void> {
    const ws = new WebSocket(`ws://localhost:8000/api/council/stream`);

    ws.onopen = () => {
      ws.send(JSON.stringify(request));
    };

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      onMessage(msg);
    };

    return new Promise((resolve, reject) => {
      ws.onclose = () => resolve();
      ws.onerror = (err) => reject(err);
    });
  },
};
