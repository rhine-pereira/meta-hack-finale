export class GenesisClient {
  private baseUrl: string;
  private sessionId: string | null = null;
  private requestId = 0;

  constructor(baseUrl = "http://localhost:7860") {
    this.baseUrl = baseUrl;
  }

  async initialize(): Promise<void> {
    try {
      const res = await fetch(`${this.baseUrl}/mcp`, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Accept": "application/json, text/event-stream"
        },
        body: JSON.stringify({
          jsonrpc: "2.0",
          method: "initialize",
          params: {
            protocolVersion: "2024-11-05",
            capabilities: {},
            clientInfo: { name: "genesis-ui", version: "1.0.0" }
          },
          id: this.requestId++
        })
      });

      if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);

      this.sessionId = res.headers.get("mcp-session-id");
      const text = await res.text();
      const data = this.parseResponse(text);
      console.log("MCP Initialized:", data);
    } catch (error) {
      console.error("Failed to initialize Genesis client:", error);
      throw error;
    }
  }

  async callTool(name: string, args: Record<string, any> = {}): Promise<any> {
    if (!this.sessionId) {
      await this.initialize();
    }

    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      "Accept": "application/json, text/event-stream"
    };
    if (this.sessionId) headers["mcp-session-id"] = this.sessionId;

    try {
      const res = await fetch(`${this.baseUrl}/mcp`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          jsonrpc: "2.0",
          method: "tools/call",
          params: { name, arguments: args },
          id: this.requestId++
        })
      });

      if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);

      const sid = res.headers.get("mcp-session-id");
      if (sid) this.sessionId = sid;

      const text = await res.text();
      return this.parseResponse(text);
    } catch (error) {
      console.error(`Tool call '${name}' failed:`, error);
      throw error;
    }
  }

  private parseResponse(text: string): any {
    text = text.trim();
    if (text.startsWith("{")) {
      const data = JSON.parse(text);
      if (data.error) throw new Error(data.error.message || "Unknown MCP error");
      return this.extractResult(data.result);
    }

    // Handle SSE-style responses from FastMCP
    const dataLines = text.split("\n")
      .filter(l => l.startsWith("data:"))
      .map(l => l.slice(5).trim());
    
    if (dataLines.length) {
      const lastLine = dataLines[dataLines.length - 1];
      const data = JSON.parse(lastLine);
      if (data.error) throw new Error(data.error.message || "Unknown MCP error");
      return this.extractResult(data.result);
    }

    throw new Error("Unable to parse MCP response");
  }

  private extractResult(result: any): any {
    if (!result) return result;
    
    // FastMCP tool results often come in a 'content' array or 'structuredContent'
    if (result.structuredContent) {
      return result.structuredContent;
    }
    
    if (Array.isArray(result.content) && result.content.length > 0) {
      const firstContent = result.content[0];
      if (firstContent.type === "text" && typeof firstContent.text === "string") {
        try {
          // If the text is JSON, parse it
          if (firstContent.text.trim().startsWith("{") || firstContent.text.trim().startsWith("[")) {
            return JSON.parse(firstContent.text);
          }
          return firstContent.text;
        } catch {
          return firstContent.text;
        }
      }
    }
    
    return result;
  }

  async checkHealth(): Promise<boolean> {
    try {
      const res = await fetch(`${this.baseUrl}/health`);
      const data = await res.json();
      return data.status === "ok";
    } catch {
      return false;
    }
  }
}

export const genesisClient = new GenesisClient();
