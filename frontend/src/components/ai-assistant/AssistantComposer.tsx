import { useState } from 'react';
import { quickPrompts } from './constants';

export function AssistantComposer({
  disabled,
  onSend,
}: {
  disabled: boolean;
  onSend: (message: string) => Promise<void>;
}) {
  const [value, setValue] = useState('');

  const submit = async (message?: string) => {
    const next = (message ?? value).trim();
    if (!next || disabled) return;
    setValue('');
    await onSend(next);
  };

  return (
    <section className="assistant-panel p-3 md:p-4">
      <div className="mb-3 flex flex-wrap gap-2">
        {quickPrompts.map((prompt) => (
          <button key={prompt} type="button" className="assistant-chip text-left" disabled={disabled} onClick={() => void submit(prompt)}>
            {prompt}
          </button>
        ))}
      </div>
      <div className="flex flex-col gap-2 md:flex-row md:items-end">
        <textarea
          className="ui-input min-h-[120px] flex-1 resize-none md:min-h-[92px]"
          value={value}
          disabled={disabled}
          onChange={(event) => setValue(event.target.value)}
          placeholder="Ask for a precise, actionable investment view..."
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault();
              void submit();
            }
          }}
        />
        <button type="button" className="btn-primary h-[44px] w-full min-w-[132px] md:w-auto" disabled={disabled || !value.trim()} onClick={() => void submit()}>
          {disabled ? 'Streaming...' : 'Send'}
        </button>
      </div>
      <p className="mt-2 text-xs text-muted">Enter to send, Shift+Enter for new line.</p>
    </section>
  );
}
