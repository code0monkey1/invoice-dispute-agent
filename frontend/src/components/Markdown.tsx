import ReactMarkdown, { type Components } from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkBreaks from 'remark-breaks'

// Raw HTML is never parsed (no rehype-raw) and react-markdown's default
// urlTransform strips unsafe schemes like javascript:, so model output
// can't inject markup or script. Images are never loaded: model output
// can be steered by client replies, and an auto-loaded image URL could
// leak invoice data to a third party. Only the alt text is shown.
const components: Components = {
  p: ({ children }) => <p className="my-2 first:mt-0 last:mb-0">{children}</p>,
  strong: ({ children }) => <strong className="font-semibold text-gray-900">{children}</strong>,
  em: ({ children }) => <em className="italic">{children}</em>,
  h1: ({ children }) => <h1 className="text-base font-bold text-gray-900 mt-3 mb-2 first:mt-0">{children}</h1>,
  h2: ({ children }) => <h2 className="text-[15px] font-bold text-gray-900 mt-3 mb-2 first:mt-0">{children}</h2>,
  h3: ({ children }) => <h3 className="text-sm font-bold text-gray-900 mt-3 mb-1.5 first:mt-0">{children}</h3>,
  h4: ({ children }) => <h4 className="text-sm font-semibold text-gray-900 mt-2 mb-1 first:mt-0">{children}</h4>,
  ul: ({ children }) => <ul className="list-disc pl-5 my-2 space-y-1">{children}</ul>,
  ol: ({ children }) => <ol className="list-decimal pl-5 my-2 space-y-1">{children}</ol>,
  li: ({ children }) => <li className="pl-0.5">{children}</li>,
  blockquote: ({ children }) => (
    <blockquote className="border-l-2 border-orange-200 pl-3 my-2 text-gray-600">{children}</blockquote>
  ),
  img: ({ alt }) => (alt ? <span className="italic text-gray-500">[{alt}]</span> : null),
  hr: () => <hr className="my-3 border-gray-100" />,
  a: ({ href, children }) => (
    <a href={href} target="_blank" rel="noopener noreferrer" className="text-[#FF6B35] underline underline-offset-2 hover:text-[#e55a2b]">
      {children}
    </a>
  ),
  pre: ({ children }) => (
    <pre className="my-2 overflow-x-auto rounded-lg bg-gray-50 border border-gray-100 p-3 text-[13px] font-mono">{children}</pre>
  ),
  code: ({ className, children }) => (
    <code className={className ?? 'rounded bg-gray-100 px-1 py-0.5 text-[13px] font-mono text-gray-800'}>{children}</code>
  ),
  table: ({ children }) => (
    <div className="my-2 max-w-full overflow-x-auto rounded-lg border border-gray-100">
      <table className="w-full border-collapse text-[13px]">{children}</table>
    </div>
  ),
  thead: ({ children }) => <thead className="bg-gray-50">{children}</thead>,
  th: ({ children }) => (
    <th className="px-3 py-2 text-left font-semibold text-gray-700 border-b border-gray-100 whitespace-nowrap">{children}</th>
  ),
  td: ({ children }) => <td className="px-3 py-2 align-top border-b border-gray-50">{children}</td>,
}

export default function Markdown({ children }: { children: string }) {
  return (
    <div className="break-words">
      <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]} components={components}>
        {children}
      </ReactMarkdown>
    </div>
  )
}
