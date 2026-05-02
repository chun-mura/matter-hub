import * as Dialog from "@radix-ui/react-dialog";
import { useState } from "react";

type Props = {
  open: boolean;
  onClose: () => void;
  onSubmit: (text: string) => Promise<void>;
};

export function SummarizeWithTextModal({ open, onClose, onSubmit }: Props) {
  const [value, setValue] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleOpenChange = (o: boolean) => {
    if (!o && !submitting) onClose();
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      await onSubmit(value);
    } finally {
      setSubmitting(false);
    }
    setValue("");
    onClose();
  };

  return (
    <Dialog.Root open={open} onOpenChange={handleOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-modal bg-black/50 dark:bg-black/60" />
        <Dialog.Content
          className="fixed left-1/2 top-1/2 z-modal w-full max-w-2xl -translate-x-1/2 -translate-y-1/2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 shadow-xl p-5 sm:p-6 focus:outline-none"
          onEscapeKeyDown={() => { if (!submitting) onClose(); }}
        >
          <Dialog.Title className="text-base font-semibold text-gray-900 dark:text-gray-100">
            本文を貼り付けて要約
          </Dialog.Title>
          <Dialog.Description className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            記事本文をコピーして貼り付けてください。Ollama で日本語要約を生成します（X など直接取得できない記事に使用できます）。
          </Dialog.Description>
          <textarea
            className="mt-3 w-full rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-sm text-gray-800 dark:text-gray-100 p-2.5 resize-y min-h-[240px] focus:outline-none focus:ring-2 focus:ring-action-primary"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            disabled={submitting}
            placeholder="ここに記事本文を貼り付けてください…"
            aria-label="記事本文"
          />
          <div className="mt-4 flex flex-wrap justify-end gap-2">
            <button
              type="button"
              className="px-3 py-1.5 rounded text-sm border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-100 hover:bg-gray-50 dark:hover:bg-gray-700/50 disabled:opacity-50"
              onClick={onClose}
              disabled={submitting}
            >
              キャンセル
            </button>
            <button
              type="button"
              className="px-3 py-1.5 rounded text-sm bg-action-primary hover:bg-action-primary-hover text-white font-medium disabled:opacity-70"
              onClick={() => void handleSubmit()}
              disabled={submitting || !value.trim()}
            >
              {submitting ? "送信中…" : "要約を生成"}
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
