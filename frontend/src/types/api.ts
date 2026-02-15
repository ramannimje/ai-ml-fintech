export type Commodity = 'gold' | 'silver' | 'crude_oil';

export interface HistoricalPoint {
  date: string;
  close: number;
}

export interface HistoricalResponse {
  commodity: string;
  rows: number;
  data: HistoricalPoint[];
}

export interface PredictionResponse {
  commodity: string;
  prediction_date: string;
  predicted_price: number;
  confidence_interval: [number, number];
  model_used: string;
  model_accuracy_rmse: number;
  horizon_days: number;
}

export interface MetricsResponse {
  commodity: string;
  model_name: string;
  rmse: number;
  mape: number;
  trained_at: string;
}

export interface TrainResponse {
  commodity: string;
  best_model: string;
  model_version: string;
  rmse: number;
  mape: number;
}
