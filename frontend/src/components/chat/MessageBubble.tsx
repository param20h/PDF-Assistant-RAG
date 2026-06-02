"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ChatMsg } from "./ChatPanel";
import { Brain, User, Volume2, VolumeX } from "lucide-react";
import { useState, useEffect } from "react";

interface Props {
  message: ChatMsg;
}

export default function MessageBubble({ message }: Props) {
  const isUser = message.role === "user";
  const [isSpeaking, setIsSpeaking] = useState(false);

  // Stop speaking when component unmounts
  useEffect(() => {
    return () => {
      window.speechSynthesis.cancel();
    };
  }, []);

  const toggleSpeech = () => {
    if (isSpeaking) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
    } else {
      const utterance = new SpeechSynthesisUtterance(message.content);
      utterance.onend = () => setIsSpeaking(false);
      utterance.onerror = () => setIsSpeaking(false);
      
      // Attempt to find a natural sounding voice
      const voices = window.speechSynthesis.getVoices();
      const preferredVoice = voices.find(v => v.lang.startsWith("en") && v.name.includes("Google")) || voices[0];
      if (preferredVoice) utterance.voice = preferredVoice;

      setIsSpeaking(true);
      window.speechSynthesis.speak(utterance);
    }
  };

  return (
    <div
      className={`flex gap-3 py-3 animate-fade-in-up ${isUser ? "justify-end" : "justify-start"}`}
    >
      {!isUser && (
        <div className="flex flex-col items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-primary/15 flex items-center justify-center shrink-0 mt-0.5">
            <Brain className="w-4 h-4 text-primary" />
          </div>
          <button
            onClick={toggleSpeech}
            className={`p-1.5 rounded-md transition-colors ${
              isSpeaking 
                ? "bg-primary text-primary-foreground" 
                : "bg-muted text-muted-foreground hover:bg-primary/20"
            }`}
            title={isSpeaking ? "Stop speaking" : "Read aloud"}
          >
            {isSpeaking ? (
              <VolumeX className="w-3.5 h-3.5" />
            ) : (
              <Volume2 className="w-3.5 h-3.5" />
            )}
          </button>
        </div>
      )}

      <div
        className={`max-w-[80%] rounded-xl px-4 py-3 ${
          isUser
            ? "bg-primary text-primary-foreground rounded-br-sm"
            : "bg-card border border-border/50 rounded-bl-sm"
        }`}
      >
        {isUser ? (
          <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
        ) : (
          <div className="prose-chat text-sm">
            {message.content ? (
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.content}
              </ReactMarkdown>
            ) : message.isStreaming ? (
              <div className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-primary/60 animate-bounce [animation-delay:0ms]" />
                <span className="w-1.5 h-1.5 rounded-full bg-primary/60 animate-bounce [animation-delay:150ms]" />
                <span className="w-1.5 h-1.5 rounded-full bg-primary/60 animate-bounce [animation-delay:300ms]" />
              </div>
            ) : null}
            {message.isStreaming && message.content && (
              <span className="inline-block w-0.5 h-4 bg-primary/60 animate-pulse ml-0.5 align-text-bottom" />
            )}
          </div>
        )}
      </div>

      {isUser && (
        <div className="w-8 h-8 rounded-lg bg-primary/20 flex items-center justify-center shrink-0 mt-0.5">
          <User className="w-4 h-4 text-primary-foreground" />
        </div>
      )}
    </div>
  );
}
