"""Resolve inbound-analysis placeholders before persisting the assistant reply."""
from langchain.agents.middleware import after_model
from langchain_core.messages import AIMessage

from src.domain.email_templates import fill_draft_from_context


@after_model
def fill_reply_details(state, runtime):
    if not getattr(runtime.context, "untrusted_input", False):
        return None
    messages = state.get("messages") or []
    if not messages or not isinstance(messages[-1], AIMessage) or messages[-1].tool_calls:
        return None
    message = messages[-1]

    def fill(text):
        return fill_draft_from_context(text, state, runtime.context) if "[" in text else text

    def fill_block(block):
        if isinstance(block, str):
            return fill(block)
        if block.get("type") == "text" and isinstance(block.get("text"), str):
            return {**block, "text": fill(block["text"])}
        return block

    if isinstance(message.content, str):
        content = fill(message.content)
    else:
        content = [fill_block(block) for block in message.content]
    if content == message.content:
        return None
    # Retain the message ID so add_messages replaces it, rather than adding a
    # second answer. Tool calls and their arguments never enter this formatter.
    return {"messages": [message.model_copy(update={"content": content})]}
