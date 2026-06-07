import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import MessageBubble from "./MessageBubble";
import type { ChatMsg } from "@/store/chat-store";

vi.mock("@/lib/api", () => ({
  api: {
    patch: vi.fn(),
    post: vi.fn(),
  },
}));

const makeMessage = (overrides: Partial<ChatMsg>): ChatMsg => ({
  id: "msg-1",
  role: "assistant",
  content: "Assistant response",
  sources: [],
  ...overrides,
});

describe("MessageBubble", () => {
  it("renders a user message without assistant actions", () => {
    render(
      <MessageBubble
        message={makeMessage({
          role: "user",
          content: "Summarize my uploaded report",
        })}
      />,
    );

    expect(screen.getByText("Summarize my uploaded report")).toBeInTheDocument();
    expect(screen.queryByText("Was this helpful?")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Copy response")).not.toBeInTheDocument();
  });

  it("renders an assistant message with markdown and response controls", () => {
    const { container } = render(
      <MessageBubble
        message={makeMessage({
          content: "Here is the answer:\n\n```ts\nconst ok = true;\n```",
        })}
      />,
    );

    expect(screen.getByText("Here is the answer:")).toBeInTheDocument();
    expect(container.querySelector("pre")).toHaveTextContent("const ok = true;");
    expect(screen.getByText("Was this helpful?")).toBeInTheDocument();
    expect(screen.getByLabelText("Copy response")).toBeInTheDocument();
    expect(screen.getByLabelText("Share response")).toBeInTheDocument();
    expect(screen.getByLabelText("Play speech")).toBeInTheDocument();
  });
});
