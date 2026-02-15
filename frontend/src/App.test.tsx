import { render } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { Layout } from './components/layout';

describe('Layout', () => {
  it('renders title', () => {
    const view = render(<MemoryRouter><Layout /></MemoryRouter>);
    expect(view.getByText(/AI Commodity Predictor/i)).toBeInTheDocument();
  });
});
