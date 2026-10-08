import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import "./markdown.css";

export function Markdown({ children }: { children: string }) {
  return (
    <div className="markdown-content">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        skipHtml
        components={{
          a: ({ href, children: label }) => (
            <a href={href} target="_blank" rel="noopener noreferrer">
              {label}
            </a>
          ),
          // Notes must not silently contact remote image hosts when reviewed.
          img: ({ alt }) => (
            <span className="markdown-image-placeholder">
              [图片：{alt || "未命名"}]
            </span>
          ),
          table: ({ children: rows }) => (
            <div className="markdown-table-scroll">
              <table>{rows}</table>
            </div>
          ),
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}

export default Markdown;
