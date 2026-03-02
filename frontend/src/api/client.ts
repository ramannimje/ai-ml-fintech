import axios from 'axios';
import { z } from 'zod';
import type {
  AlertCommodity,
  AlertEvaluation,
  AlertHistoryItem,
  AlertType,
  CommodityNewsSummary,
  Commodity,
  CommodityDefinition,
  HistoricalResponse,
  LivePrice,
  PriceAlert,
  PredictionResponse,
  Region,
  RegionDefinition,
  TrainResponse,
} from '../types/api';

const baseURL = import.meta.env.VITE_API_BASE_URL || '/api';
const api = axios.create({ baseURL });
let tokenGetter: (() => Promise<string | undefined>) | null = null;

export function setAccessTokenGetter(getter: () => Promise<string | undefined>): void {
  tokenGetter = getter;
}

api.interceptors.request.use(async (config) => {
  if (tokenGetter) {
    const token = await tokenGetter();
    if (token) {
      config.headers = config.headers ?? {};
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

const regionSchema = z.object({
  id: z.enum(['india', 'us', 'europe']),
  currency: z.enum(['INR', 'USD', 'EUR']),
  unit: z.string(),
});

const commoditySchema = z.object({
  id: z.enum(['gold', 'silver', 'crude_oil']),
});

export const livePriceSchema = z.object({
  commodity: z.enum(['gold', 'silver', 'crude_oil']),
  region: z.enum(['india', 'us', 'europe']),
  unit: z.string(),
  currency: z.string(),
  live_price: z.number(),
  source: z.string(),
  timestamp: z.string(),
});

const liveEnvelopeSchema = z.object({ items: z.array(livePriceSchema) });

const historicalPointSchema = z.object({
  date: z.string(),
  open: z.number().nullable(),
  high: z.number().nullable(),
  low: z.number().nullable(),
  close: z.number(),
  volume: z.number().nullable(),
});

export const historicalSchema = z.object({
  commodity: z.enum(['gold', 'silver', 'crude_oil']),
  region: z.enum(['india', 'us', 'europe']),
  currency: z.string(),
  unit: z.string(),
  rows: z.number(),
  data: z.array(historicalPointSchema),
});

export const predictionSchema = z.object({
  commodity: z.enum(['gold', 'silver', 'crude_oil']),
  region: z.enum(['india', 'us', 'europe']),
  unit: z.string(),
  currency: z.string(),
  forecast_horizon: z.string(),
  point_forecast: z.number(),
  confidence_interval: z.tuple([z.number(), z.number()]),
  scenario: z.enum(['bull', 'base', 'bear']),
  scenario_forecasts: z.object({
    bull: z.number(),
    base: z.number(),
    bear: z.number(),
  }),
  model_used: z.string(),
});

const trainSchema = z.object({
  commodity: z.enum(['gold', 'silver', 'crude_oil']),
  region: z.enum(['india', 'us', 'europe']),
  best_model: z.string(),
  model_version: z.string(),
  rmse: z.number(),
  mape: z.number(),
});

const alertCommoditySchema = z.enum(['gold', 'silver', 'crude_oil', 'natural_gas', 'copper']);
const alertTypeSchema = z.enum(['above', 'below', 'pct_change_24h', 'spike', 'drop']);

const priceAlertSchema = z.object({
  id: z.number(),
  commodity: alertCommoditySchema,
  region: z.enum(['india', 'us', 'europe']),
  currency: z.string(),
  unit: z.string(),
  alert_type: alertTypeSchema,
  threshold: z.number(),
  enabled: z.boolean(),
  last_triggered_at: z.string().nullable().optional(),
  created_at: z.string(),
});

const alertHistorySchema = z.object({
  id: z.number(),
  alert_id: z.number(),
  commodity: alertCommoditySchema,
  region: z.enum(['india', 'us', 'europe']),
  currency: z.string(),
  alert_type: alertTypeSchema,
  threshold: z.number(),
  observed_value: z.number(),
  message: z.string(),
  email_status: z.string(),
  triggered_at: z.string(),
});

const alertEvaluationSchema = z.object({
  checked: z.number(),
  triggered: z.number(),
  events: z.array(alertHistorySchema),
});

const newsHeadlineSchema = z.object({
  title: z.string(),
  source: z.string(),
  url: z.string(),
  published_at: z.string(),
});

const newsSummarySchema = z.object({
  commodity: alertCommoditySchema,
  sentiment: z.enum(['bullish', 'bearish', 'neutral']),
  summary: z.string(),
  headlines: z.array(newsHeadlineSchema),
  updated_at: z.string(),
});

export const client = {
  regions: async () => z.array(regionSchema).parse((await api.get('/regions')).data) as RegionDefinition[],
  commodities: async () => z.array(commoditySchema).parse((await api.get('/commodities')).data) as CommodityDefinition[],
  livePrices: async () => liveEnvelopeSchema.parse((await api.get('/live-prices')).data).items as LivePrice[],
  livePricesByRegion: async (region: Region) =>
    liveEnvelopeSchema.parse((await api.get(`/live-prices/${region}`)).data).items as LivePrice[],
  publicLivePricesByRegion: async (region: Region) =>
    liveEnvelopeSchema.parse((await api.get(`/public/live-prices/${region}`)).data).items as LivePrice[],
  historical: async (commodity: Commodity, region: Region, range: '1m' | '6m' | '1y' | '5y' | 'max') =>
    historicalSchema.parse((await api.get(`/historical/${commodity}/${region}?range=${range}`)).data) as HistoricalResponse,
  train: async (commodity: Commodity, region: Region, horizon: number) =>
    trainSchema.parse((await api.post(`/train/${commodity}/${region}?horizon=${horizon}`)).data) as TrainResponse,
  predict: async (commodity: Commodity, region: Region, horizon: number) =>
    predictionSchema.parse((await api.get(`/predict/${commodity}/${region}?horizon=${horizon}`)).data) as PredictionResponse,
  createAlert: async (input: { commodity: AlertCommodity; region: Region; alert_type: AlertType; threshold: number }) =>
    priceAlertSchema.parse((await api.post('/alerts', input)).data) as PriceAlert,
  listAlerts: async () => z.array(priceAlertSchema).parse((await api.get('/alerts')).data) as PriceAlert[],
  deleteAlert: async (alertId: number) => api.delete(`/alerts/${alertId}`),
  evaluateAlerts: async () => alertEvaluationSchema.parse((await api.post('/alerts/evaluate')).data) as AlertEvaluation,
  alertHistory: async () => z.array(alertHistorySchema).parse((await api.get('/alerts/history')).data) as AlertHistoryItem[],
  commodityNewsSummary: async (commodity: AlertCommodity) =>
    newsSummarySchema.parse((await api.get(`/news-summary/${commodity}`)).data) as CommodityNewsSummary,
};
