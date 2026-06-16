import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import MessageBubble from "./MessageBubble";
import type { ChatMsg } from "@/store/chat-store";
import { api } from "@/lib/api";

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

    expect(
      screen.getByText("Summarize my uploaded report"),
    ).toBeInTheDocument();
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
    expect(container.querySelector("pre")).toHaveTextContent(
      "const ok = true;",
    );
    expect(screen.getByLabelText("Copy response")).toBeInTheDocument();
    expect(screen.getByLabelText("Share response")).toBeInTheDocument();
  });

  it("copies assistant message content to clipboard when copy button is clicked", () => {
    const content = "This is some assistant response text";
    render(<MessageBubble message={makeMessage({ content })} />);

    fireEvent.click(screen.getByLabelText("Copy response"));

    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(content);
    expect(screen.getByLabelText("Copied")).toBeInTheDocument();
  });

  it("shares assistant message via API and copies share link to clipboard", async () => {
    vi.mocked(api.post).mockResolvedValueOnce({
      message_id: "msg-1",
      share_url: "/shared/abc-123",
    });

    render(
      <MessageBubble
        message={makeMessage({ content: "Share this content" })}
      />,
    );

    fireEvent.click(screen.getByLabelText("Share response"));

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith("/api/v1/chat/share/msg-1");
    });

    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
      "http://localhost:3000/shared/abc-123",
    );
  });
});
