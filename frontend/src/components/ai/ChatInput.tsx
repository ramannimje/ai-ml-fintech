import { useState } from 'react';

export function ChatInput({
  disabled,
  onSend,
}: {
  disabled?: boolean;
  onSend: (message: string) => Promise<void> | void;
}) {
  const [value, setValue] = useState('');

  const submit = async () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    setValue('');
    await onSend(trimmed);
  };

  return (
    <div className="panel rounded-2xl p-3">
      <div className="flex items-end gap-2">
        <textarea
          value={value}
          onChange={(event) => setValue(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault();
              void submit();
            }
          }}
          placeholder="Ask about trends, forecasts, regional comparisons, or signals..."
          rows={3}
          className="ui-input min-h-[86px] flex-1 resize-none"
          disabled={disabled}
        />
        <button type="button" onClick={() => void submit()} disabled={disabled || !value.trim()} className="btn-primary h-[42px] min-w-[96px]">
          Send
        </button>
      </div>
      <p className="mt-2 text-xs text-muted">Press Enter to send, Shift+Enter for a new line.</p>
    </div>
  );
}

