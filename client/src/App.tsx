import { useState } from "react";
import ChatInterface from "./components/ChatInterface";
import FileUploadArea from "./components/FileUploadArea";
import { Database, UploadCloud } from "lucide-react";

function App() {
  const [activeTab, setActiveTab] = useState<"chat" | "knowledge">("chat");

  return (
    <div className="flex h-screen bg-neutral-900 text-neutral-100 font-sans selection:bg-indigo-500/30">
      {/* Sidebar */}
      <div className="w-64 bg-neutral-950 border-r border-neutral-800 flex flex-col">
        <div className="p-4 border-b border-neutral-800 flex items-center gap-2">
          <Database className="w-5 h-5 text-indigo-400" />
          <h1 className="font-semibold text-sm tracking-wide">AI Assistant</h1>
        </div>
        <nav className="flex-1 p-2 space-y-1">
          <button
            onClick={() => setActiveTab("chat")}
            className={`w-full flex items-center gap-3 px-3 py-2.5 text-sm rounded-lg transition-colors ${
              activeTab === "chat"
                ? "bg-indigo-500/10 text-indigo-400"
                : "text-neutral-400 hover:bg-neutral-800 hover:text-neutral-200"
            }`}
          >
            <Database className="w-4 h-4" />
            Chat Assistant
          </button>
          <button
            onClick={() => setActiveTab("knowledge")}
            className={`w-full flex items-center gap-3 px-3 py-2.5 text-sm rounded-lg transition-colors ${
              activeTab === "knowledge"
                ? "bg-indigo-500/10 text-indigo-400"
                : "text-neutral-400 hover:bg-neutral-800 hover:text-neutral-200"
            }`}
          >
            <UploadCloud className="w-4 h-4" />
            Knowledge Base
          </button>
        </nav>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0 bg-neutral-900">
        {activeTab === "chat" ? <ChatInterface /> : <FileUploadArea />}
      </div>
    </div>
  );
}

export default App;
