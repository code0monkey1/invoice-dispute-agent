"""Inbound reply routing is application logic, independent of FastAPI."""


class Store:
    def __init__(self, invoice=None):
        self.invoice = invoice
        self.communications = []

    def get_invoice_by_reply_token(self, token):
        return self.invoice if token == "known" else None

    def add_communication(self, **fields):
        self.communications.append(fields)
        return fields


def event(sender="Sam <ap@acme.example>"):
    return {"type": "email.received", "data": {
        "email_id": "em-1", "from": sender,
        "to": ["inv-known@example.test"], "cc": [], "subject": "Re: invoice",
    }}


def build(store, fetched):
    from src.usecases.inbound_reply import InboundReplyUseCases

    return InboundReplyUseCases(
        invoices=store,
        communications=store,
        fetch_email=lambda email_id: fetched.append(email_id) or {"text": "Paying Friday"},
        parse_token=lambda recipients: "known" if recipients else None,
        plain_text=lambda message: message["text"],
        inbound_domain=lambda: "example.test",
        new_token=lambda: "new-token",
    )


def test_unknown_reply_token_is_ignored_without_fetching_content():
    fetched = []
    usecases = build(Store(), fetched)

    assert usecases.process(event(), lambda *_args: None) == "ignored"
    assert fetched == []


def test_only_the_invoice_client_can_trigger_the_agent():
    invoice = {"id": "inv-1", "user_id": "u1", "client_email": "ap@acme.example"}
    store, fetched, handled = Store(invoice), [], []
    usecases = build(store, fetched)

    status = usecases.process(event("Mallory <mallory@evil.example>"), lambda *args: handled.append(args))

    assert status == "stored_unverified"
    assert handled == []
    assert store.communications[0]["comm_type"] == "client_reply_unverified"


def test_verified_client_reply_is_delegated_after_fetching_the_body():
    invoice = {"id": "inv-1", "user_id": "u1", "client_email": "ap@acme.example"}
    store, fetched, handled = Store(invoice), [], []
    usecases = build(store, fetched)

    status = usecases.process(event(), lambda *args: handled.append(args))

    assert status == "stored"
    assert fetched == ["em-1"]
    assert handled == [(invoice, "Sam <ap@acme.example>", "Re: invoice", "Paying Friday")]
