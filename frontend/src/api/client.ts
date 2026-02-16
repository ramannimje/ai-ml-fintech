import axios from 'axios';
import { z } from 'zod';
import type { Commodity, HistoricalResponse, MetricsResponse, PredictionResponse, Region, TrainResponse } from '../types/api';

const api = axios.create({ baseURL: '/api' });
const commoditiesSchema = z.object({ commodities: z.array(z.string()) });

export const client = {
  commodities: async () => commoditiesSchema.parse((await api.get('/commodities')).data).commodities as Commodity[],
  historical: async (commodity: Commodity, region: Region, range = '5y') => (await api.get<HistoricalResponse>(`/historical/${commodity}?region=${region}&range=${range}`)).data,
  train: async (commodity: Commodity, region: Region, horizon: number) => (await api.post<TrainResponse>(`/train/${commodity}?region=${region}&horizon=${horizon}`)).data,
  predict: async (commodity: Commodity, region: Region, horizon: number) => (await api.get<PredictionResponse>(`/predict/${commodity}?region=${region}&horizon=${horizon}`)).data,
  metrics: async (commodity: Commodity, region: Region) => (await api.get<MetricsResponse>(`/metrics/${commodity}?region=${region}`)).data,
  retrainAll: async (region: Region, horizon: number) => (await api.post(`/retrain-all?region=${region}&horizon=${horizon}`)).data,
};
