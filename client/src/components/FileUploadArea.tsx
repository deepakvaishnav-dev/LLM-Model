import React, { useState } from "react";
import { Upload, FileUp, CheckCircle, AlertCircle } from "lucide-react";

export default function FileUploadArea() {
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<
    "idle" | "uploading" | "success" | "error"
  >("idle");
  const [message, setMessage] = useState("");

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) setFile(droppedFile);
  };

  const handleUpload = async () => {
    if (!file) return;
    setStatus("uploading");

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch("http://localhost:8000/api/upload/", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();
      if (response.ok) {
        setStatus("success");
        setMessage(data.message);
      } else {
        setStatus("error");
        setMessage(data.detail || data.error || "Upload failed");
      }
    } catch (err) {
      console.error(err);
      setStatus("error");
      setMessage("Network error occurred during upload.");
    }
  };

  return (
    <div className="flex-1 flex flex-col items-center justify-center p-8">
      <div className="max-w-xl w-full">
        <h2 className="text-2xl font-bold mb-2">Knowledge Base</h2>
        <p className="text-neutral-400 mb-8">
          Upload codebases (ZIP), documentation (PDF, MD), to expand the
          assistant's knowledge.
        </p>

        <div
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleDrop}
          className="border-2 border-dashed border-neutral-700 rounded-xl p-12 flex flex-col items-center justify-center bg-neutral-800/20 hover:bg-neutral-800/40 transition-colors"
        >
          <div className="w-16 h-16 bg-neutral-800 rounded-full flex items-center justify-center mb-4 text-indigo-400">
            <Upload className="w-8 h-8" />
          </div>
          <p className="text-lg font-medium text-neutral-200 mb-1">
            Drag and drop your files here
          </p>
          <p className="text-sm text-neutral-500 mb-6">
            Supports .zip, .pdf, .md, .txt up to 50MB
          </p>

          <label className="cursor-pointer bg-neutral-800 hover:bg-neutral-700 text-neutral-200 px-6 py-2.5 rounded-lg font-medium transition-colors">
            Browse Files
            <input
              type="file"
              className="hidden"
              accept=".zip,.pdf,.md,.txt"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
            />
          </label>
        </div>

        {file && (
          <div className="mt-6 p-4 bg-neutral-800 rounded-lg flex items-center justify-between border border-neutral-700">
            <div className="flex items-center gap-3">
              <FileUp className="w-5 h-5 text-indigo-400" />
              <div>
                <p className="font-medium text-sm text-neutral-200">
                  {file.name}
                </p>
                <p className="text-xs text-neutral-400">
                  {(file.size / 1024 / 1024).toFixed(2)} MB
                </p>
              </div>
            </div>

            <button
              onClick={handleUpload}
              disabled={status === "uploading"}
              className="px-4 py-2 bg-indigo-500 hover:bg-indigo-600 disabled:bg-indigo-500/50 text-white text-sm font-medium rounded-md transition-colors"
            >
              {status === "uploading" ? "Uploading..." : "Process File"}
            </button>
          </div>
        )}

        {status === "success" && (
          <div className="mt-4 p-4 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-lg flex items-center gap-2 text-sm">
            <CheckCircle className="w-4 h-4" />
            {message}
          </div>
        )}

        {status === "error" && (
          <div className="mt-4 p-4 bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg flex items-center gap-2 text-sm">
            <AlertCircle className="w-4 h-4" />
            {message}
          </div>
        )}
      </div>
    </div>
  );
}
