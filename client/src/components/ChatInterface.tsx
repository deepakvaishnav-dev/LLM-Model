import React, { useState, useRef, useEffect } from "react";
import { Send, Bot, User, Code2, AlertTriangle } from "lucide-react";

interface Source {
  file: string;
  text: string;
  score: number;
}

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
}

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        "Hello! I am your AI Knowledge Assistant. Upload projects to the Knowledge Base, then ask me anything about your code.",
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = { role: "user" as const, content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const apiUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
      const response = await fetch(`${apiUrl}/api/chat/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ query: input }),
      });

      if (!response.ok) {
        // Read the actual error detail from the backend
        let errorMessage = "An unexpected error occurred. Please try again.";
        try {
          const errData = await response.json();
          if (errData?.detail) errorMessage = errData.detail;
        } catch (_) {
          /* ignore parse errors */
        }

        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: `⚠️ ${errorMessage}`,
          },
        ]);
        return;
      }

      const data = await response.json();

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.response,
          sources: data.sources,
        },
      ]);
    } catch (error) {
      console.error(error);
      const errorMsg =
        error instanceof Error
          ? error.message
          : "An unexpected error occurred.";
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `⚠️ ${errorMsg}`,
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-neutral-900 overflow-hidden">
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6 scroll-smooth">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex gap-4 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            {msg.role === "assistant" && (
              <div className="w-8 h-8 rounded-full bg-indigo-500/20 text-indigo-400 flex items-center justify-center flex-shrink-0 border border-indigo-500/30">
                <Bot className="w-5 h-5" />
              </div>
            )}

            <div
              className={`flex flex-col max-w-[80%] ${msg.role === "user" ? "items-end" : "items-start"}`}
            >
              <div
                className={`p-4 rounded-2xl shadow-sm ${
                  msg.role === "user"
                    ? "bg-indigo-600 text-white rounded-tr-none"
                    : "bg-neutral-800 text-neutral-200 rounded-tl-none border border-neutral-700/50"
                }`}
              >
                <div className="whitespace-pre-wrap leading-relaxed text-[15px]">
                  {msg.content}
                </div>
              </div>

              {/* Citations */}
              {msg.sources && msg.sources.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-2">
                  <span className="text-xs text-neutral-500 font-medium mr-1 flex items-center h-6">
                    Sources:
                  </span>
                  {msg.sources.map((src, i) => (
                    <div
                      key={i}
                      className="group relative cursor-pointer flex items-center gap-1.5 px-2.5 py-1 bg-neutral-800 hover:bg-neutral-700 border border-neutral-700 rounded-md text-xs text-neutral-400 transition-colors"
                    >
                      <Code2 className="w-3.5 h-3.5" />
                      <span className="truncate max-w-[120px]">{src.file}</span>

                      {/* Tooltip for code snippet preview */}
                      <div className="absolute bottom-full left-0 mb-2 hidden group-hover:block w-[300px] p-3 bg-neutral-800 border border-neutral-700 rounded-lg shadow-xl z-10 text-neutral-300">
                        <div className="font-mono text-[10px] whitespace-pre-wrap break-words opacity-80 overflow-hidden text-ellipsis line-clamp-6">
                          {src.text}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {msg.role === "user" && (
              <div className="w-8 h-8 rounded-full bg-neutral-800 text-neutral-400 flex items-center justify-center flex-shrink-0 border border-neutral-700">
                <User className="w-5 h-5" />
              </div>
            )}
          </div>
        ))}

        {isLoading && (
          <div className="flex gap-4 p-2">
            <div className="w-8 h-8 rounded-full bg-indigo-500/20 text-indigo-400 flex items-center justify-center flex-shrink-0 border border-indigo-500/30">
              <Bot className="w-5 h-5" />
            </div>
            <div className="flex items-center gap-1">
              <span
                className="w-2 h-2 rounded-full bg-neutral-600 animate-bounce"
                style={{ animationDelay: "0ms" }}
              />
              <span
                className="w-2 h-2 rounded-full bg-neutral-600 animate-bounce"
                style={{ animationDelay: "150ms" }}
              />
              <span
                className="w-2 h-2 rounded-full bg-neutral-600 animate-bounce"
                style={{ animationDelay: "300ms" }}
              />
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-4 border-t border-neutral-800 bg-neutral-900/80 backdrop-blur">
        <form
          onSubmit={handleSubmit}
          className="max-w-4xl mx-auto relative group"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isLoading}
            placeholder="Ask about a function, find a bug, or request an explanation..."
            className="w-full bg-neutral-800 border border-neutral-700 text-neutral-200 rounded-xl pl-5 pr-14 py-4 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all shadow-sm placeholder-neutral-500 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className="absolute right-2 top-2 p-2 bg-indigo-500 hover:bg-indigo-600 disabled:bg-indigo-500/0 disabled:text-neutral-500 text-white rounded-lg transition-all"
          >
            <Send className="w-5 h-5" />
          </button>
        </form>
        <div className="text-center mt-3 text-xs text-neutral-500 flex items-center justify-center gap-1.5">
          <AlertTriangle className="w-3.5 h-3.5" />
          AI can make mistakes. Verify critical code suggestions.
        </div>
      </div>
    </div>
  );
}
