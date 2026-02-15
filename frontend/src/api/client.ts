import axios from 'axios';
import { z } from 'zod';
import type { Commodity, HistoricalResponse, MetricsResponse, PredictionResponse, TrainResponse } from '../types/api';

const api = axios.create({ baseURL: '/api' });

const commoditiesSchema = z.object({ commodities: z.array(z.string()) });

export const client = {
  commodities: async () => commoditiesSchema.parse((await api.get('/commodities')).data).commodities as Commodity[],
  historical: async (commodity: Commodity) => (await api.get<HistoricalResponse>(`/historical/${commodity}`)).data,
  train: async (commodity: Commodity, horizon: number) => (await api.post<TrainResponse>(`/train/${commodity}?horizon=${horizon}`)).data,
  predict: async (commodity: Commodity, horizon: number) => (await api.get<PredictionResponse>(`/predict/${commodity}?horizon=${horizon}`)).data,
  metrics: async (commodity: Commodity) => (await api.get<MetricsResponse>(`/metrics/${commodity}`)).data,
  retrainAll: async (horizon: number) => (await api.post(`/retrain-all?horizon=${horizon}`)).data,
};
