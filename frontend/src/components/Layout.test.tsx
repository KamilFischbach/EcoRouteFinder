import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { renderWithProviders } from '@/test/utils';

import { Layout } from './Layout';

describe('Layout footer', () => {
  it('credits the author with GitHub and LinkedIn links that open in a new tab', () => {
    renderWithProviders(<Layout />);

    expect(screen.getByText('Kamil Fischbach')).toBeInTheDocument();
    const github = screen.getByRole('link', { name: /Kamil Fischbach on GitHub/ });
    expect(github).toHaveAttribute('href', 'https://github.com/KamilFischbach');
    expect(github).toHaveAttribute('target', '_blank');
    expect(github).toHaveAttribute('rel', 'noopener noreferrer');
    expect(screen.getByRole('link', { name: /Kamil Fischbach on LinkedIn/ })).toHaveAttribute(
      'href',
      'https://www.linkedin.com/in/kamil-fischbach-288175253/',
    );
  });
});
