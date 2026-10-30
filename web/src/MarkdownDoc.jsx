import { useEffect, useId, useRef } from "react";
import ReactMarkdown from "react-markdown";
import { Link } from "react-router-dom";
import mermaid from "mermaid";

import { rewriteAboutHref } from "./aboutDocs.js";

mermaid.initialize({
  startOnLoad: false,
  theme: "dark",
  securityLevel: "strict",
  fontFamily: "Barlow, Arial Narrow, Arial, sans-serif",
});

/**
 * Renders repo markdown (About pages, workflow doc) with Mermaid support.
 * @param {{ markdown: string, className?: string }} props
 */
export function MarkdownDoc({ markdown, className = "about-doc" }) {
  const rootRef = useRef(null);
  const renderId = useId().replace(/:/g, "");

  useEffect(() => {
    const root = rootRef.current;
    if (!root) return undefined;
    const nodes = root.querySelectorAll(".mermaid");
    if (nodes.length === 0) return undefined;
    let cancelled = false;
    mermaid
      .run({ nodes })
      .catch((error) => {
        if (!cancelled) console.error("Mermaid render failed", error);
      });
    return () => {
      cancelled = true;
    };
  }, [markdown, renderId]);

  return (
    <div className={className} ref={rootRef}>
      <ReactMarkdown
        components={{
          a({ href, children }) {
            const next = rewriteAboutHref(href ?? "");
            if (next.startsWith("/")) {
              return <Link to={next}>{children}</Link>;
            }
            return (
              <a href={next} rel={next.startsWith("http") ? "noreferrer" : undefined}>
                {children}
              </a>
            );
          },
          code({ className: codeClass, children, ...props }) {
            const text = String(children).replace(/\n$/, "");
            const isMermaid = /language-mermaid/.test(codeClass ?? "");
            if (isMermaid) {
              return (
                <div className="mermaid-wrap">
                  <pre className="mermaid" key={`${renderId}-${text.slice(0, 24)}`}>
                    {text}
                  </pre>
                </div>
              );
            }
            const inline = !String(children).includes("\n");
            if (inline) {
              return (
                <code className={codeClass} {...props}>
                  {children}
                </code>
              );
            }
            return (
              <pre>
                <code className={codeClass} {...props}>
                  {children}
                </code>
              </pre>
            );
          },
        }}
      >
        {markdown}
      </ReactMarkdown>
    </div>
  );
}
