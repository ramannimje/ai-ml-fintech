import { useState } from 'react';
import type { AlertCommodity, AlertDirection, AlertType, Region } from '../types/api';

const alertCommodities: AlertCommodity[] = ['gold', 'silver', 'crude_oil', 'natural_gas', 'copper'];
const alertTypes: AlertType[] = ['above', 'below', 'pct_change_24h', 'spike', 'drop'];

interface AlertWizardProps {
  region: Region;
  defaultCooldownMinutes: number;
  defaultEmailEnabled: boolean;
  onCreate: (input: {
    channel: 'email' | 'whatsapp';
    commodity: AlertCommodity;
    region: Region;
    alert_type: AlertType;
    threshold: number;
    enabled: boolean;
    cooldown_minutes: number;
    email_notifications_enabled: boolean;
    whatsapp_number?: string;
    direction?: AlertDirection;
  }) => void;
  onValidationError?: (message: string) => void;
  pending?: boolean;
}

export function AlertWizard({
  region,
  defaultCooldownMinutes,
  defaultEmailEnabled,
  onCreate,
  onValidationError,
  pending = false,
}: AlertWizardProps) {
  const [commodity, setCommodity] = useState<AlertCommodity>('gold');
  const [alertType, setAlertType] = useState<AlertType>('above');
  const [threshold, setThreshold] = useState<string>('1');
  const [channel, setChannel] = useState<'email' | 'whatsapp'>('email');
  const [whatsappNumber, setWhatsappNumber] = useState<string>('');
  const [cooldownMinutes, setCooldownMinutes] = useState<string>(String(defaultCooldownMinutes));
  const [enabled, setEnabled] = useState(true);
  const [emailEnabled, setEmailEnabled] = useState(defaultEmailEnabled);

  const submit = () => {
    const parsedThreshold = Number(threshold);
    const parsedCooldown = Number(cooldownMinutes);
    if (!Number.isFinite(parsedThreshold) || parsedThreshold <= 0) {
      onValidationError?.('Threshold must be greater than 0.');
      return;
    }
    if (!Number.isFinite(parsedCooldown) || parsedCooldown < 5) {
      onValidationError?.('Cooldown must be at least 5 minutes.');
      return;
    }
    if (channel === 'whatsapp') {
      if (!whatsappNumber.trim()) {
        onValidationError?.('WhatsApp number is required for WhatsApp alerts.');
        return;
      }
      if (!whatsappNumber.trim().startsWith('+')) {
        onValidationError?.('WhatsApp number must be in E.164 format (example: +15551234567).');
        return;
      }
      if (!(alertType === 'above' || alertType === 'below')) {
        onValidationError?.('WhatsApp alerts currently support only above/below conditions.');
        return;
      }
    }
    onCreate({
      channel,
      commodity,
      region,
      alert_type: alertType,
      threshold: parsedThreshold,
      enabled,
      cooldown_minutes: parsedCooldown,
      email_notifications_enabled: emailEnabled,
      whatsapp_number: channel === 'whatsapp' ? whatsappNumber.trim() : undefined,
      direction: channel === 'whatsapp' ? (alertType as AlertDirection) : undefined,
    });
  };

  return (
    <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
      <select value={commodity} onChange={(e) => setCommodity(e.target.value as AlertCommodity)} className="ui-input rounded px-3 py-2 text-sm">
        {alertCommodities.map((item) => <option key={item} value={item}>{item.replace('_', ' ')}</option>)}
      </select>
      <select value={alertType} onChange={(e) => setAlertType(e.target.value as AlertType)} className="ui-input rounded px-3 py-2 text-sm">
        {alertTypes.map((item) => <option key={item} value={item}>{item}</option>)}
      </select>
      <select
        value={channel}
        onChange={(e) => setChannel(e.target.value as 'email' | 'whatsapp')}
        className="ui-input rounded px-3 py-2 text-sm"
      >
        <option value="email">Email</option>
        <option value="whatsapp">WhatsApp</option>
      </select>
      <input
        value={threshold}
        onChange={(e) => setThreshold(e.target.value)}
        type="number"
        min="0"
        className="ui-input rounded px-3 py-2 text-sm"
        placeholder="Threshold"
      />
      <input
        value={cooldownMinutes}
        onChange={(e) => setCooldownMinutes(e.target.value)}
        type="number"
        min="5"
        className="ui-input rounded px-3 py-2 text-sm"
        placeholder="Cooldown (min)"
      />
      {channel === 'whatsapp' ? (
        <input
          value={whatsappNumber}
          onChange={(e) => setWhatsappNumber(e.target.value)}
          className="ui-input rounded px-3 py-2 text-sm sm:col-span-2"
          placeholder="WhatsApp number (+15551234567)"
        />
      ) : null}
      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />
        Alert enabled
      </label>
      {channel === 'email' ? (
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={emailEnabled} onChange={(e) => setEmailEnabled(e.target.checked)} />
          Email notifications
        </label>
      ) : (
        <div className="text-muted text-xs sm:self-center">WhatsApp alerts are sent to the number above.</div>
      )}
      <button
        type="button"
        onClick={submit}
        disabled={pending}
        className="rounded bg-sky-600 px-3 py-2 text-sm font-medium text-white hover:bg-sky-700 disabled:opacity-60 sm:col-span-2"
      >
        {pending ? 'Saving...' : 'Create Alert'}
      </button>
    </div>
  );
}
