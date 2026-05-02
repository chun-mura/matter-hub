import * as Dialog from "@radix-ui/react-dialog";
import { useEffect, useState } from "react";

type Props = {
  open: boolean;
  initialValue: string;
  onClose: () => void;
  onSave: (text: string) => Promise<void>;
};

export function SummaryEditModal({ open, initialValue, onClose, onSave }: Props) {
  const [value, setValue] = useState(initialValue);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) setValue(initialValue);
  }, [open, initialValue]);

  const handleSave = async () => {
    setSaving(true);
    try {
      await onSave(value);
      onClose();
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog.Root open={open} onOpenChange={(o) => { if (!o) onClose(); }}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-modal bg-black/50 dark:bg-black/60" />
        <Dialog.Content
          className="fixed left-1/2 top-1/2 z-modal w-full max-w-2xl -translate-x-1/2 -translate-y-1/2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 shadow-xl p-5 sm:p-6 focus:outline-none"
          onEscapeKeyDown={onClose}
        >
          <Dialog.Title className="text-base font-semibold text-gray-900 dark:text-gray-100">
            {initialValue ? "要約を編集" : "要約を手動入力"}
          </Dialog.Title>
          <Dialog.Description className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            {initialValue ? "内容を編集して保存してください。" : "要約テキストを入力してください。"}
          </Dialog.Description>
          <textarea
            className="mt-3 w-full rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-sm text-gray-800 dark:text-gray-100 p-2.5 resize-y min-h-[200px] focus:outline-none focus:ring-2 focus:ring-action-primary"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            disabled={saving}
            aria-label="要約テキスト"
          />
          <div className="mt-4 flex flex-wrap justify-end gap-2">
            <button
              type="button"
              className="px-3 py-1.5 rounded text-sm border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-100 hover:bg-gray-50 dark:hover:bg-gray-700/50"
              onClick={onClose}
              disabled={saving}
            >
              キャンセル
            </button>
            <button
              type="button"
              className="px-3 py-1.5 rounded text-sm bg-action-primary hover:bg-action-primary-hover text-white font-medium disabled:opacity-70"
              onClick={() => void handleSave()}
              disabled={saving || !value.trim()}
            >
              {saving ? "保存中…" : "保存"}
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
