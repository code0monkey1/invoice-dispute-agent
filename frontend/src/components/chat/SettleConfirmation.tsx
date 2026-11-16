export function SettleConfirmation({ loading, onConfirm, onCancel }: { loading: boolean; onConfirm: () => void; onCancel: () => void }) {
  return (
    <div className="rounded-xl border border-emerald-200 bg-emerald-50/60 p-3">
      <p className="text-xs text-gray-700 mb-2">Mark as settled? The agent stops all work on this invoice and won't send anything else.</p>
      <div className="flex gap-2">
        <button
          onClick={() => { onConfirm() }}
          disabled={loading}
          className="flex-1 rounded-lg bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white text-xs font-bold py-2"
        >
          Yes, settled
        </button>
        <button
          onClick={() => onCancel()}
          className="flex-1 rounded-lg border border-gray-200 bg-white hover:bg-gray-50 text-gray-700 text-xs font-bold py-2"
        >
          Cancel
        </button>
      </div>
    </div>
  )

}
