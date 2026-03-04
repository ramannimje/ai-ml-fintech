import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { client } from '../api/client';
import { useUiStore } from '../store/ui-store';
import type { Commodity, Region } from '../types/api';

type ThemePref = 'light' | 'dark' | 'system';

function asErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) return error.message;
  return fallback;
}

export function SettingsPage() {
  const queryClient = useQueryClient();
  const { setTheme } = useUiStore();
  const settingsQuery = useQuery({
    queryKey: ['user-settings'],
    queryFn: () => client.getUserSettings(),
    staleTime: 60_000,
  });

  const [defaultRegion, setDefaultRegion] = useState<Region>('us');
  const [defaultCommodity, setDefaultCommodity] = useState<Commodity>('gold');
  const [predictionHorizon, setPredictionHorizon] = useState<number>(30);

  const [emailNotifications, setEmailNotifications] = useState(true);
  const [alertCooldownMinutes, setAlertCooldownMinutes] = useState(30);
  const [alertsEnabled, setAlertsEnabled] = useState(true);

  const [themePreference, setThemePreference] = useState<ThemePref>('system');

  const [enableChronosBolt, setEnableChronosBolt] = useState(false);
  const [enableXgboost, setEnableXgboost] = useState(true);
  const [autoRetrain, setAutoRetrain] = useState(false);

  const [prefError, setPrefError] = useState<string>('');
  const [alertError, setAlertError] = useState<string>('');
  const [themeError, setThemeError] = useState<string>('');
  const [modelError, setModelError] = useState<string>('');

  useEffect(() => {
    if (!settingsQuery.data) return;
    const data = settingsQuery.data;
    setDefaultRegion(data.default_region);
    setDefaultCommodity(data.default_commodity);
    setPredictionHorizon(data.prediction_horizon);

    setEmailNotifications(data.email_notifications);
    setAlertCooldownMinutes(data.alert_cooldown_minutes);
    setAlertsEnabled(data.alerts_enabled);

    setThemePreference(data.theme_preference);

    setEnableChronosBolt(data.enable_chronos_bolt);
    setEnableXgboost(data.enable_xgboost);
    setAutoRetrain(data.auto_retrain);
  }, [settingsQuery.data]);

  const updateMutation = useMutation({
    mutationFn: (input: Parameters<typeof client.updateUserSettings>[0]) => client.updateUserSettings(input),
    onSuccess: async (next) => {
      await queryClient.setQueryData(['user-settings'], next);
      await queryClient.invalidateQueries({ queryKey: ['user-settings'] });
      await queryClient.invalidateQueries({ queryKey: ['live'] });
      await queryClient.invalidateQueries({ queryKey: ['pred-dashboard'] });
    },
  });

  const saveUserPreferences = async () => {
    setPrefError('');
    if (predictionHorizon < 1 || predictionHorizon > 90) {
      setPrefError('Prediction horizon must be between 1 and 90 days.');
      return;
    }
    try {
      await updateMutation.mutateAsync({
        default_region: defaultRegion,
        default_commodity: defaultCommodity,
        prediction_horizon: predictionHorizon,
      });
    } catch (error) {
      setPrefError(asErrorMessage(error, 'Failed to save user preferences.'));
    }
  };

  const saveAlertPreferences = async () => {
    setAlertError('');
    if (alertCooldownMinutes < 5 || alertCooldownMinutes > 1440) {
      setAlertError('Alert cooldown must be between 5 and 1440 minutes.');
      return;
    }
    try {
      await updateMutation.mutateAsync({
        email_notifications: emailNotifications,
        alert_cooldown_minutes: alertCooldownMinutes,
        alerts_enabled: alertsEnabled,
      });
    } catch (error) {
      setAlertError(asErrorMessage(error, 'Failed to save alert preferences.'));
    }
  };

  const saveThemePreferences = async () => {
    setThemeError('');
    try {
      const updated = await updateMutation.mutateAsync({
        theme_preference: themePreference,
      });
      setTheme(updated.theme_preference);
    } catch (error) {
      setThemeError(asErrorMessage(error, 'Failed to save theme preferences.'));
    }
  };

  const saveModelPreferences = async () => {
    setModelError('');
    if (!enableChronosBolt && !enableXgboost) {
      setModelError('At least one model must be enabled.');
      return;
    }
    try {
      await updateMutation.mutateAsync({
        enable_chronos_bolt: enableChronosBolt,
        enable_xgboost: enableXgboost,
        auto_retrain: autoRetrain,
      });
    } catch (error) {
      setModelError(asErrorMessage(error, 'Failed to save model preferences.'));
    }
  };

  if (settingsQuery.isLoading) {
    return <div className="panel rounded-2xl p-5 text-sm">Loading settings...</div>;
  }

  if (settingsQuery.isError || !settingsQuery.data) {
    return <div className="panel rounded-2xl p-5 text-sm" style={{ color: 'var(--danger)' }}>Failed to load settings.</div>;
  }

  return (
    <div className="space-y-6">
      <section>
        <h1 className="shell-title">Settings</h1>
        <p className="shell-subtitle">Configure personalized defaults, alerts, theme behavior, and model execution preferences.</p>
      </section>

      <motion.section
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.2 }}
        className="panel p-5"
      >
        <h2 className="text-2xl font-semibold">User Preferences</h2>
        <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-3">
          <label className="text-sm text-muted">
            Default Region
            <select className="ui-input mt-1" value={defaultRegion} onChange={(e) => setDefaultRegion(e.target.value as Region)}>
              <option value="us">US</option>
              <option value="india">India</option>
              <option value="europe">Europe</option>
            </select>
          </label>
          <label className="text-sm text-muted">
            Default Commodity
            <select className="ui-input mt-1" value={defaultCommodity} onChange={(e) => setDefaultCommodity(e.target.value as Commodity)}>
              <option value="gold">Gold</option>
              <option value="silver">Silver</option>
              <option value="crude_oil">Crude Oil</option>
            </select>
          </label>
          <label className="text-sm text-muted">
            Prediction Horizon (days)
            <input
              type="number"
              min={1}
              max={90}
              className="ui-input mt-1"
              value={predictionHorizon}
              onChange={(e) => setPredictionHorizon(Number(e.target.value || 1))}
            />
          </label>
        </div>
        {!!prefError && <p className="mt-3 text-sm" style={{ color: 'var(--danger)' }}>{prefError}</p>}
        <button type="button" onClick={saveUserPreferences} disabled={updateMutation.isPending} className="btn-primary mt-4">
          {updateMutation.isPending ? 'Saving...' : 'Save Settings'}
        </button>
      </motion.section>

      <motion.section
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.24 }}
        className="panel p-5"
      >
        <h2 className="text-2xl font-semibold">Alert Preferences</h2>
        <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-3">
          <label className="panel-soft flex items-center gap-2 rounded-xl p-3 text-sm text-muted">
            <input type="checkbox" checked={emailNotifications} onChange={(e) => setEmailNotifications(e.target.checked)} />
            Enable email notifications
          </label>
          <label className="text-sm text-muted">
            Alert cooldown minutes
            <input
              type="number"
              min={5}
              max={1440}
              className="ui-input mt-1"
              value={alertCooldownMinutes}
              onChange={(e) => setAlertCooldownMinutes(Number(e.target.value || 5))}
            />
          </label>
          <label className="panel-soft flex items-center gap-2 rounded-xl p-3 text-sm text-muted">
            <input type="checkbox" checked={alertsEnabled} onChange={(e) => setAlertsEnabled(e.target.checked)} />
            Enable alerts globally
          </label>
        </div>
        {!!alertError && <p className="mt-3 text-sm" style={{ color: 'var(--danger)' }}>{alertError}</p>}
        <button type="button" onClick={saveAlertPreferences} disabled={updateMutation.isPending} className="btn-primary mt-4">
          {updateMutation.isPending ? 'Saving...' : 'Save Settings'}
        </button>
      </motion.section>

      <motion.section
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.28 }}
        className="panel p-5"
      >
        <h2 className="text-2xl font-semibold">Theme Preferences</h2>
        <div className="mt-4 flex flex-wrap gap-2">
          {(['light', 'dark', 'system'] as ThemePref[]).map((theme) => (
            <button
              key={theme}
              type="button"
              onClick={() => setThemePreference(theme)}
              className={themePreference === theme ? 'btn-primary' : 'btn-ghost'}
            >
              {theme}
            </button>
          ))}
        </div>
        {!!themeError && <p className="mt-3 text-sm" style={{ color: 'var(--danger)' }}>{themeError}</p>}
        <button type="button" onClick={saveThemePreferences} disabled={updateMutation.isPending} className="btn-primary mt-4">
          {updateMutation.isPending ? 'Saving...' : 'Save Settings'}
        </button>
      </motion.section>

      <motion.section
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.32 }}
        className="panel p-5"
      >
        <h2 className="text-2xl font-semibold">Model Preferences</h2>
        <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-3">
          <label className="panel-soft flex items-center gap-2 rounded-xl p-3 text-sm text-muted">
            <input type="checkbox" checked={enableChronosBolt} onChange={(e) => setEnableChronosBolt(e.target.checked)} />
            Enable Chronos Bolt
          </label>
          <label className="panel-soft flex items-center gap-2 rounded-xl p-3 text-sm text-muted">
            <input type="checkbox" checked={enableXgboost} onChange={(e) => setEnableXgboost(e.target.checked)} />
            Enable XGBoost
          </label>
          <label className="panel-soft flex items-center gap-2 rounded-xl p-3 text-sm text-muted">
            <input type="checkbox" checked={autoRetrain} onChange={(e) => setAutoRetrain(e.target.checked)} />
            Enable Auto Retrain
          </label>
        </div>
        {!!modelError && <p className="mt-3 text-sm" style={{ color: 'var(--danger)' }}>{modelError}</p>}
        <button type="button" onClick={saveModelPreferences} disabled={updateMutation.isPending} className="btn-primary mt-4">
          {updateMutation.isPending ? 'Saving...' : 'Save Settings'}
        </button>
      </motion.section>
    </div>
  );
}
