import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import SourceCard from "./SourceCard";
import type { SourceChunk } from "@/store/chat-store";

const sources: SourceChunk[] = [
  {
    filename: "annual-report.pdf",
    page: 2,
    text: "Revenue increased after the new pricing plan rolled out.",
    score: 0.91,
    confidence: 0.76,
    highlightRects: [{ left: 10, top: 20, width: 30, height: 40 }],
  },
  {
    filename: "board-notes.pdf",
    page: 4,
    text: "Risk review notes mention customer concentration and renewal timing.",
    score: 0.42,
  },
];

describe("SourceCard", () => {
  it("renders a collapsed source summary and forwards page clicks", async () => {
    const onPageClick = vi.fn();
    const user = userEvent.setup();

    render(<SourceCard sources={sources} onPageClick={onPageClick} />);

    expect(
      screen.getByRole("button", { name: "Expand 2 cited sources" }),
    ).toBeInTheDocument();
    expect(screen.getByText("2 sources cited")).toBeInTheDocument();
    expect(
      screen.getByLabelText("Go to source page 3. Confidence Medium"),
    ).toHaveTextContent("p.3 - Medium");
    expect(
      screen.getByLabelText("Go to source page 5. Confidence Low"),
    ).toHaveTextContent("p.5 - Low");

    await user.click(
      screen.getByLabelText("Go to source page 3. Confidence Medium"),
    );

    expect(onPageClick).toHaveBeenCalledWith({
      page: 3,
      highlightRects: sources[0].highlightRects,
    });
  });

  it("expands to show source metadata and excerpts", async () => {
    const user = userEvent.setup();

    render(<SourceCard sources={sources} onPageClick={vi.fn()} />);

    await user.click(screen.getByRole("button", { name: "Expand 2 cited sources" }));

    expect(
      screen.getByRole("button", { name: "Collapse 2 cited sources" }),
    ).toBeInTheDocument();
    expect(screen.getByText("annual-report.pdf")).toBeInTheDocument();
    expect(screen.getByText("Page 3")).toBeInTheDocument();
    expect(screen.getByText("Score: High")).toBeInTheDocument();
    expect(screen.getByText("Confidence: Medium")).toBeInTheDocument();
    expect(
      screen.getByText("Revenue increased after the new pricing plan rolled out."),
    ).toBeInTheDocument();
  });

  it("does not render when there are no sources", () => {
    const { container } = render(
      <SourceCard sources={[]} onPageClick={vi.fn()} />,
    );

    expect(container).toBeEmptyDOMElement();
  });
});
