import * as Dialog from "@radix-ui/react-dialog";

type Props = {
  open: boolean;
  title: string;
  description: React.ReactNode;
  confirmLabel: string;
  cancelLabel?: string;
  variant?: "danger" | "primary";
  onClose: () => void;
  onConfirm: () => void | Promise<void>;
};

export function ConfirmModal({
  open,
  title,
  description,
  confirmLabel,
  cancelLabel = "キャンセル",
  variant = "primary",
  onClose,
  onConfirm,
}: Props) {
  return (
    <Dialog.Root open={open} onOpenChange={(o) => { if (!o) onClose(); }}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-modal bg-black/50 dark:bg-black/60" />
        <Dialog.Content
          className="fixed left-1/2 top-1/2 z-modal w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 shadow-xl p-5 sm:p-6 focus:outline-none"
          onEscapeKeyDown={onClose}
        >
          <Dialog.Title className="text-base font-semibold text-gray-900 dark:text-gray-100">
            {title}
          </Dialog.Title>
          <Dialog.Description className="mt-3 text-sm text-gray-600 dark:text-gray-300 leading-relaxed">
            {description}
          </Dialog.Description>
          <div className="mt-5 flex flex-wrap justify-end gap-2">
            <button
              type="button"
              className="px-3 py-1.5 rounded text-sm border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-100 hover:bg-gray-50 dark:hover:bg-gray-700/50"
              onClick={onClose}
            >
              {cancelLabel}
            </button>
            <button
              type="button"
              className={
                variant === "danger"
                  ? "px-3 py-1.5 rounded text-sm bg-action-danger hover:bg-action-danger-hover text-white font-medium"
                  : "px-3 py-1.5 rounded text-sm bg-action-primary hover:bg-action-primary-hover text-white font-medium"
              }
              onClick={() => void Promise.resolve(onConfirm())}
            >
              {confirmLabel}
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
