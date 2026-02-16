export type Commodity = 'gold' | 'silver' | 'crude_oil';
export type Region = 'india' | 'us' | 'europe';

export interface HistoricalPoint {
  timestamp: string;
  close: number;
  open?: number;
  high?: number;
  low?: number;
  volume?: number;
}

export interface HistoricalResponse {
  commodity: string;
  region: Region;
  currency: string;
  unit: string;
  source: string;
  rows: number;
  data: HistoricalPoint[];
}

export interface PredictionPoint {
  date: string;
  price: number;
}

export interface PredictionResponse {
  commodity: string;
  region: Region;
  unit: string;
  currency: string;
  predictions: PredictionPoint[];
  confidence_interval: [number, number];
  model_used: string;
  model_accuracy_rmse: number;
  horizon_days: number;
}

export interface MetricsResponse {
  commodity: string;
  region: Region;
  model_name: string;
  rmse: number;
  mape: number;
  trained_at: string;
}

export interface TrainResponse {
  commodity: string;
  region: Region;
  best_model: string;
  model_version: string;
  rmse: number;
  mape: number;
}
