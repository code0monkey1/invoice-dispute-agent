import { Bot, User, Wrench } from 'lucide-react'
import type { Message } from '../types'

export default function MessageBubble({ message }: { message: Message }) {
  const isUser = message.type === 'HumanMessage'
  const isTool = message.type === 'ToolMessage'
  const isAI = message.type === 'AIMessage'

  // Tool call trigger (no content, just calling tools)
  if (isAI && !message.content && message.tool_calls?.length) {
    return (
      <div className="flex items-center gap-2 text-xs text-gray-400 py-1.5 px-5 font-medium">
        <div className="w-5 h-5 rounded-md bg-violet-50 flex items-center justify-center">
          <Wrench className="w-3 h-3 text-violet-400" />
        </div>
        Using {message.tool_calls.map(tc => (
          <span key={tc.name} className="text-violet-500 font-semibold">{tc.name}</span>
        ))}...
      </div>
    )
  }

  if (!message.content) return null

  // Tool result
  if (isTool) {
    return (
      <div className="mx-5 my-2">
        <div className="bg-gradient-to-br from-violet-50/80 to-purple-50/50 border border-violet-100 rounded-xl px-4 py-3 text-xs">
          <div className="flex items-center gap-1.5 text-violet-500 mb-2 font-semibold uppercase tracking-wider text-[10px]">
            <Wrench className="w-3 h-3" />
            {message.name || 'Tool Result'}
          </div>
          <pre className="text-gray-600 whitespace-pre-wrap font-mono leading-relaxed text-[13px]">
            {message.content}
          </pre>
        </div>
      </div>
    )
  }

  // User / AI message
  return (
    <div className={`flex gap-3 px-5 py-3 ${isUser ? 'justify-end' : ''}`}>
      {!isUser && (
        <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-[#FF6B35] to-[#FF8F65] flex items-center justify-center flex-shrink-0 mt-0.5 shadow-md shadow-orange-200/40">
          <Bot className="w-4 h-4 text-white" />
        </div>
      )}
      <div className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
        isUser
          ? 'bg-gradient-to-br from-[#FF6B35] to-[#FF8F65] text-white shadow-md shadow-orange-200/30 rounded-br-md'
          : 'bg-white text-gray-700 border border-gray-100 shadow-sm rounded-bl-md'
      }`}>
        <p className="whitespace-pre-wrap">{message.content}</p>
      </div>
      {isUser && (
        <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-teal-500 to-emerald-500 flex items-center justify-center flex-shrink-0 mt-0.5 shadow-md shadow-teal-200/40">
          <User className="w-4 h-4 text-white" />
        </div>
      )}
    </div>
  )
}
