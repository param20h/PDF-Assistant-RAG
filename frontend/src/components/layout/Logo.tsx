import React from "react";

interface LogoProps {
  className?: string;
  size?: number;
}

export default function Logo({ className = "w-7 h-7", size = 28 }: LogoProps) {
  return (
    <div
      className={`relative flex items-center justify-center shrink-0 rounded-lg bg-gradient-to-br from-indigo-500 via-primary to-cyan-400 p-[1.5px] shadow-sm shadow-primary/25 overflow-hidden group ${className}`}
      style={{ width: size, height: size }}
      aria-hidden="true"
    >
      <div className="w-full h-full bg-card rounded-[7px] flex items-center justify-center overflow-hidden">
        <svg
          viewBox="0 0 24 24"
          fill="none"
          className="w-4/5 h-4/5 text-primary transition-transform duration-300 group-hover:scale-105"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <defs>
            <linearGradient id="docAiGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#6366f1" />
              <stop offset="50%" stopColor="#3b82f6" />
              <stop offset="100%" stopColor="#06b6d4" />
            </linearGradient>
          </defs>
          <path
            d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"
            fill="url(#docAiGradient)"
            fillOpacity="0.2"
            stroke="url(#docAiGradient)"
          />
          <polyline points="14 2 14 8 20 8" stroke="url(#docAiGradient)" />
          <path d="M8 13h8" stroke="currentColor" strokeWidth="1.75" />
          <path d="M8 17h5" stroke="currentColor" strokeWidth="1.75" />
          <circle cx="16" cy="17" r="1.25" fill="currentColor" stroke="none" />
        </svg>
      </div>
    </div>
  );
}
