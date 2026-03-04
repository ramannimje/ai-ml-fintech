import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { SettingsPage } from './settings';

vi.mock('../api/client', () => ({
  client: {
    getUserSettings: vi.fn(async () => ({
      id: 1,
      user_id: 'test-user',
      default_region: 'us',
      default_commodity: 'gold',
      prediction_horizon: 30,
      email_notifications: true,
      alert_cooldown_minutes: 30,
      alerts_enabled: true,
      enable_chronos_bolt: false,
      enable_xgboost: true,
      auto_retrain: false,
      theme_preference: 'system',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    })),
    updateUserSettings: vi.fn(async (input: Record<string, unknown>) => ({
      id: 1,
      user_id: 'test-user',
      default_region: (input.default_region as 'india' | 'us' | 'europe') ?? 'us',
      default_commodity: (input.default_commodity as 'gold' | 'silver' | 'crude_oil') ?? 'gold',
      prediction_horizon: (input.prediction_horizon as number) ?? 30,
      email_notifications: (input.email_notifications as boolean) ?? true,
      alert_cooldown_minutes: (input.alert_cooldown_minutes as number) ?? 30,
      alerts_enabled: (input.alerts_enabled as boolean) ?? true,
      enable_chronos_bolt: (input.enable_chronos_bolt as boolean) ?? false,
      enable_xgboost: (input.enable_xgboost as boolean) ?? true,
      auto_retrain: (input.auto_retrain as boolean) ?? false,
      theme_preference: (input.theme_preference as 'light' | 'dark' | 'system') ?? 'system',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    })),
  },
}));

describe('SettingsPage', () => {
  it('loads and validates prediction horizon before save', async () => {
    const queryClient = new QueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <SettingsPage />
      </QueryClientProvider>,
    );

    await waitFor(() => expect(screen.getByText('User Preferences')).toBeInTheDocument());
    const horizonInput = screen.getByLabelText('Prediction Horizon (days)') as HTMLInputElement;
    fireEvent.change(horizonInput, { target: { value: '0' } });
    fireEvent.click(screen.getAllByRole('button', { name: 'Save Settings' })[0]);

    expect(screen.getByText('Prediction horizon must be between 1 and 90 days.')).toBeInTheDocument();
  });
});
