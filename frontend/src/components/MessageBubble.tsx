import { Bot, User, Wrench, Mail } from 'lucide-react'
import type { Message } from '../types'
import Markdown from './Markdown'

function messageText(content: unknown): string {
  if (content == null) return ''
  if (typeof content === 'string') return content
  if (Array.isArray(content)) {
    return content
      .map((part) => {
        if (typeof part === 'string') return part
        if (part && typeof part === 'object') {
          const record = part as Record<string, unknown>
          return String(record.text ?? record.content ?? JSON.stringify(record))
        }
        return String(part)
      })
      .filter(Boolean)
      .join('\n')
  }
  if (typeof content === 'object') {
    const record = content as Record<string, unknown>
    return String(record.text ?? record.content ?? JSON.stringify(record))
  }
  return String(content)
}

export default function MessageBubble({ message }: { message: Message }) {
  const isUser = message.type === 'HumanMessage'
  const isTool = message.type === 'ToolMessage'
  const isAI = message.type === 'AIMessage'
  const content = messageText(message.content)

  // Tool call trigger (no content, just calling tools)
  if (isAI && !content && message.tool_calls?.length) {
    return (
      <div className="flex items-center gap-2 text-xs text-gray-400 py-1.5 px-5 font-medium">
        <div className="w-5 h-5 rounded-md bg-tint flex items-center justify-center">
          <Wrench className="w-3 h-3 text-muted" />
        </div>
        Using {message.tool_calls.map(tc => (
          <span key={tc.name} className="text-body font-semibold">{tc.name}</span>
        ))}...
      </div>
    )
  }

  if (!content) return null

  // Inbound client email reply
  const isInboundEmail = content.startsWith('[INCOMING CLIENT REPLY]')
  if (isInboundEmail) {
    const lines = content.split('\n')
    const fromLine = lines.find(l => l.startsWith('From:'))?.replace('From:', '').trim() || ''
    const subjectLine = lines.find(l => l.startsWith('Subject:'))?.replace('Subject:', '').trim() || ''
    const bodyStart = lines.findIndex(l => l === '')
    const rawBody = bodyStart >= 0 ? lines.slice(bodyStart + 1).join('\n').trim() : ''
    const bodyText = rawBody.replace(/\n*Please analyze this reply and suggest the appropriate next action\.?$/i, '').trim()

    return (
      <div className="flex justify-start px-5 mb-4">
        <div className="max-w-[75%] bg-white border border-line border-l-4 border-l-ink rounded-xl p-4 shadow-card">
          <div className="flex items-center gap-2 mb-2">
            <Mail className="w-4 h-4 text-ink" />
            <span className="text-xs font-semibold text-ink uppercase tracking-wider">Client reply</span>
          </div>
          {fromLine && <p className="text-xs text-gray-400 mb-1">From: {fromLine}</p>}
          {subjectLine && <p className="text-sm font-semibold text-gray-700 mb-2">{subjectLine}</p>}
          {bodyText && <p className="text-sm text-gray-600 whitespace-pre-wrap leading-relaxed">{bodyText}</p>}
        </div>
      </div>
    )
  }

  // Tool result
  if (isTool) {
    return (
      <div className="mx-5 my-2">
        <div className="bg-tint border border-line rounded-xl px-4 py-3 text-xs">
          <div className="flex items-center gap-1.5 text-body mb-2 font-semibold uppercase tracking-wider text-xs">
            <Wrench className="w-3 h-3" />
            {message.name || 'Tool Result'}
          </div>
          <pre className="text-gray-600 whitespace-pre-wrap font-mono leading-relaxed text-[13px]">
            {content}
          </pre>
        </div>
      </div>
    )
  }

  // User / AI message
  return (
    <div className={`flex gap-3 px-5 py-3 ${isUser ? 'justify-end' : ''}`}>
      {!isUser && (
        <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-coral to-coral-2 flex items-center justify-center flex-shrink-0 mt-0.5 shadow-card">
          <Bot className="w-4 h-4 text-ink" />
        </div>
      )}
      <div className={`max-w-[75%] min-w-0 rounded-xl px-4 py-3 text-sm leading-relaxed ${
        isUser
          ? 'bg-gradient-to-br from-coral to-coral-2 text-ink shadow-card rounded-br-md'
          : 'bg-white text-gray-700 border border-gray-100 shadow-card rounded-bl-md'
      }`}>
        {isAI ? <Markdown>{content}</Markdown> : <p className="whitespace-pre-wrap">{content}</p>}
      </div>
      {isUser && (
        <div className="w-8 h-8 rounded-xl bg-ink flex items-center justify-center flex-shrink-0 mt-0.5">
          <User className="w-4 h-4 text-white" />
        </div>
      )}
    </div>
  )
}
