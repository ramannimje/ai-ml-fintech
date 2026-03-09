import type { AIProviderStatus, Commodity, Region } from '../../types/api';
import { formatCommodity, formatRegion } from './format';

function ProviderBadge({ status }: { status?: AIProviderStatus }) {
  if (!status) {
    return <span className="assistant-badge">Provider: Checking</span>;
  }

  const unavailable = !status.openrouter_api_key_present || status.provider === 'disabled' || status.openrouter_cooldown_seconds_remaining > 0;
  return (
    <span className={`assistant-badge ${unavailable ? 'assistant-down' : 'assistant-up'}`}>
      {unavailable ? 'Fallback Mode' : 'OpenRouter Live'}
    </span>
  );
}

export function AssistantHeader({
  region,
  commodity,
  provider,
  onClear,
  asOf,
}: {
  region: Region;
  commodity: Commodity;
  provider?: AIProviderStatus;
  onClear: () => void;
  asOf?: string;
}) {
  return (
    <header className="assistant-panel p-4 md:p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="shell-title">AI Market Intelligence Assistant</h1>
          <p className="shell-subtitle">
            {formatCommodity(commodity)} desk for {formatRegion(region)} with live price + model context.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <ProviderBadge status={provider} />
          {asOf ? <span className="assistant-badge">Refreshed {asOf}</span> : null}
          <button type="button" className="btn-ghost" onClick={onClear}>
            Clear Context
          </button>
        </div>
      </div>
      {provider?.last_openrouter_error ? (
        <p className="mt-3 rounded-lg border px-3 py-2 text-xs" style={{ borderColor: 'color-mix(in srgb, var(--danger) 35%, var(--assistant-border))', color: 'var(--danger)' }}>
          Provider note: {provider.last_openrouter_error}
        </p>
      ) : null}
    </header>
  );
}
