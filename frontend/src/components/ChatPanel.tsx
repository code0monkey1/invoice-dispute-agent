import { useChatPanel } from '../hooks/useChatPanel'
import { ChatConversation } from './chat/ChatConversation'
import { ChatSidebar } from './chat/ChatSidebar'

export default function ChatPanel() {
  const panel = useChatPanel()
  return (
    <div className="flex flex-col lg:flex-row gap-6 lg:h-[calc(100dvh-7rem)] animate-fade-up">
      <ChatConversation panel={panel} />
      <ChatSidebar panel={panel} />
    </div>
  )
}
