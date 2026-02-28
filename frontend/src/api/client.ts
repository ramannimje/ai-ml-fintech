import axios from 'axios';
import { z } from 'zod';
import type {
  Commodity,
  CommodityDefinition,
  HistoricalResponse,
  LivePrice,
  PredictionResponse,
  Region,
  RegionDefinition,
  TrainResponse,
} from '../types/api';

const baseURL = import.meta.env.VITE_API_BASE_URL || '/api';
const api = axios.create({ baseURL });

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

export const client = {
  regions: async () => z.array(regionSchema).parse((await api.get('/regions')).data) as RegionDefinition[],
  commodities: async () => z.array(commoditySchema).parse((await api.get('/commodities')).data) as CommodityDefinition[],
  livePrices: async () => liveEnvelopeSchema.parse((await api.get('/live-prices')).data).items as LivePrice[],
  livePricesByRegion: async (region: Region) =>
    liveEnvelopeSchema.parse((await api.get(`/live-prices/${region}`)).data).items as LivePrice[],
  historical: async (commodity: Commodity, region: Region, range: '1m' | '6m' | '1y' | '5y' | 'max') =>
    historicalSchema.parse((await api.get(`/historical/${commodity}/${region}?range=${range}`)).data) as HistoricalResponse,
  train: async (commodity: Commodity, region: Region, horizon: number) =>
    trainSchema.parse((await api.post(`/train/${commodity}/${region}?horizon=${horizon}`)).data) as TrainResponse,
  predict: async (commodity: Commodity, region: Region, horizon: number) =>
    predictionSchema.parse((await api.get(`/predict/${commodity}/${region}?horizon=${horizon}`)).data) as PredictionResponse,
};
