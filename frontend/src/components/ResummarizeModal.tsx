import { ConfirmModal } from "./ui/ConfirmModal";

type Props = {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void | Promise<void>;
};

export function ResummarizeModal({ open, onClose, onConfirm }: Props) {
  return (
    <ConfirmModal
      open={open}
      onClose={onClose}
      onConfirm={onConfirm}
      title="再要約の確認"
      description={
        <>
          承認するとすぐに再要約が始まります。実行中は
          <strong className="font-medium text-gray-800 dark:text-gray-200">
            画面上の既存の要約は進捗表示に置き換わり
          </strong>
          、完了すると新しい要約で上書きされます。取り消しはできません。
        </>
      }
      confirmLabel="再要約を開始"
      variant="primary"
    />
  );
}
