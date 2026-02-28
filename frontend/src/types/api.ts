export type Commodity = 'gold' | 'silver' | 'crude_oil';
export type Region = 'india' | 'us' | 'europe';

export interface RegionDefinition {
  id: Region;
  currency: 'INR' | 'USD' | 'EUR';
  unit: string;
}

export interface CommodityDefinition {
  id: Commodity;
}

export interface LivePrice {
  commodity: Commodity;
  region: Region;
  unit: string;
  currency: string;
  live_price: number;
  source: string;
  timestamp: string;
}

export interface HistoricalPoint {
  date: string;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number;
  volume: number | null;
}

export interface HistoricalResponse {
  commodity: Commodity;
  region: Region;
  currency: string;
  unit: string;
  rows: number;
  data: HistoricalPoint[];
}

export interface PredictionResponse {
  commodity: Commodity;
  region: Region;
  unit: string;
  currency: string;
  forecast_horizon: string;
  point_forecast: number;
  confidence_interval: [number, number];
  scenario: 'bull' | 'base' | 'bear';
  scenario_forecasts: Record<'bull' | 'base' | 'bear', number>;
  model_used: string;
}

export interface TrainResponse {
  commodity: Commodity;
  region: Region;
  best_model: string;
  model_version: string;
  rmse: number;
  mape: number;
}
