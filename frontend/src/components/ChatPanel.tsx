import { useChatPanel } from '../hooks/useChatPanel'
import { ChatConversation } from './chat/ChatConversation'
import { ChatSidebar } from './chat/ChatSidebar'

export default function ChatPanel() {
  const panel = useChatPanel()
  return (
    <div className="flex gap-6 h-[calc(100vh-7rem)] animate-fade-up">
      <ChatConversation panel={panel} />
      <ChatSidebar panel={panel} />
    </div>
  )
}
