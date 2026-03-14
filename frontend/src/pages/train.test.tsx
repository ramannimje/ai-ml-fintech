import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { TrainPage } from './train';

const mockTrain = vi.fn();
const mockTrainStatus = vi.fn();

vi.mock('../api/client', () => ({
  client: {
    train: (...args: unknown[]) => mockTrain(...args),
    trainStatus: (...args: unknown[]) => mockTrainStatus(...args),
  },
}));

describe('TrainPage', () => {
  beforeEach(() => {
    mockTrain.mockReset();
    mockTrainStatus.mockReset();
    mockTrain.mockResolvedValue({ message: 'Training initiated', status: 'processing' });
    mockTrainStatus.mockResolvedValue({
      status: 'none',
      message: 'No recent run',
    });
  });

  it('renders Model Training Studio title and scope options', () => {
    render(<TrainPage />);
    expect(screen.getByText('Model Training Studio')).toBeInTheDocument();
    expect(screen.getByText('Single Market')).toBeInTheDocument();
    expect(screen.getByText('All Markets')).toBeInTheDocument();
  });

  it('shows confirmation modal when Train All Markets is clicked', async () => {
    render(<TrainPage />);
    fireEvent.click(screen.getByText('All Markets'));
    fireEvent.click(screen.getByRole('button', { name: /Train All Markets/i }));
    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument();
      expect(screen.getByText(/Confirm bulk training/i)).toBeInTheDocument();
      expect(screen.getByText(/9 jobs/)).toBeInTheDocument();
    });
  });

  it('calls train 9 times when All Markets is confirmed', async () => {
    render(<TrainPage />);
    fireEvent.click(screen.getByText('All Markets'));
    fireEvent.click(screen.getByRole('button', { name: /Train All Markets/i }));
    await waitFor(() => expect(screen.getByRole('dialog')).toBeInTheDocument());
    fireEvent.click(screen.getByRole('button', { name: 'Confirm' }));
    await waitFor(
      () => {
        expect(mockTrain).toHaveBeenCalledTimes(9);
      },
      { timeout: 2000 }
    );
  });

  it('single market launches one job without modal', async () => {
    render(<TrainPage />);
    expect(screen.getByText('Single Market')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Run Training/i }));
    await waitFor(() => expect(mockTrain).toHaveBeenCalledTimes(1));
    expect(mockTrain).toHaveBeenCalledWith('gold', 'us', 30);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
});
