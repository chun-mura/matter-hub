type Props = {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void | Promise<void>;
};

export function ResummarizeModal({ open, onClose, onConfirm }: Props) {
  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[100]"
      role="dialog"
      aria-modal="true"
      aria-labelledby="resummarize-modal-title"
    >
      <button
        type="button"
        className="absolute inset-0 w-full h-full bg-black/50 dark:bg-black/60 border-0 cursor-default"
        aria-label="閉じる"
        onClick={onClose}
      />
      <div className="relative flex min-h-full items-center justify-center p-4 pointer-events-none">
        <div className="pointer-events-auto w-full max-w-md rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 shadow-xl p-5 sm:p-6">
          <h2
            id="resummarize-modal-title"
            className="text-base font-semibold text-gray-900 dark:text-gray-100"
          >
            再要約の確認
          </h2>
          <p className="mt-3 text-sm text-gray-600 dark:text-gray-300 leading-relaxed">
            承認するとすぐに再要約が始まります。実行中は
            <strong className="font-medium text-gray-800 dark:text-gray-200">
              画面上の既存の要約は進捗表示に置き換わり
            </strong>
            、完了すると新しい要約で上書きされます。取り消しはできません。
          </p>
          <div className="mt-5 flex flex-wrap justify-end gap-2">
            <button
              type="button"
              className="px-3 py-1.5 rounded text-sm border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-100 hover:bg-gray-50 dark:hover:bg-gray-700/50"
              onClick={onClose}
            >
              キャンセル
            </button>
            <button
              type="button"
              className="px-3 py-1.5 rounded text-sm bg-indigo-600 hover:bg-indigo-700 text-white font-medium"
              onClick={() => void Promise.resolve(onConfirm())}
            >
              再要約を開始
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
