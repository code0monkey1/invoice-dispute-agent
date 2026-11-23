export function SettleConfirmation({ loading, onConfirm, onCancel }: { loading: boolean; onConfirm: () => void; onCancel: () => void }) {
  return (
    <div className="rounded-xl border border-green/20 bg-green-bg p-3">
      <p className="text-xs text-body mb-2">Mark as settled? The agent stops all work on this invoice and won't send anything else.</p>
      <div className="flex gap-2">
        <button
          onClick={() => { onConfirm() }}
          disabled={loading}
          className="flex-1 rounded-lg bg-green hover:opacity-90 disabled:opacity-50 text-white text-xs font-bold py-2"
        >
          Yes, settled
        </button>
        <button
          onClick={() => onCancel()}
          className="flex-1 rounded-lg border border-gray-200 bg-white hover:bg-gray-50 text-body text-xs font-bold py-2"
        >
          Cancel
        </button>
      </div>
    </div>
  )

}
