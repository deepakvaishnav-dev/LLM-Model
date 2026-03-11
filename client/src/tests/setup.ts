import '@testing-library/jest-dom';
import { vi } from 'vitest';
import React from 'react';

// Basic fetch mock that test cases can override
const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

// Mock all lucide-react icons globally
vi.mock('lucide-react', () => {
  return new Proxy(
    {},
    {
      get: function (_target, prop) {
        return ({ className }: { className?: string }) => {
          return React.createElement('span', {
            'data-testid': `icon-${String(prop)}`,
            className: className || '',
          });
        };
      },
    }
  );
});
