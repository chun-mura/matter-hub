type Props = {
  message: string | null;
};

export function Toast({ message }: Props) {
  if (!message) return null;
  return (
    <div
      role="status"
      aria-live="polite"
      className="fixed bottom-4 right-4 z-modal px-4 py-2 rounded-lg bg-gray-800 dark:bg-gray-700 text-white text-sm shadow-lg"
    >
      {message}
    </div>
  );
}
